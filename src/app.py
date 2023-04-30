from db import db
# from db import ### MODELS
from db import User
from db import Photo
from db import Item
from db import Note
from db import Category

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


# routes

# Authentication routes (ie. sign up/log in)
# Get items for user with id=1 (GET /api/items/1/)
# Add item for user with id=1 (GET/api/items/1/)
#

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)

