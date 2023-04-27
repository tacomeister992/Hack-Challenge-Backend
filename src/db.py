from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

association_table = db.Table(
    "association",
    db.Column("item_id", db.Integer, db.ForeignKey("items.id")),
     db.Column("note_id", db.Integer, db.ForeignKey("notes.id"))
)

# Models
class Item(db.Model):
    """
    Model for item
    """

    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    name = db.Column(db.String, nullable=False)
    # dates = db.relationship() -> have as seperate table
    # photo = db.relationship()
    notes = db.relationship("Note", cascade="delete")


class Note(db.Model):
    """
    Model for note
    """
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    content = db.Column(db.String, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)


# Item
# User
# Category
# dates -> to have multiple dates for an event, maybe a many-to-many type thing
