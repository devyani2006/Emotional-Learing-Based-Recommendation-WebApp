"""
EmoLearn Advanced Routes
- Friends / Social
- User Settings & Preferences
- Export Report (JSON / CSV)
- Mood Trend Prediction
- Achievements check
- Streak management
- Personalized Learning Path
"""
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from database import db
from models import (User, EmotionLog, UserActivity, ActivityContent,
                    Achievement, UserAchievement)
from datetime import datetime, timedelta, date
import json, csv, io, random

adv_bp = Blueprint("advanced", __name__)

# ── helpers ───────────────────────────────────────────────
def _uid():
    raw = get_jwt_identity()
    if raw == "admin":
        return None
    return int(raw)

def _user():
    uid = _uid()
    return db.session.get(User, uid) if uid else None


# ══════════════════════════════════════════════════════════
#  STREAK  (called after every emotion save)
# ══════════════════════════════════════════════════════════
@adv_bp.post("/api/streak/update")
@jwt_required()
def update_streak():
    user = _user()
    if not user:
        return jsonify(detail="Admin cannot update streak"), 403

    today = date.today()
    last  = user.last_login.date() if user.last_login else None

    if last is None or last < today - timedelta(days=1):
        user.streak_days = 1            # reset
    elif last < today:
        user.streak_days = (user.streak_days or 0) + 1  # extend
    # same day → no change

    user.last_login = datetime.utcnow()
    db.session.commit()

    # check streak achievements
    _check_achievements(user)
    return jsonify(streak=user.streak_days)


