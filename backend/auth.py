from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'Sab fields bharni zaroori hain'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password kam se kam 6 characters ka hona chahiye'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Yeh username pehle se le liya gaya hai'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Yeh email pehle se registered hai'}), 409

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(username=username, email=email, password=hashed)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'Account ban gaya!'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'error': 'Email ya password galat hai'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({
        'token': token,
        'username': user.username
    }), 200