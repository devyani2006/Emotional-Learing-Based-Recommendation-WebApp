from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from database import db
from models import EmotionLog, User
from datetime import datetime, timedelta
from sqlalchemy import func

emotions_bp = Blueprint("emotions", __name__)

def _get_user():
    uid = get_jwt_identity()
    if uid == "admin":
        return None
    return db.session.get(User, int(uid))


@emotions_bp.post("/api/emotions")
@jwt_required()
def save_emotion():
    user = _get_user()
    if not user:
        return jsonify(detail="Admin cannot log emotions"), 403
    d = request.get_json()
    log = EmotionLog(
        user_id       = user.id,
        emotion       = d.get("emotion", "neutral"),
        confidence    = float(d.get("confidence", 0.5)),
        face_detected = d.get("face_detected", True),
        source        = d.get("source", "camera")
    )
    db.session.add(log)

    # Update streak
    from datetime import date, timedelta, datetime as dt
    today = date.today()
    last  = user.last_login.date() if user.last_login else None
    if last is None or last < today - timedelta(days=1):
        user.streak_days = 1
    elif last < today:
        user.streak_days = (user.streak_days or 0) + 1
    user.last_login = dt.utcnow()

    db.session.commit()
    return jsonify(message="Saved", emotion=log.emotion, streak=user.streak_days)


@emotions_bp.get("/api/emotions/history")
@jwt_required()
def get_history():
    user = _get_user()
    if not user:
        return jsonify(emotions=[])
    limit = int(request.args.get("limit", 50))
    logs = EmotionLog.query.filter_by(user_id=user.id)\
                           .order_by(EmotionLog.created_at.desc()).limit(limit).all()
    return jsonify(emotions=[l.to_dict() for l in logs])


@emotions_bp.get("/api/emotions/stats")
@jwt_required()
def get_stats():
    user = _get_user()
    if not user:
        return jsonify({})
    logs = EmotionLog.query.filter_by(user_id=user.id).all()
    if not logs:
        return jsonify(total_sessions=0, avg_confidence=0,
                       dominant_emotion="neutral", avg_focus_score=0,
                       emotion_counts={}, weekly=[])

    counts = {}
    for l in logs:
        counts[l.emotion] = counts.get(l.emotion, 0) + 1
    dominant  = max(counts, key=counts.get)
    avg_conf  = sum(l.confidence for l in logs) / len(logs)
    focused   = sum(1 for l in logs if l.emotion in ["engaged", "happy", "neutral", "calm"])
    focus_pct = round((focused / len(logs)) * 100)

    # Weekly chart — last 7 days grouped by day
    seven_days_ago = datetime.utcnow() - timedelta(days=6)
    weekly_logs = EmotionLog.query.filter(
        EmotionLog.user_id == user.id,
        EmotionLog.created_at >= seven_days_ago
    ).all()

    from collections import defaultdict
    daily = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
    POSITIVE = {"happy", "engaged", "calm", "surprised"}
    NEGATIVE = {"anxious", "sad", "angry", "confused", "bored"}
    for l in weekly_logs:
        day = l.created_at.strftime("%a")
        daily[day]["total"] += 1
        if l.emotion in POSITIVE:
            daily[day]["positive"] += 1
        elif l.emotion in NEGATIVE:
            daily[day]["negative"] += 1
        else:
            daily[day]["neutral"] += 1

    days_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    weekly = [{"day": d, **daily[d]} for d in days_order]

    return jsonify(
        total_sessions   = len(logs) // 5 + 1,
        avg_confidence   = round(avg_conf * 100),
        dominant_emotion = dominant,
        avg_focus_score  = focus_pct,
        emotion_counts   = counts,
        weekly           = weekly,
        total_logs       = len(logs)
    )


@emotions_bp.get("/api/emotions/chart")
@jwt_required()
def get_chart():
    """Daily emotion breakdown for line/bar chart"""
    user = _get_user()
    if not user:
        return jsonify(data=[])
    days = int(request.args.get("days", 7))
    since = datetime.utcnow() - timedelta(days=days)
    logs = EmotionLog.query.filter(
        EmotionLog.user_id == user.id,
        EmotionLog.created_at >= since
    ).order_by(EmotionLog.created_at).all()

    # Group by date
    from collections import defaultdict
    daily = defaultdict(list)
    for l in logs:
        day = l.created_at.strftime("%Y-%m-%d")
        daily[day].append(l.emotion)

    result = []
    for day, emotions in sorted(daily.items()):
        c = {}
        for e in emotions:
            c[e] = c.get(e, 0) + 1
        dominant = max(c, key=c.get) if c else "neutral"
        result.append({"date": day, "emotions": c, "dominant": dominant, "total": len(emotions)})

    return jsonify(data=result)