# ══════════════════════════════════════════════════════════
#  ACHIEVEMENTS
# ══════════════════════════════════════════════════════════
def _check_achievements(user):
    """Auto-unlock achievements for a user — call after XP/streak update."""
    all_achievements = Achievement.query.all()
    earned_ids = {ua.achievement_id for ua in
                  UserAchievement.query.filter_by(user_id=user.id).all()}

    activity_count = UserActivity.query.filter_by(
        user_id=user.id, completed=True).count()
    emotion_count  = EmotionLog.query.filter_by(user_id=user.id).count()

    newly_earned = []
    for ach in all_achievements:
        if ach.id in earned_ids:
            continue
        ct = ach.condition_type
        cv = ach.condition_value
        unlocked = False
        if ct == "activities" and activity_count >= cv:
            unlocked = True
        elif ct == "emotions"  and emotion_count  >= cv:
            unlocked = True
        elif ct == "streak"    and (user.streak_days or 0) >= cv:
            unlocked = True
        elif ct == "xp"        and (user.total_xp   or 0) >= cv:
            unlocked = True

        if unlocked:
            db.session.add(UserAchievement(
                user_id=user.id, achievement_id=ach.id))
            user.total_xp = (user.total_xp or 0) + ach.xp_reward
            user.level    = max(1, (user.total_xp // 100) + 1)
            newly_earned.append(ach.to_dict())

    if newly_earned:
        db.session.commit()
    return newly_earned


@adv_bp.get("/api/achievements")
@jwt_required()
def get_achievements():
    user = _user()
    if not user:
        return jsonify(achievements=[])

    all_ach = Achievement.query.all()
    earned  = {ua.achievement_id: ua.earned_at for ua in
               UserAchievement.query.filter_by(user_id=user.id).all()}

    result = []
    for a in all_ach:
        d = a.to_dict()
        d["earned"]    = a.id in earned
        d["earned_at"] = str(earned[a.id]) if a.id in earned else None
        result.append(d)

    return jsonify(achievements=result)


@adv_bp.post("/api/achievements/check")
@jwt_required()
def check_achievements():
    user = _user()
    if not user:
        return jsonify(newly_earned=[])
    newly = _check_achievements(user)
    return jsonify(newly_earned=newly)


# ══════════════════════════════════════════════════════════
#  USER SETTINGS & PREFERENCES
# ══════════════════════════════════════════════════════════
@adv_bp.get("/api/settings")
@jwt_required()
def get_settings():
    user = _user()
    if not user:
        return jsonify(detail="Admin"), 403

    # Settings stored as JSON in user.bio field prefixed with __settings__
    # (to avoid a new column migration)
    raw = user.bio or ""
    if raw.startswith("__settings__"):
        try:
            settings = json.loads(raw[len("__settings__"):])
        except Exception:
            settings = {}
    else:
        settings = {}

    defaults = {
        "notifications_enabled": True,
        "daily_reminder_time": "09:00",
        "preferred_activities": [],
        "theme": "dark",
        "session_duration": 30,
        "language": "en",
        "show_mood_prediction": True,
        "public_profile": False,
        "bio_text": raw if not raw.startswith("__settings__") else "",
    }
    return jsonify({**defaults, **settings})


@adv_bp.put("/api/settings")
@jwt_required()
def update_settings():
    user = _user()
    if not user:
        return jsonify(detail="Admin"), 403

    d = request.get_json() or {}

    # Load existing
    raw = user.bio or ""
    if raw.startswith("__settings__"):
        try:
            existing = json.loads(raw[len("__settings__"):])
        except Exception:
            existing = {}
    else:
        existing = {"bio_text": raw}

    existing.update(d)
    user.bio = "__settings__" + json.dumps(existing)
    db.session.commit()
    return jsonify(message="Settings saved!", settings=existing)


# ══════════════════════════════════════════════════════════
#  MOOD TREND PREDICTION
# ══════════════════════════════════════════════════════════
@adv_bp.get("/api/mood/prediction")
@jwt_required()
def mood_prediction():
    user = _user()
    if not user:
        return jsonify(detail="Admin"), 403

    # Last 14 days of logs
    since = datetime.utcnow() - timedelta(days=14)
    logs  = (EmotionLog.query
             .filter(EmotionLog.user_id == user.id,
                     EmotionLog.created_at >= since)
             .order_by(EmotionLog.created_at.asc())
             .all())

    if len(logs) < 3:
        return jsonify(
            prediction="neutral",
            confidence=0.5,
            trend="insufficient_data",
            insight="Log more sessions to enable mood predictions.",
            weekly_pattern=[],
            improvement_tips=[]
        )

    # Count emotions
    from collections import Counter
    counts  = Counter(l.emotion for l in logs)
    total   = len(logs)
    recent  = logs[-min(5, len(logs)):]
    r_counts = Counter(l.emotion for l in recent)

    # Most frequent recent emotion
    predicted = r_counts.most_common(1)[0][0]
    confidence = round(r_counts[predicted] / len(recent), 2)

    # Trend: positive / negative / stable
    POS = {"happy", "engaged", "calm", "surprised"}
    NEG = {"sad", "anxious", "angry", "bored", "confused"}
    early = logs[:len(logs)//2]
    late  = logs[len(logs)//2:]
    early_pos = sum(1 for l in early if l.emotion in POS) / max(len(early), 1)
    late_pos  = sum(1 for l in late  if l.emotion in POS) / max(len(late),  1)
    if   late_pos > early_pos + 0.1: trend = "improving"
    elif late_pos < early_pos - 0.1: trend = "declining"
    else:                             trend = "stable"

    # Weekly pattern (counts per weekday)
    weekdays = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    wd_counts = [0]*7
    for l in logs:
        wd_counts[l.created_at.weekday()] += 1
    weekly_pattern = [{"day": weekdays[i], "count": wd_counts[i]}
                      for i in range(7)]

    # Insights & tips
    dominant = counts.most_common(1)[0][0]
    INSIGHTS = {
        "happy":    "You're in a great mental space lately! Keep up the positive momentum.",
        "engaged":  "Your focus and curiosity are at a high — perfect for deep learning.",
        "calm":     "Consistent calm is your superpower. Use it for complex topics.",
        "anxious":  "Anxiety patterns detected. Breathing exercises could help significantly.",
        "sad":      "You've had some tough days. Remember to take breaks and be kind to yourself.",
        "bored":    "Boredom spikes suggest you need more variety in your activities.",
        "confused": "Confusion is a sign of growth! Try breaking topics into smaller chunks.",
        "angry":    "Frustration peaks detected. Short walks or breathing exercises may help.",
        "neutral":  "Stable neutral state — a good baseline for consistent learning.",
        "surprised":"Lots of curiosity! Follow that energy into new topics.",
    }
    TIPS = {
        "anxious":  ["Try 4-7-8 breathing before sessions", "Limit session length to 20 min",
                     "Journal your worries before starting"],
        "sad":      ["Start with uplifting music", "Short 5-min wins build momentum",
                     "Connect with a friend after studying"],
        "bored":    ["Switch activity types every 15 min", "Set a challenge timer",
                     "Try the memory game for a quick reset"],
        "confused": ["Use the Feynman technique", "Watch an explainer video first",
                     "Take notes with mind maps"],
        "angry":    ["Physical activity first", "Box breathing 4-4-4-4",
                     "5 min break before resuming"],
        "happy":    ["Channel energy into hard topics", "Teach someone else",
                     "Set ambitious goals today"],
        "engaged":  ["Go deep — avoid distractions", "Work on your hardest subject",
                     "Log what worked for next time"],
        "calm":     ["Read dense material now", "Practice memorisation",
                     "Try meditation to extend this state"],
    }
    insight = INSIGHTS.get(dominant, "Keep logging to get better insights!")
    tips    = TIPS.get(dominant, ["Stay consistent", "Log daily for better predictions"])

    return jsonify(
        prediction=predicted,
        confidence=confidence,
        trend=trend,
        dominant_14d=dominant,
        insight=insight,
        weekly_pattern=weekly_pattern,
        improvement_tips=tips,
        total_logs=total,
    )


# ══════════════════════════════════════════════════════════
#  PERSONALIZED LEARNING PATH
# ══════════════════════════════════════════════════════════
@adv_bp.get("/api/learning-path")
@jwt_required()
def learning_path():
    user = _user()
    if not user:
        return jsonify(detail="Admin"), 403

    completed_ids = {ua.activity_id for ua in
                     UserActivity.query.filter_by(
                         user_id=user.id, completed=True).all()}

    # Recent dominant emotion
    recent_logs = (EmotionLog.query
                   .filter_by(user_id=user.id)
                   .order_by(EmotionLog.created_at.desc())
                   .limit(10).all())
    from collections import Counter
    if recent_logs:
        dominant = Counter(l.emotion for l in recent_logs).most_common(1)[0][0]
    else:
        dominant = "neutral"

    # Build 3-step path
    steps = []

    # Step 1: warm-up (beginner, not done)
    warmup = (ActivityContent.query
              .filter_by(target_emotion=dominant, difficulty="beginner", is_active=True)
              .filter(ActivityContent.id.notin_(completed_ids))
              .first())
    if not warmup:
        warmup = (ActivityContent.query
                  .filter_by(target_emotion=dominant, is_active=True)
                  .filter(ActivityContent.id.notin_(completed_ids))
                  .first())
    if warmup:
        steps.append({"step": 1, "label": "🌱 Warm-Up",
                      "activity": warmup.to_dict(), "done": False})

    # Step 2: intermediate / different type
    done_types = {warmup.activity_type} if warmup else set()
    mid = (ActivityContent.query
           .filter_by(target_emotion=dominant, difficulty="intermediate", is_active=True)
           .filter(ActivityContent.id.notin_(completed_ids))
           .filter(ActivityContent.activity_type.notin_(done_types))
           .first())
    if not mid:
        mid = (ActivityContent.query
               .filter_by(is_active=True)
               .filter(ActivityContent.id.notin_(completed_ids))
               .filter(ActivityContent.activity_type.notin_(done_types))
               .first())
    if mid:
        done_types.add(mid.activity_type)
        steps.append({"step": 2, "label": "🚀 Core Practice",
                      "activity": mid.to_dict(), "done": False})

    # Step 3: advanced / challenge
    challenge = (ActivityContent.query
                 .filter_by(difficulty="advanced", is_active=True)
                 .filter(ActivityContent.id.notin_(completed_ids))
                 .filter(ActivityContent.activity_type.notin_(done_types))
                 .first())
    if not challenge:
        challenge = (ActivityContent.query
                     .filter_by(is_active=True)
                     .filter(ActivityContent.id.notin_(completed_ids))
                     .filter(ActivityContent.activity_type.notin_(done_types))
                     .first())
    if challenge:
        steps.append({"step": 3, "label": "🏆 Challenge",
                      "activity": challenge.to_dict(), "done": False})

    # XP progress
    total_xp   = user.total_xp or 0
    next_level = (user.level or 1) * 100
    xp_pct     = int((total_xp % 100))

    return jsonify(
        dominant_emotion=dominant,
        path_steps=steps,
        completed_count=len(completed_ids),
        total_xp=total_xp,
        level=user.level or 1,
        xp_to_next=max(0, next_level - total_xp),
        xp_pct=xp_pct,
    )


# ══════════════════════════════════════════════════════════
#  FRIENDS / SOCIAL
# ══════════════════════════════════════════════════════════
@adv_bp.get("/api/social/leaderboard")
@jwt_required()
def leaderboard():
    users = (User.query
             .filter_by(is_active=True)
             .filter(User.role != "admin")
             .order_by(User.total_xp.desc())
             .limit(20).all())
    uid = _uid()
    result = []
    for rank, u in enumerate(users, 1):
        result.append({
            "rank":        rank,
            "user_id":     u.id,
            "username":    u.username,
            "fullname":    u.fullname,
            "avatar_emoji":u.avatar_emoji or "😊",
            "total_xp":    u.total_xp or 0,
            "level":       u.level or 1,
            "streak_days": u.streak_days or 0,
            "is_me":       u.id == uid,
        })
    return jsonify(leaderboard=result)


@adv_bp.get("/api/social/profile/<int:target_uid>")
@jwt_required()
def public_profile(target_uid):
    u = db.session.get(User, target_uid)
    if not u or not u.is_active or u.role == "admin":
        return jsonify(detail="Not found"), 404

    activity_count = UserActivity.query.filter_by(
        user_id=u.id, completed=True).count()
    emotion_count  = EmotionLog.query.filter_by(user_id=u.id).count()

    earned_achievements = (
        db.session.query(Achievement)
        .join(UserAchievement, Achievement.id == UserAchievement.achievement_id)
        .filter(UserAchievement.user_id == u.id)
        .all()
    )

    return jsonify(
        user_id=u.id,
        username=u.username,
        fullname=u.fullname,
        avatar_emoji=u.avatar_emoji or "😊",
        level=u.level or 1,
        total_xp=u.total_xp or 0,
        streak_days=u.streak_days or 0,
        activity_count=activity_count,
        emotion_count=emotion_count,
        achievements=[a.to_dict() for a in earned_achievements],
        member_since=str(u.created_at)[:10] if u.created_at else "—",
    )


# ══════════════════════════════════════════════════════════
#  EXPORT REPORT
# ══════════════════════════════════════════════════════════
@adv_bp.get("/api/export/json")
@jwt_required()
def export_json():
    user = _user()
    if not user:
        return jsonify(detail="Admin cannot export"), 403

    emotions = [e.to_dict() for e in
                EmotionLog.query.filter_by(user_id=user.id)
                .order_by(EmotionLog.created_at.desc()).all()]

    activities_raw = (UserActivity.query
                      .filter_by(user_id=user.id)
                      .order_by(UserActivity.created_at.desc()).all())
    activities = []
    for a in activities_raw:
        ac = db.session.get(ActivityContent, a.activity_id)
        activities.append({
            **a.to_dict(),
            "activity_title": ac.title if ac else "—",
            "activity_type":  ac.activity_type if ac else "—",
        })

    earned = (
        db.session.query(Achievement)
        .join(UserAchievement, Achievement.id == UserAchievement.achievement_id)
        .filter(UserAchievement.user_id == user.id).all()
    )

    payload = {
        "exported_at":  datetime.utcnow().isoformat(),
        "user":         user.to_dict(),
        "emotions":     emotions,
        "activities":   activities,
        "achievements": [a.to_dict() for a in earned],
    }

    resp = make_response(json.dumps(payload, indent=2))
    resp.headers["Content-Type"]        = "application/json"
    resp.headers["Content-Disposition"] = \
        f"attachment; filename=emolearn-{user.username}-{date.today()}.json"
    return resp


@adv_bp.get("/api/export/csv")
@jwt_required()
def export_csv():
    user = _user()
    if not user:
        return jsonify(detail="Admin cannot export"), 403

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== EmoLearn Export ===", f"User: {user.username}",
                     f"Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])

    writer.writerow(["--- EMOTION LOGS ---"])
    writer.writerow(["ID","Emotion","Confidence","Source","Face Detected","Notes","Created At"])
    for e in (EmotionLog.query.filter_by(user_id=user.id)
              .order_by(EmotionLog.created_at.desc()).all()):
        writer.writerow([e.id, e.emotion, f"{e.confidence:.2f}", e.source,
                         e.face_detected, e.notes or "", e.created_at])

    writer.writerow([])
    writer.writerow(["--- ACTIVITY HISTORY ---"])
    writer.writerow(["ID","Activity","Type","Emotion","Completed","Duration(s)","XP Earned","Rating","Date"])
    for a in (UserActivity.query.filter_by(user_id=user.id)
              .order_by(UserActivity.created_at.desc()).all()):
        ac = db.session.get(ActivityContent, a.activity_id)
        writer.writerow([a.id, ac.title if ac else "—", ac.activity_type if ac else "—",
                         a.emotion_at_time, a.completed, a.duration_spent,
                         a.xp_earned, a.rating or "", a.created_at])

    writer.writerow([])
    writer.writerow(["--- PROFILE ---"])
    writer.writerow(["Username","Level","Total XP","Streak","Member Since"])
    writer.writerow([user.username, user.level, user.total_xp,
                     user.streak_days, str(user.created_at)[:10]])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"]        = "text/csv"
    resp.headers["Content-Disposition"] = \
        f"attachment; filename=emolearn-{user.username}-{date.today()}.csv"
    return resp


# ══════════════════════════════════════════════════════════
#  APP DEEP-LINK  (Spotify / YouTube Music / etc.)
# ══════════════════════════════════════════════════════════
@adv_bp.post("/api/activity/deep-link")
@jwt_required()
def get_deep_link():
    """
    Given a music/video activity URL, return platform-specific deep links
    so the frontend can open the native app.
    """
    d = request.get_json() or {}
    url   = d.get("url", "")
    title = d.get("title", "")
    atype = d.get("activity_type", "music")

    links = _build_deep_links(url, title, atype)
    return jsonify(links=links)


def _build_deep_links(url: str, title: str, atype: str) -> list:
    links = []
    url_lower = url.lower()
    query = title.replace(" ", "+")

    if atype == "music":
        links.append({
            "platform": "Spotify",
            "icon": "🎵",
            "url": f"https://open.spotify.com/search/{query}",
            "deep_link": f"spotify:search:{title}",
            "color": "#1DB954"
        })
        links.append({
            "platform": "YouTube Music",
            "icon": "🎶",
            "url": f"https://music.youtube.com/search?q={query}",
            "deep_link": f"youtubemusic://search?q={query}",
            "color": "#FF0000"
        })
        links.append({
            "platform": "Apple Music",
            "icon": "🍎",
            "url": f"https://music.apple.com/search?term={query}",
            "deep_link": f"music://music.apple.com/search?term={query}",
            "color": "#fc3c44"
        })
        links.append({
            "platform": "JioSaavn",
            "icon": "🎸",
            "url": f"https://www.jiosaavn.com/search/{query}",
            "deep_link": f"jiosaavn://search/{query}",
            "color": "#2BC5B4"
        })

    if atype in ("video", "shorts") or "youtube" in url_lower:
        links.append({
            "platform": "YouTube",
            "icon": "▶️",
            "url": url or f"https://www.youtube.com/results?search_query={query}",
            "deep_link": f"vnd.youtube://results?search_query={query}",
            "color": "#FF0000"
        })

    if atype == "meditation":
        links.append({
            "platform": "Headspace",
            "icon": "🧘",
            "url": "https://www.headspace.com",
            "deep_link": "headspace://",
            "color": "#F47D31"
        })
        links.append({
            "platform": "Calm",
            "icon": "😌",
            "url": "https://www.calm.com",
            "deep_link": "calm://",
            "color": "#4A90E2"
        })

    if atype == "exercise":
        links.append({
            "platform": "YouTube Fitness",
            "icon": "🏃",
            "url": f"https://www.youtube.com/results?search_query={query}+workout",
            "deep_link": f"vnd.youtube://results?search_query={query}+workout",
            "color": "#FF0000"
        })

    # Always add browser fallback
    if url:
        links.append({
            "platform": "Open in Browser",
            "icon": "🌐",
            "url": url,
            "deep_link": url,
            "color": "#666"
        })

    return links


# ══════════════════════════════════════════════════════════
#  NOTIFICATION PREFERENCES  (stored client-side via SW,
#  backend just stores the preference)
# ══════════════════════════════════════════════════════════
@adv_bp.post("/api/notifications/subscribe")
@jwt_required()
def subscribe_notifications():
    user = _user()
    if not user:
        return jsonify(detail="Admin"), 403
    # In production you'd store a web push subscription object
    # For now just confirm and return reminder time from settings
    d = request.get_json() or {}
    return jsonify(
        message="Notification preference saved!",
        reminder_time=d.get("reminder_time", "09:00")
    )
