from db import db
from db import User
from db import Photo
from db import Item

import users_dao

from flask import Flask, request
import json
import os
import datetime

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
def logout():
    """
    Endpoint for logging out a user
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    user.session_expiration = datetime.datetime.now()
    db.session.commit()
    return success_response({'message': 'Successful logout'})


# App routes
@app.route('/items/')
def get_all_items():
    items = [i.serialize() for i in Item.query.all()]
    return success_response({'items': items})


@app.route('/user/items/')
def get_items_of_user():
    """
    Endpoint for getting the items of a user
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    items = [i.serialize() for i in user.items]
    return success_response({'items': items})


@app.route('/user/items/', methods=['POST'])
def create_item():
    """
    Endpoint for creating an item for a user
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    body = json.loads(request.data)
    name = body.get('name')
    location = body.get('location')
    date = body.get('date')
    note = body.get('note')
    photo = body.get('photo')
    is_experience = body.get('is_experience')

    if not name or not location or not date or not note or is_experience is None:
        return failure_response('Invalid request body, something is missing', 400)
    if photo is None:
        return failure_response("No Base64 Url", 400)
    
    item = Item(user_id=user.id, name=name, location=location, date=date,
                note=note, photo=photo, is_experience=is_experience)
    
    photo = Photo(image_data=photo, item_id=item.id)

    db.session.add(item)
    db.session.add(photo)
    db.session.commit()

    return success_response(item.serialize(), 201)


@app.route('/user/items/<int:item_id>/', methods=['POST'])
def update_item(item_id):
    """
    Endpoint for updating an item for a user
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    item = Item.query.filter_by(id=item_id).first()
    if item is None:
        return failure_response('Item does not exist', 400)

    body = json.loads(request.data)
    name = body.get('name', item.name)
    location = body.get('location', item.location)
    date = body.get('date', item.date)
    note = body.get('note', item.note)
    photo = body.get('photo', item.photo)
    is_experience = body.get('is_experience', item.is_experience)

    item.name = name
    item.location = location
    item.date = date
    item.note = note
    item.photo = photo
    item.is_experience = is_experience
    db.session.commit()

    return success_response(item.serialize(), 200)


@app.route('/items/<int:item_id>/like/', methods=['POST'])
def like_item(item_id):
    """
    Endpoint for a user liking or unliking an Item
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    item = Item.query.filter_by(id=item_id).first()
    if item is None:
        return failure_response('Item does not exist', 400)

    if user in item.liked_by:
        item.likes -= 1
        item.liked_by.remove(user)
        like_msg = 'liked'
    else:
        item.likes += 1
        item.liked_by.append(user)
        like_msg = 'unliked'

    db.session.commit()
    return success_response({'message': f'User has successfully {like_msg} item {item_id}'})


@app.route('/user/items/<int:item_id>/', methods=['POST'])
def delete_item(item_id):
    """
    Endpoint for a user to delete their own item
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response(session_token, 400)

    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response('Invalid session', 401)

    item = Item.query.filter_by(id=item_id).first()
    if item is None:
        return failure_response('Item does not exist', 400)
    if item.user_id != user.id:
        return failure_response('User did not create the item', 401)

    db.session.delete(item)
    db.session.commit()

    return success_response(item.serialize())


# photo routes
@app.route("/upload/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image if image not assigned to an item
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No Base64 Url")
    
    photo = Photo(image_data=image_data)
    db.session.add(photo)
    db.session.commit()
    return success_response(photo.serialize(), 201)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
