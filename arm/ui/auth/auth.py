"""
ARM route blueprint for auth pages
Covers
- user_loader [GET, POST]
- unauthorized_handler [GET]
- login [GET, POST]
- login/2fa [GET, POST]
- logout [GET]
- update_password [GET, POST]
- account / 2FA setup
- users admin
"""
from sqlite3 import OperationalError
import base64
import io
import bcrypt
from flask import redirect, render_template, request, Blueprint, flash, session
from flask_login import LoginManager, login_required, \
    current_user, login_user, logout_user  # noqa: F401

from arm.ui import app, db, constants   # noqa: F811
from arm.models.user import User
from arm.ui.forms import SetupForm, DBUpdate, PasswordReset, TotpForm, UserCreateForm
from arm.ui import auth_utils
import arm.ui.utils as ui_utils

route_auth = Blueprint('route_auth', __name__,
                       template_folder='templates',
                       static_folder='../static')

# Define the Flask login manager
login_manager = LoginManager()
login_manager.init_app(app)


def _qr_data_uri(otpauth_uri):
    try:
        import qrcode
        img = qrcode.make(otpauth_uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


@route_auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page if login is enabled
    :return: redirect
    """
    page_support_databaseupdate = "support/databaseupdate.html"

    # Check the database is current
    db_update = ui_utils.arm_db_check()
    if not db_update["db_current"] or not db_update["db_exists"]:
        dbform = DBUpdate(request.form)
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    return_redirect = None
    try:
        user_list = User.query.all()
        if not user_list:
            app.logger.error("No admin found")
    except OperationalError as e:
        flash(constants.NO_ADMIN_ACCOUNT, "danger")
        app.logger.error(constants.NO_ADMIN_ACCOUNT)
        app.logger.error(f"ERROR: Missing Data in the ARM User Table: {e}")
        dbform = DBUpdate(request.form)
        db_update = ui_utils.arm_db_check()
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    if current_user.is_authenticated:
        return_redirect = redirect(constants.HOME_PAGE)

    form = SetupForm()
    if form.validate_on_submit():
        login_username = form.username.data.strip()
        login_password = form.password.data.strip().encode('utf-8')
        user = User.query.filter_by(email=login_username).first()
        app.logger.debug("user= " + str(user))
        if user and user.is_active is not False:
            login_hashed = bcrypt.hashpw(login_password, user.hash)
            if login_hashed == user.password:
                if user.totp_enabled and user.totp_secret:
                    session["pending_2fa_user_id"] = user.user_id
                    session.modified = True
                    return redirect("/login/2fa")
                login_user(user)
                session.modified = True
                app.logger.debug("user was logged in - redirecting")
                return_redirect = redirect(constants.HOME_PAGE)
            else:
                flash("Something isn't right", "danger")
        else:
            flash("Something isn't right", "danger")

    if request.method == 'GET' or return_redirect is None:
        return_redirect = render_template('login.html', form=form)

    return return_redirect


@route_auth.route('/login/2fa', methods=['GET', 'POST'])
def login_2fa():
    """Complete login with TOTP or backup code."""
    pending_id = session.get("pending_2fa_user_id")
    if not pending_id:
        return redirect("/login")
    user = User.query.get(int(pending_id))
    if not user:
        auth_utils.clear_pending_2fa()
        return redirect("/login")

    form = TotpForm()
    if form.validate_on_submit():
        token = form.token.data.strip()
        ok = auth_utils.verify_totp(user.totp_secret, token)
        if not ok:
            ok = auth_utils.consume_backup_code(user, token)
            if ok:
                db.session.commit()
        if ok:
            auth_utils.clear_pending_2fa()
            login_user(user)
            session.modified = True
            flash("Logged in", "success")
            return redirect(constants.HOME_PAGE)
        flash("Invalid authentication code", "danger")

    return render_template('login_2fa.html', form=form, username=user.email)


@route_auth.route("/logout")
def logout():
    """
    Log user out
    :return:
    """
    auth_utils.clear_pending_2fa()
    logout_user()
    flash("logged out", "success")
    return redirect('/')


@route_auth.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    """
    updating the password for the current account
    """
    user = current_user
    session["page_title"] = "Update Password"

    form = PasswordReset()

    if form.validate_on_submit():
        username = form.username.data.strip()
        new_password = form.new_password.data.strip().encode('utf-8')
        old_password = form.old_password.data.strip().encode('utf-8')

        user = User.query.filter_by(email=username).first()
        if not user or user.user_id != current_user.user_id:
            flash("You can only change your own password", "danger")
            return render_template('update_password.html', user=current_user.email, form=form)

        current_password = user.password
        hashed = user.hash
        login_hashed = bcrypt.hashpw(old_password, hashed)

        if login_hashed == current_password:
            hashed_password = bcrypt.hashpw(new_password, hashed)
            user.password = hashed_password
            user.hash = hashed
            try:
                db.session.commit()
                flash("Password successfully updated", "success")
                app.logger.info("Password successfully updated")
                return redirect("logout")
            except Exception as error:
                flash(str(error), "danger")
                app.logger.error(f"Error in updating password: {error}")
        else:
            flash("Current password does not match", "danger")
            app.logger.error("Current password does not match")

    return render_template('update_password.html', user=user.email, form=form)


@route_auth.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    """Account page: enable/disable TOTP 2FA."""
    session["page_title"] = "Account"
    user = User.query.get(current_user.user_id)
    form = TotpForm()
    pending_secret = session.get("pending_totp_secret")
    qr_uri = None
    backup_codes = session.pop("show_backup_codes", None)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start_2fa":
            secret = auth_utils.generate_totp_secret()
            session["pending_totp_secret"] = secret
            session.modified = True
            pending_secret = secret
            flash("Scan the QR code, then enter a code to confirm", "info")
        elif action == "confirm_2fa" and form.validate_on_submit() and pending_secret:
            if auth_utils.verify_totp(pending_secret, form.token.data):
                codes, hashes = auth_utils.generate_backup_codes()
                user.totp_secret = pending_secret
                user.totp_enabled = True
                user.set_backup_code_hashes(hashes)
                db.session.commit()
                session.pop("pending_totp_secret", None)
                session["show_backup_codes"] = codes
                flash("Two-factor authentication enabled. Save your backup codes.", "success")
                return redirect("/account")
            flash("Invalid code — try again", "danger")
        elif action == "disable_2fa" and form.validate_on_submit():
            if user.totp_enabled and auth_utils.verify_totp(user.totp_secret, form.token.data):
                user.totp_enabled = False
                user.totp_secret = None
                user.backup_codes = None
                db.session.commit()
                flash("Two-factor authentication disabled", "success")
                return redirect("/account")
            flash("Invalid code", "danger")

    if pending_secret:
        otpauth = auth_utils.totp_uri(pending_secret, user.email)
        qr_uri = _qr_data_uri(otpauth)
    else:
        otpauth = None

    return render_template(
        "account.html",
        user=user,
        form=form,
        pending_secret=pending_secret,
        otpauth=otpauth,
        qr_uri=qr_uri,
        backup_codes=backup_codes,
    )


@route_auth.route('/users', methods=['GET', 'POST'])
@auth_utils.admin_required
def users_admin():
    """Admin user management."""
    session["page_title"] = "Users"
    form = UserCreateForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        if User.query.filter_by(email=username).first():
            flash("User already exists", "danger")
        else:
            salt = bcrypt.gensalt(12)
            password = form.password.data.strip().encode("utf-8")
            new_user = User(
                email=username,
                password=bcrypt.hashpw(password, salt),
                hashed=salt,
                role=form.role.data,
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f"Created user {username}", "success")
            return redirect("/users")

    action = request.args.get("action")
    uid = request.args.get("id")
    if action and uid:
        target = User.query.get(int(uid))
        if target:
            if action == "disable" and target.user_id != current_user.user_id:
                target.is_active = False
                db.session.commit()
                flash("User disabled", "success")
            elif action == "enable":
                target.is_active = True
                db.session.commit()
                flash("User enabled", "success")
            elif action == "clear_2fa" and target.user_id != current_user.user_id:
                target.totp_enabled = False
                target.totp_secret = None
                target.backup_codes = None
                db.session.commit()
                flash("Cleared 2FA for user", "success")
            elif action == "reset_password":
                salt = bcrypt.gensalt(12)
                new_pw = "password"
                target.password = bcrypt.hashpw(new_pw.encode("utf-8"), salt)
                target.hash = salt
                db.session.commit()
                flash(f"Password reset to '{new_pw}' for {target.email}", "warning")
        return redirect("/users")

    users = User.query.order_by(User.user_id).all()
    return render_template("users.html", users=users, form=form)


@login_manager.user_loader
def load_user(user_id):
    """
    Logged in check
    :param user_id:
    :return:
    """
    try:
        return User.query.get(int(user_id))
    except OperationalError as e:
        app.logger.error("Error getting user")
        app.logger.error(f"ERROR: {e}")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
    User isn't authorised to view the requested page
    :return: redirect to login page
    """
    return redirect('/login')
