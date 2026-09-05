from flask_login import UserMixin
import json

from arm.ui import db


class User(db.Model, UserMixin):
    """
    Class to hold ARM users (admin / operator)
    """
    user_id = db.Column(db.Integer, index=True, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(128))
    hash = db.Column(db.String(256))
    role = db.Column(db.String(32), default="admin", nullable=False)
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)
    backup_codes = db.Column(db.Text, nullable=True)  # JSON list of bcrypt hashes
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __init__(self, email=None, password=None, hashed=None, role="admin"):
        self.email = email
        self.password = password
        self.hash = hashed
        self.role = role or "admin"
        self.totp_enabled = False
        self.is_active = True

    def __repr__(self):
        """ Return users name """
        return f'<User {self.email}>'

    def __str__(self):
        """Returns a string of the object"""
        return self.__class__.__name__ + ": " + self.email

    def get_id(self):
        """ Return users id """
        return self.user_id

    @property
    def is_admin(self):
        return (self.role or "admin") == "admin"

    def get_backup_code_hashes(self):
        if not self.backup_codes:
            return []
        try:
            return json.loads(self.backup_codes)
        except (TypeError, ValueError):
            return []

    def set_backup_code_hashes(self, hashes):
        self.backup_codes = json.dumps(hashes)
