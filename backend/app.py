from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from models import db, User
from auth import auth_bp, bcrypt
from recommender import recommender

app = Flask(__name__)

# Settings
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'mera-secret-key-123'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

# Setup
CORS(app)
db.init_app(app)
bcrypt.init_app(app)
JWTManager(app)

# Auth routes
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Database tables banao
with app.app_context():
    db.create_all()
    print("✅ Database ready!")


@app.route('/api/recommend', methods=['POST'])
@jwt_required()
def recommend():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    query = data.get('query', '').strip()

    if not query:
        return jsonify({'error': 'Kuch toh search karo bhai'}), 400

    results, error = recommender.search(query)

    if error:
        return jsonify({'error': error, 'results': []}), 404

    # Search history save karo
    user = User.query.get(user_id)
    if user:
        history = [h for h in user.history.split(',') if h] if user.history else []
        if query not in history:
            history.insert(0, query)
        user.history = ','.join(history[:20])
        db.session.commit()

    return jsonify({'results': results, 'count': len(results)}), 200


@app.route('/api/history', methods=['GET'])
@jwt_required()
def get_history():
    user = User.query.get(int(get_jwt_identity()))
    history = [h for h in user.history.split(',') if h] if user and user.history else []
    return jsonify({'history': history})


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'Server chal raha hai ✅',
        'movies': len(recommender.df) if recommender.df is not None else 0
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)