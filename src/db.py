from flask_sqlalchemy import SQLAlchemy

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
    name = db.Column(db.String, nullable=False)
    # dates = db.relationship() -> have as separate table
    # photo = db.relationship()
    notes = db.relationship("Note", cascade="delete")
    categories = db.relationship("Category", secondary=association_table, back_populates='items')

    def __init__(self, **kwargs):
        self.name = kwargs.get('name')


class Note(db.Model):
    """
    Model for note
    """
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.String, nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)

    def __init__(self, **kwargs):
        self.content = kwargs.get('content')
        self.item_id = kwargs.get('item_id')


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
        self.name = kwargs.get('name')
        self.color = kwargs.get('color')

# Item
# User
# Category
# dates -> to have multiple dates for an event, maybe a many-to-many type thing
