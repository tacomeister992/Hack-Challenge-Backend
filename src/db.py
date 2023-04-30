from flask_sqlalchemy import SQLAlchemy

import datetime
import hashlib
import os

import base64
import boto
import io
from io import BytesIO
from mimetypes import guess_extension, guess_type
from PIL import Image
import random
import re
import string

import bcrypt

db = SQLAlchemy()

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASEDIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us.east-1.amazonaws.com"

association_table = db.Table(
    "association", db.Model.metadata,
    db.Column("item_id", db.Integer, db.ForeignKey("items.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"))
)

association_table2 = db.Table(
    "association2", db.metadata,
    db.Column("item_id", db.Integer, db.ForeignKey("items.id")),
    db.Column("photo_id", db.Integer, db.ForeignKey("photos.id"))
)


# Models
class Item(db.Model):
    """
    Model for item
    """

    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False) # maybe make many-to-many to add multiple users to an item, i.e. users, if we have time
    name = db.Column(db.String, nullable=False)
    likes = db.Column(db.Integer, nullable=False) # likes to help with popular sorting
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date = db.Column(db.DateTime(timezone=True), nullable=True) # null if no end date, need to find a way to do recurring events if have time, but don't really need
    notes = db.relationship("Note", cascade="delete")
    photo = db.relationship("Photo", secondary=association_table2, back_populates="items")
    categories = db.relationship("Category", secondary=association_table, back_populates='items')
    # public = db.Column(db.Boolean, nullable=False), lets user set public or private items

    def __init__(self, **kwargs):
        self.user_id = kwargs.get("user_id")
        self.likes = 0
        self.name = kwargs.get("name", "")
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")


    def serialize(self):
        """
        Serialize an instance of Item
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "likes": self.likes,
            "dates": f"{self.start_date} - {self.end_date}",
            "notes": [n.serialize() for n in self.notes],
            "catergories": [c.simple_serialize() for c in self.categories]
        }
    
    def simple_serialize(self):
        """
        Serialize an instance of Item without catergories
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "likes": self.likes,
            "dates": f"{self.start_date} - {self.end_date}",
            "notes": [n.serialize() for n in self.notes]
        }


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

    def __init__(self, **kwargs):
        """
        Initialize an instance of User
        """
        self.email = kwargs.get("email")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13)) # encrypts passowrd by hashing
        self.renew_session()

    # not sure if we should serialize username/password
    def serialize(self):
        """
        Serialize and instance of User
        """
        return {
            "id": self.id,
            "items": [i.serialize() for i in self.items]
        }
    

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
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1) # datetime.datetime.now() gives current time, datetime.timedelta(days=1) gives length of a day
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
    base_url = db.Column(db.String, nullable=False)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        self.create(kwargs.get("image_data"))

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

            s3_client = boto.client("s3")
            s3_client.upload_file(img_temploc, S3_BUCKET_NAME, img_filename)

            s3_resource = boto.resource("s3")
            object_acl = s3_resource.OcjectAc(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL="public-read")

            os.remove(img_temploc)

        except Exception as e:
            print(f"Error while uploading image: {e}")



# Item
# User -> integrate into app, add poster field in item
# Category
# Photo
# look up crontab/cronjob