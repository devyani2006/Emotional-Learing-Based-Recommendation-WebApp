# -*- coding: utf-8 -*-
"""
EmoLearn Backend -- Flask + SQLite
"""
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from database import db
import os

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["SQLALCHEMY_DATABASE_URI"]        = "sqlite:///emolearn.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"]                 = "emolearn-iit-secret-2025"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]       = False

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    from routes.auth     import auth_bp
    from routes.emotions import emotions_bp
    from routes.admin    import admin_bp
    from routes.content  import content_bp
    from routes.activity import activity_bp
    from routes.advanced import adv_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(emotions_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(adv_bp)

    with app.app_context():
        db.create_all()
        _seed_defaults()

    @app.route("/")
    def index():
        return send_file(os.path.join(FRONTEND_DIR, "index.html"))

    @app.route("/admin-dashboard.html")
    def admin_html():
        return send_file(os.path.join(FRONTEND_DIR, "admin-dashboard.html"))

    @app.route("/style.css")
    def style():
        return send_file(os.path.join(FRONTEND_DIR, "style.css"))

    @app.route("/src/<path:filename>")
    def src_files(filename):
        return send_from_directory(os.path.join(FRONTEND_DIR, "src"), filename)

    @app.route("/<path:filename>")
    def static_files(filename):
        target = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(target):
            return send_file(target)
        return send_file(os.path.join(FRONTEND_DIR, "index.html"))

    return app


def _seed_defaults():
    from models import EmotionRule, ActivityContent, Achievement
    from werkzeug.security import generate_password_hash
    from models import User

    # ── Seed admin user ──────────────────────────────────────
    from database import db as _db
    if not User.query.filter_by(email="admin@gmail.com").first():
        admin = User(
            fullname="Super Admin", username="admin",
            email="admin@gmail.com", password=generate_password_hash("admin123"),
            role="admin", is_active=True, avatar_emoji="🛡️",
            total_xp=9999, level=99
        )
        _db.session.add(admin)
        _db.session.commit()

    EMOTION_RULES = [
        dict(emotion="happy",    label="Happy 😊",    priority=1,
             recommendation="You're in the zone! Channel this energy into creative projects.",
             tip="Peak state — try something challenging while motivation is high."),
        dict(emotion="engaged",  label="Engaged 🤔",  priority=1,
             recommendation="Excellent focus! Keep pushing with challenging content.",
             tip="This is peak learning state — maximise it with deep work."),
        dict(emotion="neutral",  label="Neutral 😐",  priority=1,
             recommendation="Try a short quiz or video to spark curiosity.",
             tip="Explore a new topic that interests you."),
        dict(emotion="confused", label="Confused 😕", priority=3,
             recommendation="Let's slow down — simpler explanations and worked examples.",
             tip="Try explaining the concept in your own words to identify gaps."),
        dict(emotion="anxious",  label="Anxious 😰",  priority=3,
             recommendation="Take a breath. A short mindfulness break will help.",
             tip="Box breathing: 4s in → 4s hold → 4s out → 4s hold."),
        dict(emotion="bored",    label="Bored 😑",    priority=2,
             recommendation="Time for something interactive! A quiz or challenge awaits.",
             tip="Set a 5-minute challenge timer to re-engage."),
        dict(emotion="sad",      label="Sad 😢",      priority=3,
             recommendation="It's okay to take a break. Uplifting content is here.",
             tip="Journaling for 2 minutes can help process emotions."),
        dict(emotion="angry",    label="Angry 😠",    priority=3,
             recommendation="Let's release that tension first — breathing exercise ready.",
             tip="Step away for 5 minutes before returning to the topic."),
        dict(emotion="calm",     label="Calm 😌",     priority=1,
             recommendation="Perfect state for deep reading or new concepts.",
             tip="Calm focus is ideal for memorisation tasks."),
        dict(emotion="surprised",label="Surprised 😲",priority=1,
             recommendation="Curiosity unlocked! Explore related topics while interest is fresh.",
             tip="Follow the curiosity trail — note what surprised you."),
    ]

    ACTIVITY_CONTENT = [
        # HAPPY
        dict(title="Happy Upbeat Playlist",activity_type="music",target_emotion="happy",
             description="Feel-good music to amplify your positive energy.",
             url="https://www.youtube.com/results?search_query=happy+upbeat+playlist",icon="🎵",difficulty="beginner",duration_minutes=15,xp_reward=15),
        dict(title="Watch: The Science of Happiness",activity_type="video",target_emotion="happy",
             description="A TED-Ed on what makes us happy.",
             url="https://www.youtube.com/results?search_query=happiness+science+ted",icon="🎬",difficulty="beginner",duration_minutes=8,xp_reward=20),
        dict(title="Gratitude Journal",activity_type="journal",target_emotion="happy",
             description="Write 3 things you are grateful for to amplify positive feelings.",
             url=None,icon="📓",difficulty="beginner",duration_minutes=5,xp_reward=25),
        # CONFUSED
        dict(title="Khan Academy Explainer",activity_type="video",target_emotion="confused",
             description="Step-by-step video explanations from Khan Academy.",
             url="https://www.khanacademy.org",icon="🎬",difficulty="beginner",duration_minutes=10,xp_reward=20),
        dict(title="Concept Mind Map",activity_type="exercise",target_emotion="confused",
             description="Draw a mind map connecting the ideas you find confusing.",
             url=None,icon="🗺️",difficulty="beginner",duration_minutes=8,xp_reward=20),
        dict(title="Feynman Technique Guide",activity_type="article",target_emotion="confused",
             description="Explain the concept like you are teaching a 5-year-old.",
             url="https://www.youtube.com/results?search_query=feynman+technique",icon="📄",difficulty="beginner",duration_minutes=6,xp_reward=15),
        # ANXIOUS
        dict(title="4-7-8 Breathing Exercise",activity_type="breathing",target_emotion="anxious",
             description="Guided breathing: 4 in, 7 hold, 8 out. Reduces anxiety fast.",
             url=None,icon="🫁",difficulty="beginner",duration_minutes=3,xp_reward=25),
        dict(title="5-Minute Meditation",activity_type="meditation",target_emotion="anxious",
             description="Quick mindfulness session to calm nerves.",
             url="https://www.youtube.com/results?search_query=5+minute+meditation+anxiety",icon="🧘",difficulty="beginner",duration_minutes=5,xp_reward=25),
        dict(title="Calm Lofi Music",activity_type="music",target_emotion="anxious",
             description="Lo-fi beats to calm your anxious mind.",
             url="https://www.youtube.com/results?search_query=lofi+study+calm",icon="🎵",difficulty="beginner",duration_minutes=15,xp_reward=15),
        # BORED
        dict(title="Interactive Quiz Challenge",activity_type="quiz",target_emotion="bored",
             description="5-minute quiz to re-engage your brain.",
             url=None,icon="❓",difficulty="intermediate",duration_minutes=5,xp_reward=30),
        dict(title="YouTube Educational Shorts",activity_type="shorts",target_emotion="bored",
             description="Fascinating facts in under 60 seconds.",
             url="https://www.youtube.com/shorts",icon="📱",difficulty="beginner",duration_minutes=5,xp_reward=10),
        dict(title="Mandala Coloring Art",activity_type="art",target_emotion="bored",
             description="Interactive mandala drawing — art therapy for boredom.",
             url=None,icon="🎨",difficulty="beginner",duration_minutes=10,xp_reward=20),
        # SAD
        dict(title="Uplifting Music Playlist",activity_type="music",target_emotion="sad",
             description="Feel-good music to brighten your mood.",
             url="https://www.youtube.com/results?search_query=uplifting+happy+music",icon="🎵",difficulty="beginner",duration_minutes=10,xp_reward=15),
        dict(title="Gratitude Journal Prompt",activity_type="journal",target_emotion="sad",
             description="Write 3 things you are grateful for right now.",
             url=None,icon="📓",difficulty="beginner",duration_minutes=5,xp_reward=25),
        dict(title="Comedy Shorts",activity_type="video",target_emotion="sad",
             description="Light-hearted clips to lift your spirits.",
             url="https://www.youtube.com/results?search_query=funny+wholesome+shorts",icon="🎬",difficulty="beginner",duration_minutes=5,xp_reward=10),
        # ENGAGED
        dict(title="Deep-Dive Documentary",activity_type="video",target_emotion="engaged",
             description="Long-form educational documentary.",
             url="https://www.youtube.com/results?search_query=educational+documentary",icon="🎬",difficulty="advanced",duration_minutes=30,xp_reward=30),
        dict(title="Advanced Quiz Challenge",activity_type="quiz",target_emotion="engaged",
             description="Push your limits with hard questions.",
             url=None,icon="🏆",difficulty="advanced",duration_minutes=15,xp_reward=40),
        dict(title="Focus Music — Deep Work",activity_type="music",target_emotion="engaged",
             description="Binaural beats for deep focus sessions.",
             url="https://www.youtube.com/results?search_query=binaural+beats+focus+study",icon="🎵",difficulty="beginner",duration_minutes=60,xp_reward=15),
        # ANGRY
        dict(title="Progressive Muscle Relaxation",activity_type="exercise",target_emotion="angry",
             description="Tense and release muscle groups to release anger.",
             url="https://www.youtube.com/results?search_query=progressive+muscle+relaxation",icon="🏃",difficulty="beginner",duration_minutes=7,xp_reward=20),
        dict(title="Box Breathing — Anger Reset",activity_type="breathing",target_emotion="angry",
             description="4-4-4-4 box breathing to cool down instantly.",
             url=None,icon="🫁",difficulty="beginner",duration_minutes=3,xp_reward=25),
        dict(title="Classical Music Reset",activity_type="music",target_emotion="angry",
             description="Soothing classical music to restore calm.",
             url="https://www.youtube.com/results?search_query=classical+music+calm+relaxing",icon="🎵",difficulty="beginner",duration_minutes=10,xp_reward=15),
        # NEUTRAL
        dict(title="TED Talk: Curiosity",activity_type="video",target_emotion="neutral",
             description="Short inspiring TED talk to spark interest.",
             url="https://www.youtube.com/results?search_query=ted+talk+learning+curiosity",icon="🎬",difficulty="beginner",duration_minutes=12,xp_reward=20),
        dict(title="Quick Knowledge Quiz",activity_type="quiz",target_emotion="neutral",
             description="General knowledge quiz — just for fun!",
             url=None,icon="❓",difficulty="beginner",duration_minutes=5,xp_reward=25),
        dict(title="Ambient Study Music",activity_type="music",target_emotion="neutral",
             description="Background music for comfortable studying.",
             url="https://www.youtube.com/results?search_query=ambient+study+music",icon="🎵",difficulty="beginner",duration_minutes=30,xp_reward=10),
        # CALM
        dict(title="New Concept Introduction",activity_type="article",target_emotion="calm",
             description="Perfect time to absorb a brand new topic.",
             url="https://www.youtube.com/results?search_query=learn+something+new+educational",icon="📄",difficulty="intermediate",duration_minutes=15,xp_reward=20),
        dict(title="Memory Techniques",activity_type="exercise",target_emotion="calm",
             description="Practice spaced repetition and memory palace techniques.",
             url=None,icon="🧠",difficulty="intermediate",duration_minutes=10,xp_reward=25),
        dict(title="Nature Soundscape",activity_type="music",target_emotion="calm",
             description="Nature sounds for a peaceful study session.",
             url="https://www.youtube.com/results?search_query=nature+sounds+study+focus",icon="🌿",difficulty="beginner",duration_minutes=60,xp_reward=10),
    ]

    ACHIEVEMENTS = [
        dict(name="First Step",      description="Complete your first activity",     emoji="🌱", condition_type="activities", condition_value=1,   xp_reward=50,  rarity="common"),
        dict(name="Explorer",        description="Log 10 emotion sessions",           emoji="🔍", condition_type="emotions",   condition_value=10,  xp_reward=75,  rarity="common"),
        dict(name="Week Warrior",    description="Maintain a 7-day streak",           emoji="🔥", condition_type="streak",     condition_value=7,   xp_reward=150, rarity="rare"),
        dict(name="XP Hunter",       description="Earn 500 total XP",                 emoji="⭐", condition_type="xp",         condition_value=500, xp_reward=100, rarity="rare"),
        dict(name="Mindful Master",  description="Complete 20 activities",            emoji="🧘", condition_type="activities", condition_value=20,  xp_reward=200, rarity="epic"),
        dict(name="Month Streak",    description="30-day consecutive streak",         emoji="🏆", condition_type="streak",     condition_value=30,  xp_reward=500, rarity="legendary"),
        dict(name="XP Legend",       description="Earn 2000 total XP",               emoji="💎", condition_type="xp",         condition_value=2000,xp_reward=750, rarity="legendary"),
    ]

    if EmotionRule.query.count() == 0:
        for r in EMOTION_RULES:
            db.session.add(EmotionRule(**r))
        db.session.commit()

    if ActivityContent.query.count() == 0:
        for a in ACTIVITY_CONTENT:
            db.session.add(ActivityContent(**a))
        db.session.commit()

    if Achievement.query.count() == 0:
        for a in ACHIEVEMENTS:
            db.session.add(Achievement(**a))
        db.session.commit()


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    app = create_app()
    print("\n" + "="*50)
    print("  EmoLearn Server Started! ")
    print("  http://localhost:5000")
    print("  Admin: admin@gmail.com / admin123")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)
