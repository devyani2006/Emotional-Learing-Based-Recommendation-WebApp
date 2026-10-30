from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User
from datetime import timedelta, datetime

auth_bp = Blueprint("auth", __name__)

def _user_token(user):
    return create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
        expires_delta=timedelta(hours=24)
    )

def _user_dict(user):
    return dict(
        id=user.id, email=user.email, username=user.username,
        fullname=user.fullname, role=user.role, dob=user.dob, phone=user.phone,
        avatar_emoji=user.avatar_emoji or "😊", bio=user.bio or "",
        total_xp=user.total_xp or 0, level=user.level or 1,
        streak_days=user.streak_days or 0, is_active=user.is_active
    )


@auth_bp.post("/api/auth/register")
def register():
    d = request.get_json()
    if not d:
        return jsonify(detail="No data"), 400
    if User.query.filter_by(email=d.get("email","")).first():
        return jsonify(detail="Email already registered"), 400
    if User.query.filter_by(username=d.get("username","")).first():
        return jsonify(detail="Username already taken"), 400

    user = User(
        fullname=d.get("fullname",""), username=d["username"],
        email=d["email"], password=generate_password_hash(d["password"]),
        phone=d.get("phone",""), dob=d.get("dob",""),
        role="customer", is_active=True,
        avatar_emoji=d.get("avatar_emoji","😊"),
        total_xp=0, level=1, streak_days=0
    )
    db.session.add(user)
    db.session.commit()
    token = _user_token(user)
    return jsonify(message="Account created!", token=token, user=_user_dict(user)), 201


@auth_bp.post("/api/auth/login")
def login():
    d = request.get_json()
    role = d.get("role", "customer")

    if role == "admin":
        if d.get("email") == "admin@gmail.com" and d.get("password") == "admin123":
            token = create_access_token(
                identity="admin",
                additional_claims={"role":"admin","email":"admin@gmail.com"},
                expires_delta=timedelta(hours=24)
            )
            return jsonify(token=token, user=dict(email="admin@gmail.com",role="admin",username="Admin"))
        return jsonify(detail="Invalid admin credentials"), 401

    user = User.query.filter_by(email=d.get("email","")).first()
    if not user or not check_password_hash(user.password, d.get("password","")):
        return jsonify(detail="Invalid email or password"), 401
    if not user.is_active:
        return jsonify(detail="Account is deactivated. Contact admin."), 403

    user.last_login = datetime.utcnow()
    db.session.commit()
    return jsonify(token=_user_token(user), user=_user_dict(user))


@auth_bp.get("/api/auth/me")
@jwt_required()
def me():
    claims = get_jwt()
    if claims.get("role") == "admin":
        return jsonify(email="admin@gmail.com", role="admin", username="Admin")
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user:
        return jsonify(detail="Not found"), 404
    return jsonify(_user_dict(user))


@auth_bp.put("/api/auth/profile")
@jwt_required()
def update_profile():
    claims = get_jwt()
    if claims.get("role") == "admin":
        return jsonify(detail="Admin profile not editable here"), 403
    uid = int(get_jwt_identity())
    user = db.session.get(User, uid)
    if not user:
        return jsonify(detail="Not found"), 404
    d = request.get_json() or {}
    for f in ["fullname","phone","bio","avatar_emoji"]:
        if f in d: setattr(user, f, d[f])
    db.session.commit()
    return jsonify(message="Profile updated!", user=_user_dict(user))
