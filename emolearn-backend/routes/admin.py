from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.security import generate_password_hash
from functools import wraps
from database import db
from models import User, EmotionLog, ActivityContent, UserActivity, EmotionRule
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get("role") != "admin":
            return jsonify(detail="Admin access required"), 403
        return fn(*args, **kwargs)
    return wrapper

# ── Stats ──────────────────────────────────────────────────────
@admin_bp.get("/api/admin/stats")
@admin_required
def stats():
    from collections import Counter
    from datetime import timedelta
    logs_30 = EmotionLog.query.filter(
        EmotionLog.created_at >= datetime.utcnow() - timedelta(days=30)
    ).all()
    emotion_dist = dict(Counter(l.emotion for l in logs_30))
    top_acts = ActivityContent.query.order_by(ActivityContent.play_count.desc()).limit(5).all()
    return jsonify(
        total_users      = User.query.filter_by(role="customer").count(),
        total_detections = EmotionLog.query.count(),
        total_content    = ActivityContent.query.count(),
        active_rules     = EmotionRule.query.filter_by(active=True).count(),
        total_activities = UserActivity.query.filter_by(completed=True).count(),
        emotion_dist_30d = emotion_dist,
        top_activities   = [{"title":a.title,"play_count":a.play_count,"type":a.activity_type} for a in top_acts]
    )

# ── Users ──────────────────────────────────────────────────────
@admin_bp.get("/api/admin/users")
@admin_required
def get_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify(users=[u.to_dict() for u in users])

@admin_bp.post("/api/admin/users")
@admin_required
def add_user():
    d = request.get_json()
    if not d.get("username") or not d.get("email") or not d.get("password"):
        return jsonify(detail="Username, Email and Password required"), 400
    if User.query.filter_by(email=d["email"]).first():
        return jsonify(detail="Email already exists"), 400
    if User.query.filter_by(username=d["username"]).first():
        return jsonify(detail="Username already exists"), 400
    user = User(
        fullname=d.get("fullname",""), username=d["username"],
        email=d["email"], password=generate_password_hash(d["password"]),
        phone=d.get("phone",""), dob=d.get("dob",""),
        role=d.get("role","customer"), is_active=True,
        avatar_emoji=d.get("avatar_emoji","😊"),
        total_xp=0, level=1, streak_days=0
    )
    db.session.add(user)
    db.session.commit()
    return jsonify(message="User added!", id=user.id), 201

@admin_bp.put("/api/admin/users/<int:uid>")
@admin_required
def update_user(uid):
    user = db.session.get(User, uid)
    if not user: return jsonify(detail="Not found"), 404
    d = request.get_json()
    for f in ["fullname","username","email","phone","dob","role","is_active","avatar_emoji","bio"]:
        if f in d: setattr(user, f, d[f])
    if d.get("password"):
        user.password = generate_password_hash(d["password"])
    db.session.commit()
    return jsonify(message="Updated!", user=user.to_dict())

@admin_bp.delete("/api/admin/users/<int:uid>")
@admin_required
def delete_user(uid):
    user = db.session.get(User, uid)
    if not user: return jsonify(detail="Not found"), 404
    EmotionLog.query.filter_by(user_id=uid).delete()
    UserActivity.query.filter_by(user_id=uid).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="User and all data deleted")

@admin_bp.patch("/api/admin/users/<int:uid>/toggle")
@admin_required
def toggle_user(uid):
    user = db.session.get(User, uid)
    if not user: return jsonify(detail="Not found"), 404
    user.is_active = not user.is_active
    db.session.commit()
    return jsonify(message="Toggled", is_active=user.is_active)

# ── Emotions ───────────────────────────────────────────────────
@admin_bp.get("/api/admin/all-emotions")
@admin_required
def all_emotions():
    rows = db.session.query(EmotionLog, User)\
                     .outerjoin(User, EmotionLog.user_id == User.id)\
                     .order_by(EmotionLog.created_at.desc()).limit(200).all()
    data = []
    for log, user in rows:
        d = log.to_dict()
        d["username"] = user.username if user else "Unknown"
        d["email"]    = user.email    if user else "—"
        data.append(d)
    return jsonify(emotions=data)

@admin_bp.get("/api/admin/users/<int:uid>/emotions")
@admin_required
def user_emotions(uid):
    logs = EmotionLog.query.filter_by(user_id=uid)\
                           .order_by(EmotionLog.created_at.desc()).all()
    return jsonify(emotions=[l.to_dict() for l in logs])

