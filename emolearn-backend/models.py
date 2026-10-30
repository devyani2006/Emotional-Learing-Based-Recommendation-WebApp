from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"
    id           = db.Column(db.Integer, primary_key=True)
    fullname     = db.Column(db.String(100))
    username     = db.Column(db.String(50),  unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    phone        = db.Column(db.String(20))
    dob          = db.Column(db.String(20))
    role         = db.Column(db.String(20),  default="customer")
    is_active    = db.Column(db.Boolean,     default=True)
    avatar_emoji = db.Column(db.String(10),  default="😊")
    bio          = db.Column(db.Text,        default="")
    total_xp     = db.Column(db.Integer,     default=0)
    level        = db.Column(db.Integer,     default=1)
    streak_days  = db.Column(db.Integer,     default=0)
    last_login   = db.Column(db.DateTime,    nullable=True)
    created_at   = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return dict(
            id=self.id, fullname=self.fullname, username=self.username,
            email=self.email, phone=self.phone, dob=self.dob,
            role=self.role, is_active=self.is_active,
            avatar_emoji=self.avatar_emoji, bio=self.bio,
            total_xp=self.total_xp, level=self.level,
            streak_days=self.streak_days,
            last_login=str(self.last_login) if self.last_login else None,
            created_at=str(self.created_at)
        )


class EmotionLog(db.Model):
    __tablename__ = "emotion_logs"
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    emotion       = db.Column(db.String(30),  nullable=False)
    confidence    = db.Column(db.Float,       nullable=False)
    face_detected = db.Column(db.Boolean,     default=True)
    source        = db.Column(db.String(20),  default="camera")
    notes         = db.Column(db.Text,        nullable=True)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return dict(
            id=self.id, user_id=self.user_id, emotion=self.emotion,
            confidence=self.confidence, face_detected=self.face_detected,
            source=self.source, notes=self.notes,
            created_at=str(self.created_at)
        )


class ActivityContent(db.Model):
    __tablename__ = "activity_content"
    id               = db.Column(db.Integer, primary_key=True)
    title            = db.Column(db.String(200), nullable=False)
    description      = db.Column(db.Text)
    activity_type    = db.Column(db.String(30),  nullable=False)
    target_emotion   = db.Column(db.String(30),  nullable=False)
    url              = db.Column(db.String(500))
    icon             = db.Column(db.String(10),  default="📚")
    difficulty       = db.Column(db.String(20),  default="beginner")
    duration_minutes = db.Column(db.Integer,     default=5)
    xp_reward        = db.Column(db.Integer,     default=15)
    play_count       = db.Column(db.Integer,     default=0)
    is_active        = db.Column(db.Boolean,     default=True)
    created_by       = db.Column(db.String(20),  default="admin")
    created_at       = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return dict(
            id=self.id, title=self.title, description=self.description,
            activity_type=self.activity_type, target_emotion=self.target_emotion,
            url=self.url, icon=self.icon, difficulty=self.difficulty,
            duration_minutes=self.duration_minutes, xp_reward=self.xp_reward,
            play_count=self.play_count, is_active=self.is_active,
            created_by=self.created_by, created_at=str(self.created_at)
        )


class UserActivity(db.Model):
    __tablename__ = "user_activities"
    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    activity_id     = db.Column(db.Integer, db.ForeignKey("activity_content.id"), nullable=False)
    emotion_at_time = db.Column(db.String(30))
    completed       = db.Column(db.Boolean, default=False)
    duration_spent  = db.Column(db.Integer, default=0)
    rating          = db.Column(db.Integer, nullable=True)
    xp_earned       = db.Column(db.Integer, default=0)
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return dict(
            id=self.id, user_id=self.user_id, activity_id=self.activity_id,
            emotion_at_time=self.emotion_at_time, completed=self.completed,
            duration_spent=self.duration_spent, rating=self.rating,
            xp_earned=self.xp_earned, created_at=str(self.created_at)
        )


class EmotionRule(db.Model):
    __tablename__ = "emotion_rules"
    id             = db.Column(db.Integer, primary_key=True)
    emotion        = db.Column(db.String(30), unique=True, nullable=False)
    label          = db.Column(db.String(60))
    recommendation = db.Column(db.Text, nullable=False)
    tip            = db.Column(db.Text)
    priority       = db.Column(db.Integer, default=1)
    active         = db.Column(db.Boolean, default=True)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return dict(
            id=self.id, emotion=self.emotion, label=self.label,
            recommendation=self.recommendation, tip=self.tip,
            priority=self.priority, active=self.active,
            updated_at=str(self.updated_at)
        )


class Achievement(db.Model):
    __tablename__ = "achievements"
    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.Text)
    emoji           = db.Column(db.String(10), default="🏆")
    condition_type  = db.Column(db.String(30), nullable=False)
    condition_value = db.Column(db.Integer, default=1)
    xp_reward       = db.Column(db.Integer, default=50)
    rarity          = db.Column(db.String(20), default="common")

    def to_dict(self):
        return dict(id=self.id, name=self.name, description=self.description,
                    emoji=self.emoji, condition_type=self.condition_type,
                    condition_value=self.condition_value, xp_reward=self.xp_reward,
                    rarity=self.rarity)


class UserAchievement(db.Model):
    __tablename__ = "user_achievements"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    achievement_id = db.Column(db.Integer, nullable=False)
    earned_at      = db.Column(db.DateTime, default=datetime.utcnow)
