"""Auth helpers: roles and TOTP."""
from functools import wraps
import secrets
import bcrypt
from flask import redirect, flash, session
from flask_login import current_user, login_required


def _pyotp():
    try:
        import pyotp
        return pyotp
    except ImportError as err:
        raise RuntimeError(
            "pyotp is not installed. Rebuild the Docker image "
            "(pip install pyotp) to enable 2FA."
        ) from err


def admin_required(view):
    """Require authenticated admin role."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            flash("Administrator access required", "danger")
            return redirect("/")
        return view(*args, **kwargs)
    return wrapped


def generate_totp_secret():
    return _pyotp().random_base32()


def totp_uri(secret, username, issuer="ARM"):
    return _pyotp().TOTP(secret).provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret, token):
    if not secret or not token:
        return False
    return _pyotp().TOTP(secret).verify(token.strip().replace(" ", ""), valid_window=1)


def generate_backup_codes(count=8):
    """Return (plaintext_codes, bcrypt hashes)."""
    codes = []
    hashes = []
    for _ in range(count):
        code = secrets.token_hex(4)
        codes.append(code)
        salt = bcrypt.gensalt(12)
        hashes.append(bcrypt.hashpw(code.encode("utf-8"), salt).decode("utf-8"))
    return codes, hashes


def consume_backup_code(user, code):
    """Return True and update user.backup_codes if code matches."""
    if not code:
        return False
    remaining = []
    matched = False
    for hashed in user.get_backup_code_hashes():
        if not matched and bcrypt.checkpw(code.strip().encode("utf-8"), hashed.encode("utf-8")):
            matched = True
            continue
        remaining.append(hashed)
    if matched:
        user.set_backup_code_hashes(remaining)
    return matched


def clear_pending_2fa():
    session.pop("pending_2fa_user_id", None)
