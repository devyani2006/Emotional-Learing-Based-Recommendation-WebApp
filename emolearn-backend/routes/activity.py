from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from database import db
from models import ActivityContent, UserActivity, User
import random

activity_bp = Blueprint("activity", __name__)

ACTIVITY_TYPES = {
    "music":      "🎵",
    "video":      "🎬",
    "shorts":     "📱",
    "quiz":       "❓",
    "breathing":  "🫁",
    "meditation": "🧘",
    "exercise":   "🏃",
    "article":    "📄",
    "journal":    "📓",
    "art":        "🎨",
    "game":       "🎮",
}


@activity_bp.get("/api/activities/for-emotion/<emotion>")
@jwt_required()
def activities_for_emotion(emotion):
    """Return exactly 3 diverse activity recommendations for the given emotion."""
    items = ActivityContent.query.filter_by(target_emotion=emotion, is_active=True).all()
    if not items:
        # fallback: any active
        items = ActivityContent.query.filter_by(is_active=True).all()

    random.shuffle(items)
    seen_types, picked = set(), []
    for item in items:
        if item.activity_type not in seen_types:
            picked.append(item)
            seen_types.add(item.activity_type)
        if len(picked) >= 3:
            break
    # Fill if still under 3
    for item in items:
        if item not in picked:
            picked.append(item)
        if len(picked) >= 3:
            break

    for a in picked:
        a.play_count = (a.play_count or 0) + 1
    db.session.commit()

    return jsonify(activities=[a.to_dict() for a in picked[:3]])


@activity_bp.post("/api/activities/choose")
@jwt_required()
def choose_activity():
    uid_raw = get_jwt_identity()
    if uid_raw == "admin":
        return jsonify(detail="Admin cannot do activities"), 403

    d = request.get_json()
    activity_id     = d.get("activity_id")
    emotion_at_time = d.get("emotion", "neutral")

    activity = db.session.get(ActivityContent, activity_id)
    if not activity:
        return jsonify(detail="Activity not found"), 404

    log = UserActivity(
        user_id=int(uid_raw),
        activity_id=activity_id,
        emotion_at_time=emotion_at_time,
        completed=False
    )
    db.session.add(log)
    db.session.commit()

    action = _get_action(activity)
    return jsonify(log_id=log.id, activity=activity.to_dict(), action=action)


@activity_bp.post("/api/activities/complete/<int:log_id>")
@jwt_required()
def complete_activity(log_id):
    uid = get_jwt_identity()
    if uid == "admin":
        return jsonify(detail="Admin cannot complete activities"), 403

    log = db.session.get(UserActivity, log_id)
    if not log or log.user_id != int(uid):
        return jsonify(detail="Not found"), 404

    body = request.get_json(silent=True) or {}
    log.completed      = True
    log.duration_spent = body.get("duration_seconds", 0)
    log.rating         = body.get("rating", None)

    # XP reward
    activity = db.session.get(ActivityContent, log.activity_id)
    xp = (activity.xp_reward or 15) if activity else 15
    log.xp_earned = xp

    user = db.session.get(User, int(uid))
    if user:
        user.total_xp = (user.total_xp or 0) + xp
        user.level    = max(1, (user.total_xp // 100) + 1)

    db.session.commit()

    # Check achievements
    newly_earned = []
    try:
        from routes.advanced import _check_achievements
        if user:
            newly_earned = _check_achievements(user)
    except Exception:
        pass

    return jsonify(
        message="Activity completed! 🎉",
        xp_earned=xp,
        new_xp=user.total_xp if user else 0,
        level=user.level if user else 1,
        newly_earned=newly_earned
    )


@activity_bp.get("/api/activities/my-history")
@jwt_required()
def my_activity_history():
    uid = get_jwt_identity()
    if uid == "admin":
        return jsonify(activities=[])
    logs = UserActivity.query.filter_by(user_id=int(uid))\
                             .order_by(UserActivity.created_at.desc()).limit(30).all()
    result = []
    for l in logs:
        act = db.session.get(ActivityContent, l.activity_id)
        result.append({
            **l.to_dict(),
            "activity_title": act.title if act else "Unknown",
            "activity_type":  act.activity_type if act else "—",
            "activity_icon":  act.icon if act else "📚",
        })
    return jsonify(activities=result)


def _get_action(activity: ActivityContent) -> dict:
    t = activity.activity_type
    if t in ("music", "video", "shorts", "article"):
        return {
            "type": "open_url",
            "url":  activity.url or "https://youtube.com",
            "label": "Open " + t.capitalize(),
            "embed": activity.url and "youtube" in (activity.url or "")
        }
    elif t == "quiz":
        return {"type": "quiz", "questions": _sample_quiz()}
    elif t == "breathing":
        return {
            "type": "breathing", "pattern": "4-7-8",
            "steps": [
                {"name":"Inhale","seconds":4,"instruction":"Breathe in slowly through your nose"},
                {"name":"Hold",  "seconds":7,"instruction":"Hold your breath gently"},
                {"name":"Exhale","seconds":8,"instruction":"Breathe out slowly through your mouth"},
            ], "cycles": 4
        }
    elif t == "meditation":
        return {"type": "timer", "seconds": (activity.duration_minutes or 5)*60,
                "label": "Meditation Timer", "sound": True}
    elif t == "exercise":
        return {"type": "exercise", "steps": [
            "Stand up and stretch for 30 seconds",
            "Roll your shoulders 5 times each direction",
            "Take 5 deep breaths",
            "Shake out your hands and arms",
            "Sit back down — feeling refreshed!"
        ]}
    elif t == "journal":
        return {"type": "journal", "prompts": [
            "How are you feeling right now?",
            "What led to this feeling today?",
            "What would help you feel better?"
        ]}
    elif t == "art":
        return {"type": "art"}
    elif t == "game":
        return {"type": "game"}
    return {"type": "info", "message": activity.description}


def _sample_quiz():
    return [
        {"q":"What is 15% of 200?","options":["20","30","25","35"],"answer":1},
        {"q":"Which planet is closest to the Sun?","options":["Venus","Earth","Mars","Mercury"],"answer":3},
        {"q":"What does HTML stand for?","options":["Hyper Text Markup Language","High Tech Modern Language","Hyper Transfer Markup Logic","Home Tool Markup Language"],"answer":0},
        {"q":"What is the square root of 144?","options":["10","11","12","13"],"answer":2},
        {"q":"Who wrote 'Romeo and Juliet'?","options":["Charles Dickens","William Shakespeare","Jane Austen","Mark Twain"],"answer":1},
    ]
