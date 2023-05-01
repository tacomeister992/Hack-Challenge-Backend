from db import db
# from db import ### MODELS
from db import User
from db import Photo
from db import Item
from db import Note
from db import Category

import users_dao

from flask import Flask, request
import json
import os

app = Flask(__name__)
db_filename = "bucket.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


# generalized response formats
def success_response(data, code=200):
    return json.dumps(data), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


def extract_token(req):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = req.headers.get('Authorization')
    if auth_header is None:
        return False, 'Missing auth header'

    bearer_token = auth_header.replace('Bearer', '').strip()
    if not bearer_token:
        return False, 'Invalid auth header'

    return True, bearer_token


# Authentication routes
@app.route('/register/', methods=['POST'])
def register_account():
    """
    Endpoint for registering a new user
    """
    body = json.loads(request.data)
    email = body.get('email')
    password = body.get('password')

    if email is None or password is None:
        return failure_response('Invalid email or password', 400)

    created, user = users_dao.create_user(email, password)

    if not created:
        return failure_response('User already exists', 400)

    return success_response({
        'session_token': user.session_token,
        'session_expiration': str(user.session_expiration),
        'update_token': user.update_token
    })


@app.route('/login/', methods=['POST'])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    email = body.get('email')
    password = body.get('password')

    if email is None or password is None:
        return failure_response('Invalid email or password', 400)

    success, user = users_dao.verify_credentials(email, password)
    if not success:
        return failure_response('Incorrect email or password', 400)

    return success_response({
        'session_token': user.session_token,
        'session_expiration': str(user.session_expiration),
        'update_token': user.update_token
    })


@app.route('/session/', methods=['POST'])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, update_token = extract_token(request)
    if not success:
        return update_token

    user = users_dao.renew_session(update_token)
    if user is None:
        return failure_response('Invalid update token', 401)

    return success_response({
        'session_token': user.session_token,
        'session_expiration': str(user.session_expiration),
        'update_token': user.update_token
    })


@app.route('/logout/', methods=['POST'])
def login():
    """
    Endpoint for logging out a user
    """
    pass


@app.route('/items/')
def get_items_from_user():
    """
    Endpoint for getting the items from a user
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    items = user.serialize()
    del items['id']
    return success_response(items)


# App routes




# Authentication routes (ie. sign up/log in)
# Get items for user with id=1 (GET /items/1/)
# Add item for user with id=1 (GET /items/1/)
#

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