@admin_bp.post("/api/admin/emotions/manual")
@admin_required
def add_emotion_manually():
    """Admin manually adds an emotion log for any user."""
    d = request.get_json()
    user_id = d.get("user_id")
    if not user_id:
        return jsonify(detail="user_id required"), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(detail="User not found"), 404
    log = EmotionLog(
        user_id=user_id,
        emotion=d.get("emotion","neutral"),
        confidence=float(d.get("confidence", 0.9)),
        face_detected=False,
        source="manual",
        notes=d.get("notes","")
    )
    db.session.add(log)
    db.session.commit()
    return jsonify(message="Emotion added manually", id=log.id), 201

@admin_bp.delete("/api/admin/emotions/<int:eid>")
@admin_required
def delete_emotion(eid):
    log = db.session.get(EmotionLog, eid)
    if not log: return jsonify(detail="Not found"), 404
    db.session.delete(log)
    db.session.commit()
    return jsonify(message="Deleted")

@admin_bp.delete("/api/admin/emotions/user/<int:uid>")
@admin_required
def delete_all_user_emotions(uid):
    EmotionLog.query.filter_by(user_id=uid).delete()
    db.session.commit()
    return jsonify(message="All emotions deleted for user")

# ── Activity Content ───────────────────────────────────────────
@admin_bp.get("/api/admin/all-content")
@admin_required
def all_content():
    items = ActivityContent.query.order_by(ActivityContent.created_at.desc()).all()
    return jsonify(content=[c.to_dict() for c in items])

@admin_bp.post("/api/admin/content")
@admin_required
def add_content():
    d = request.get_json()
    if not d.get("title") or not d.get("activity_type") or not d.get("target_emotion"):
        return jsonify(detail="title, activity_type, target_emotion required"), 400
    item = ActivityContent(
        title=d["title"], description=d.get("description",""),
        activity_type=d["activity_type"], target_emotion=d["target_emotion"],
        url=d.get("url",""), icon=d.get("icon","📚"),
        difficulty=d.get("difficulty","beginner"),
        duration_minutes=int(d.get("duration_minutes",5)),
        xp_reward=int(d.get("xp_reward",15)),
        is_active=d.get("is_active",True),
        created_by=d.get("created_by","admin")
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(message="Content added!", id=item.id), 201

@admin_bp.put("/api/admin/content/<int:cid>")
@admin_required
def update_content(cid):
    item = db.session.get(ActivityContent, cid)
    if not item: return jsonify(detail="Not found"), 404
    d = request.get_json()
    for f in ["title","description","activity_type","target_emotion","url","icon","difficulty","duration_minutes","xp_reward","is_active","created_by"]:
        if f in d: setattr(item, f, d[f])
    db.session.commit()
    return jsonify(message="Updated!", content=item.to_dict())

@admin_bp.delete("/api/admin/content/<int:cid>")
@admin_required
def delete_content(cid):
    item = db.session.get(ActivityContent, cid)
    if not item: return jsonify(detail="Not found"), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify(message="Deleted")

@admin_bp.patch("/api/admin/content/<int:cid>/toggle")
@admin_required
def toggle_content(cid):
    item = db.session.get(ActivityContent, cid)
    if not item: return jsonify(detail="Not found"), 404
    item.is_active = not item.is_active
    db.session.commit()
    return jsonify(message="Toggled", is_active=item.is_active)

# ── Emotion Rules ──────────────────────────────────────────────
@admin_bp.get("/api/admin/emotion-rules")
@admin_required
def get_rules():
    rules = EmotionRule.query.all()
    return jsonify(rules=[r.to_dict() for r in rules])

@admin_bp.post("/api/admin/emotion-rules")
@admin_required
def add_rule():
    d = request.get_json()
    if not d.get("emotion") or not d.get("recommendation"):
        return jsonify(detail="emotion and recommendation required"), 400
    if EmotionRule.query.filter_by(emotion=d["emotion"]).first():
        return jsonify(detail="Rule for this emotion already exists"), 400
    rule = EmotionRule(
        emotion=d["emotion"], label=d.get("label",d["emotion"].capitalize()),
        recommendation=d["recommendation"], tip=d.get("tip",""),
        priority=int(d.get("priority",1)), active=d.get("active",True)
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify(message="Rule created!", id=rule.id), 201

@admin_bp.put("/api/admin/emotion-rules/<int:rid>")
@admin_required
def update_rule(rid):
    rule = db.session.get(EmotionRule, rid)
    if not rule: return jsonify(detail="Not found"), 404
    d = request.get_json()
    for f in ["label","recommendation","tip","priority","active"]:
        if f in d: setattr(rule, f, d[f])
    db.session.commit()
    return jsonify(message="Updated!", rule=rule.to_dict())

@admin_bp.delete("/api/admin/emotion-rules/<int:rid>")
@admin_required
def delete_rule(rid):
    rule = db.session.get(EmotionRule, rid)
    if not rule: return jsonify(detail="Not found"), 404
    db.session.delete(rule)
    db.session.commit()
    return jsonify(message="Deleted")
