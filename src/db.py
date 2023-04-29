from flask_sqlalchemy import SQLAlchemy

import datetime
import hashlib
import os

import bcrypt

db = SQLAlchemy()

association_table = db.Table(
    "association", db.Model.metadata,
    db.Column("item_id", db.Integer, db.ForeignKey("task.id")),
    db.Column("category_id", db.Integer, db.ForeignKey("category.id"))
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
    # photo = db.relationship()
    categories = db.relationship("Category", secondary=association_table, back_populates='items')
    # public = db.relationship(db.Boolean, nullable=False), lets user set public or private items

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')

    def serialize(self):
        """
        Serialize an instance of Item
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "dates": [d.serialize() for d in self.dates],
            "notes": [n.serialize() for n in self.notes],
            "catergories": [c.serialize() for c in self.categories]
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
    color = db.Column(db.String, nullable=False)
    items = db.relationship("Item", secondary=association_table, back_populates='categories')

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.color = kwargs.get("color", "")

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

class Photo(db.Model):
    """
    Model for photo
    """
    pass


# Item
# User -> integrate into app more, add poster field in item
# Category
# Photo
# look up crontab/cronjob