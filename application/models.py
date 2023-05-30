
from application import db
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class User(db.Document):
    user_id = db.IntField(unique=True)
    first_name = db.StringField(max_length=50)
    last_name = db.StringField(max_length=50)
    email = db.StringField(max_length=30, unique=True)
    password = db.StringField()

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def get_password(self, password):
        return check_password_hash(self.password, password)

class Note(db.Document):
    content = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.datetime.utcnow)

class ChatRoom(db.Document):
    room_name = db.StringField(required=True, unique=True)
    password = db.StringField(required=True)
    users = db.ListField(db.ReferenceField(User))

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    meta = {'indexes': ['room_name']}

class ChatMessage(db.Document):
    room = db.ReferenceField(ChatRoom)
    user = db.ReferenceField(User)
    message = db.StringField(max_length=255)
    created_at = db.DateTimeField(default=datetime.datetime.now)

    meta = {
        'ordering': ['-created_at']
    }

class Availability(db.Document):
    user = db.ReferenceField(User)
    day = db.StringField(required=True)
    status = db.StringField(default='')

    meta = {'indexes': ['user', 'day']}