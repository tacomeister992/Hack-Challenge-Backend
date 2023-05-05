from flask_sqlalchemy import SQLAlchemy

import datetime
import hashlib
import os

import base64
import boto3
from io import BytesIO
from mimetypes import guess_extension, guess_type
from PIL import Image
import random
import re
import string
import datetime
import bcrypt

db = SQLAlchemy()

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASEDIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us.east-1.amazonaws.com"

association_table = db.Table(
    "association", db.metadata,
    db.Column("item_id", db.Integer, db.ForeignKey("items.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"))
)


# Models
class Item(db.Model):
    """
    Model for item
    """

    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=True)
    likes = db.Column(db.Integer, nullable=False)
    liked_by = db.relationship('User', secondary=association_table, back_populates='liked_items')
    date = db.Column(db.DateTime(timezone=True), nullable=False)
    note = db.Column(db.String, nullable=False)
    photo = db.relationship('Photo', cascade='delete', uselist=False)  # one to one
    is_experience = db.Column(db.Boolean, nullable=False)  # True if Experience, False if Location
    # public = db.Column(db.Boolean, nullable=False), lets user set public or private items, add if have time

    def __init__(self, **kwargs):
        self.user_id = kwargs.get("user_id")
        self.name = kwargs.get("name")
        self.location = kwargs.get('location')
        self.likes = 0
        date = kwargs.get("date")
        self.date = datetime.datetime.strptime(date, '%m/%d/%y')
        self.note = kwargs.get('note')
        self.is_experience = kwargs.get('is_experience')

    def serialize(self):
        """
        Serialize an instance of Item
        """
        return {
            "id": self.id,
            "user": User.query.filter_by(id=self.user_id).first().email,
            "name": self.name,
            "location": self.location,
            "likes": self.likes,
            "date": self.date.strftime('%m/%d/%Y'),
            "note": self.note,
            "photo": self.photo.serialize(),
            "is_experience": self.is_experience
        }


class User(db.Model):
    """
    Model for user
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)

    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    items = db.relationship("Item", cascade="delete")
    liked_items = db.relationship("Item", secondary=association_table, back_populates='liked_by')
    name = db.Column(db.String, nullable=False)
    birth_year = db.Column(db.Integer, nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize an instance of User
        """
        self.email = kwargs.get("email")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"),
                                             bcrypt.gensalt(rounds=13))
        self.name = kwargs.get("name")
        self.birth_year = kwargs.get("birth_year")
        self.renew_session()

    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(
            days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token


class Photo(db.Model):
    """
    Model for photo
    """
    __tablename__ = "photos"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=True)
    salt = db.Column(db.String, nullable=True)
    extension = db.Column(db.String, nullable=True)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)

    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False) # -1 if not assigned to an item

    def __init__(self, **kwargs):
        self.create(kwargs.get("image_data"))
        self.item_id = kwargs.get("item_id", -1)

    def serialize(self):
        """
        Serialize and instance of Photo
        """
        return {
            "id": self.id,
            "base_url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at),
            "item_id": self.item_id
        }

    def create(self, image_data):
        """
        Given an image in base64 form, does the following:
        1. Rejects the image if its not supported filetype
        2. Generates a random string for the image filename
        3. Decodes the image and attempts to upload it to AWS
        """

        try:
            ext = guess_extension(guess_type(image_data))[0][1:]

            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} not supported")

            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)

        except Exception as e:
            print(f"Error while creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempt to upload the image into bucket
        """

        try:
            img_temploc = f"{BASEDIR}/{img_filename}"
            img.save(img_temploc)

            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET_NAME, img_filename)

            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.OcjectAc(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            os.remove(img_temploc)

        except Exception as e:
            print(f"Error while uploading image: {e}")

# Item
# User -> integrate into app, add poster field in item
# Photo
# look up crontab/cronjob


''' maybe don't need, only singular note field in item
class Note(db.Model):
    """
    Model for note
    """
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)

    def __init__(self, **kwargs):
        self.content = kwargs.get("content", "")
        self.item_id = kwargs.get("item_id")

    def serialize(self):
        """
        Serialize an instance of Note
        """
        return {
            "id": self.id,
            "content": self.content,
            "item_id": self.item_id
        }
'''


# prob don't need any more--only two catergories are Experience and Location
'''
class Category(db.Model):
    """
    Model for category
    """
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    items = db.relationship("Item", secondary=association_table, back_populates='categories')

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.type = kwargs.get("type", "")

    def serialize(self):
        """
        Serialize an instance of Catergory
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "items": [i.simple_serialize() for i in self.items]
        }

    def simple_serialize(self):
        """
        Serialize an instance of Catergory without items
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type
        }
'''
