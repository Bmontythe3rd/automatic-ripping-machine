"""Main arm ui file"""
import secrets
import sys  # noqa: F401
import os  # noqa: F401
from getpass import getpass  # noqa: F401
from logging.config import dictConfig
from pathlib import Path
from flask import Flask, logging, current_app  # noqa: F401
from flask.logging import default_handler  # noqa: F401
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_wtf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine
from arm.ripper.logger import short_format

from flask_login import LoginManager
import bcrypt  # noqa: F401
import arm.config.config as cfg

sqlitefile = 'sqlite:///' + cfg.arm_config['DBFILE']


def _load_or_create_secret_key():
    """Persist a per-install Flask secret; override with ARM_SECRET_KEY."""
    env_key = os.environ.get("ARM_SECRET_KEY")
    if env_key:
        return env_key
    db_path = Path(cfg.arm_config["DBFILE"])
    secret_path = db_path.parent / ".arm_secret_key"
    try:
        if secret_path.is_file():
            key = secret_path.read_text(encoding="utf-8").strip()
            if key:
                return key
        key = secrets.token_hex(32)
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_path.write_text(key + "\n", encoding="utf-8")
        try:
            os.chmod(secret_path, 0o600)
        except OSError:
            pass
        return key
    except OSError:
        # Fall back to an ephemeral key if the db dir is not writable
        return secrets.token_hex(32)


# Setup logging, but because of werkzeug issues, we need to set up that later down file
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': short_format,
        'datefmt': cfg.arm_config["DATE_FORMAT"],
    }},
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        "console": {"class": "logging.StreamHandler"},
        "null": {"class": "logging.NullHandler"},
    },
    'root': {
        'level': cfg.arm_config["LOGLEVEL"],
        'handlers': ['wsgi']
    },
})

app = Flask(__name__)
csrf = CSRFProtect()
csrf.init_app(app)
CORS(app, resources={r"/*": {"origins": "*", "send_wildcard": "False"}})

login_manager = LoginManager()
login_manager.init_app(app)

# Set Flask database connection configurations
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitefile
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"timeout": 30},
}
app.config['SECRET_KEY'] = _load_or_create_secret_key()
# Set the global Flask Login state, set to True will ignore any @login_required
app.config['LOGIN_DISABLED'] = cfg.arm_config['DISABLE_LOGIN']
app.logger.debug(f"Disable Login: {cfg.arm_config['DISABLE_LOGIN']}")
# Hide werkzeug console PIN unless explicitly provided
if "WERKZEUG_DEBUG_PIN" not in os.environ:
    os.environ["WERKZEUG_DEBUG_PIN"] = "off"

db = SQLAlchemy(app)
migrate = Migrate(app, db)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Reduce SQLite lock errors under concurrent UI + ripper writers."""
    if connection_record.dialect.name != "sqlite":
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
    finally:
        cursor.close()


# Register route blueprints
# loaded post database declaration to avoid circular loops
from arm.ui.settings.settings import route_settings  # noqa: E402,F811
from arm.ui.logs.logs import route_logs  # noqa: E402,F811
from arm.ui.auth.auth import route_auth  # noqa: E402,F811
from arm.ui.database.database import route_database  # noqa: E402,F811
from arm.ui.history.history import route_history  # noqa: E402,F811
from arm.ui.jobs.jobs import route_jobs  # noqa: E402,F811
from arm.ui.sendmovies.sendmovies import route_sendmovies  # noqa: E402,F811
from arm.ui.notifications.notifications import route_notifications  # noqa: E402,F811
app.register_blueprint(route_settings)
app.register_blueprint(route_logs)
app.register_blueprint(route_auth)
app.register_blueprint(route_database)
app.register_blueprint(route_history)
app.register_blueprint(route_jobs)
app.register_blueprint(route_sendmovies)
app.register_blueprint(route_notifications)

# Remove GET/page loads from logging
import logging  # noqa: E402,F811
logging.getLogger('werkzeug').setLevel(logging.ERROR)
