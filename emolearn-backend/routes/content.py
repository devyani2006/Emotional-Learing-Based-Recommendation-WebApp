from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from database import db
from models import ActivityContent

content_bp = Blueprint("content", __name__)

@content_bp.get("/api/content")
def get_content():
    items = ActivityContent.query.filter_by(is_active=True).all()
    return jsonify([a.to_dict() for a in items])

@content_bp.get("/api/content/by-emotion/<emotion>")
def by_emotion(emotion):
    items = ActivityContent.query.filter_by(target_emotion=emotion, is_active=True).limit(3).all()
    return jsonify([a.to_dict() for a in items])
