"User display and login/logout HTMl endpoints."

import datetime
import http.client
import json
import re

import flask
import flask_mail
import werkzeug.security

from . import constants
from . import utils
from .saver import BaseSaver


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    logger = utils.get_logger(app)
    if db.put_design('users', DESIGN_DOC):
        logger.info('Updated users design document.')

DESIGN_DOC = {
    'views': {
        'username': {'map': "function(doc) {if (doc.doctype !== 'user') return; emit(doc.username, null);}"},
        'email': {'map': "function(doc) {if (doc.doctype !== 'user') return;  emit(doc.email, null);}"},
        'role': {'map': "function(doc) {if (doc.doctype !== 'user') return;  emit(doc.role, null);}"},
    }
}

blueprint = flask.Blueprint('user', __name__)

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    "Login to a user account."
    if utils.http_GET():
        return flask.render_template('user/login.html',
                                     next=flask.request.args.get('next'))
    if utils.http_POST():
        username = flask.request.form.get('username')
        password = flask.request.form.get('password')
        try:
            if username and password:
                do_login(username, password)
            else:
                raise ValueError
            try:
                next = flask.request.form['next']
            except KeyError:
                return flask.redirect(flask.url_for('home'))
            else:
                return flask.redirect(next)
        except ValueError:
            utils.flash_error('Invalid user/password, or account disabled.')
            return flask.redirect(flask.url_for('.login'))

@blueprint.route('/logout', methods=['POST'])
def logout():
    "Logout from the user account."
    username = flask.session.pop('username', None)
    if username:
        utils.get_logger().info(f"logged out {username}")
    return flask.redirect(flask.url_for('home'))

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    "Register a new user account."
    if utils.http_GET():
        return flask.render_template('user/register.html')

    elif utils.http_POST():
        try:
            with UserSaver() as saver:
                saver.set_username(flask.request.form.get('username'))
                saver.set_email(flask.request.form.get('email'))
                saver['givenname'] = flask.request.form.get('givenname') or None
                saver['familyname'] = flask.request.form.get('familyname') or None
                if flask.current_app.config['USER_GENDERS']:
                    saver.set_gender(flask.request.form.get('gender'))
                if flask.current_app.config['USER_BIRTHDATE']:
                    saver.set_birthdate(flask.request.form.get('birthdate'))
                if flask.current_app.config['USER_TITLE']:
                    saver['title'] = flask.request.form.get('title') or None
                if flask.current_app.config['USER_AFFILIATION']:
                    saver['affiliation'] = flask.request.form.get('affiliation') or None
                if flask.current_app.config['USER_POSTAL_ADDRESS']:
                    saver['postaladdress'] = flask.request.form.get('postaladdress') or None
                if flask.current_app.config['USER_PHONE']:
                    saver['phone'] = flask.request.form.get('phone') or None
                saver.set_role(constants.USER)
                saver.set_password()
            user = saver.doc
        except ValueError as error:
            utils.flash_error(error)
            return flask.redirect(flask.url_for('.register'))
        utils.get_logger().info(f"registered user {user['username']}")
        # Directly enabled; send code to the user.
        if user['status'] == constants.ENABLED:
            send_password_code(user, 'registration')
            utils.get_logger().info(f"enabled user {user['username']}")
            utils.flash_message('User account created; check your email.')
        # Was set to 'pending'; send email to admins.
        else:
            admins = get_users(constants.ADMIN, status=constants.ENABLED)
            emails = [u['email'] for u in admins]
            site = flask.current_app.config['SITE_NAME']
            message = flask_mail.Message(f"{site} user account pending",
                                         recipients=emails)
            url = utils.url_for('.display', username=user['username'])
            message.body = f"To enable the user account, go to {url}"
            utils.mail.send(message)
            utils.get_logger().info(f"pending user {user['username']}")
            utils.flash_message('User account created; an email will be sent'
                                ' when it has been enabled by the admin.')
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/reset', methods=['GET', 'POST'])
def reset():
    "Reset the password for a user account and send email."
    if utils.http_GET():
        return flask.render_template('user/reset.html',
                                     email=flask.request.args.get('email') or '')

    elif utils.http_POST():
        try:
            user = get_user(email=flask.request.form['email'])
            if user is None: raise KeyError
            if user['status'] != constants.ENABLED: raise KeyError
        except KeyError:
            pass
        else:
            with UserSaver(user) as saver:
                saver.set_password()
            send_password_code(user, 'password reset')
        utils.get_logger().info(f"reset user {user['username']}")
        utils.flash_message('An email has been sent if the user account exists.')
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/password', methods=['GET', 'POST'])
def password():
    "Set the password for a user account, and login user."
    if utils.http_GET():
        return flask.render_template(
            'user/password.html',
            username=flask.request.args.get('username'),
            code=flask.request.args.get('code'))

    elif utils.http_POST():
        try:
            username = flask.request.form['username']
            if not username: raise KeyError
            user = get_user(username=username)
            if user is None: raise KeyError
            if user['password'] != "code:{}".format(flask.request.form['code']):
                raise KeyError
            password = flask.request.form.get('password') or ''
            if len(password) < flask.current_app.config['MIN_PASSWORD_LENGTH']:
                raise ValueError
        except KeyError:
            utils.flash_error('No such user or wrong code.')
        except ValueError:
            utils.flash_error('Too short password.')
        else:
            with UserSaver(user) as saver:
                saver.set_password(password)
            utils.get_logger().info(f"password user {user['username']}")
            do_login(username, password)
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/display/<username>')
@utils.login_required
def display(username):
    "Display the given user."
    from .proposals import get_proposals_count
    user = get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not is_admin_or_self(user):
        utils.flash_error('Access not allowed.')
        return flask.redirect(flask.url_for('home'))
    user['reviewer'] = [r.value for r in flask.g.db.view('calls', 'reviewer',
                                                         key=user['username'])]
    user['proposals_count'] = get_proposals_count(username=user['username'])
    return flask.render_template('user/display.html',
                                 user=user,
                                 enable_disable=is_admin_and_not_self(user),
                                 deletable=is_deletable(user))

@blueprint.route('/display/<username>/edit',
                 methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(username):
    "Edit the user display. Or delete the user."
    user = get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not is_admin_or_self(user):
        utils.flash_error('Access not allowed.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('user/edit.html',
                                     user=user,
                                     change_role=is_admin_and_not_self(user))

    elif utils.http_POST():
        with UserSaver(user) as saver:
            if flask.g.is_admin:
                email = flask.request.form.get('email')
                if email != user['email']:
                    saver.set_email(email)
            saver['givenname'] = flask.request.form.get('givenname') or None
            saver['familyname'] = flask.request.form.get('familyname') or None
            if flask.current_app.config['USER_GENDERS']:
                saver.set_gender(flask.request.form.get('gender'))
            if flask.current_app.config['USER_BIRTHDATE']:
                saver.set_birthdate(flask.request.form.get('birthdate'))
            if flask.current_app.config['USER_TITLE']:
                saver['title'] = flask.request.form.get('title') or None
            if flask.current_app.config['USER_AFFILIATION']:
                saver['affiliation'] = flask.request.form.get('affiliation') or None
            if flask.current_app.config['USER_POSTAL_ADDRESS']:
                saver['postaladdress'] = flask.request.form.get('postaladdress') or None
            if flask.current_app.config['USER_PHONE']:
                saver['phone'] = flask.request.form.get('phone') or None
            if is_admin_and_not_self(user):
                saver.set_role(flask.request.form.get('role'))
        return flask.redirect(
            flask.url_for('.display', username=user['username']))

    elif utils.http_DELETE():
        if not is_deletable(user):
            utils.flash_error('Cannot delete the user account; admin or not empty.')
            return flask.redirect(flask.url_for('.display', username=username))
        flask.g.db.delete(user)
        utils.flash_message(f"Deleted user {username}.")
        utils.get_logger().info(f"deleted user {username}")
        if flask.g.is_admin:
            return flask.redirect(flask.url_for('.users'))
        else:
            return flask.redirect(flask.url_for('home'))

@blueprint.route('/logs/<username>')
@utils.login_required
def logs(username):
    "Display the log records of the given user."
    user = get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not is_admin_or_self(user):
        utils.flash_error('Access not allowed.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'logs.html',
        title=f"User {user['username']}",
        back_url=flask.url_for('.display', username=user['username']),
        logs=utils.get_logs(user['_id']))

@blueprint.route('/all')
@utils.admin_required
def all():
    "Display list of all users."
    from .proposals import get_proposals_count
    users = get_users(role=None)
    for user in users:
        user['proposals_count'] = get_proposals_count(username=user['username'])
    return flask.render_template('user/all.html', users=users)

@blueprint.route('/enable/<username>', methods=['POST'])
@utils.admin_required
def enable(username):
    "Enable the given user account."
    user = get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    with UserSaver(user) as saver:
        saver.set_status(constants.ENABLED)
        saver.set_password()
    send_password_code(user, 'enabled')
    utils.get_logger().info(f"enabled user {username}")
    return flask.redirect(flask.url_for('.display', username=username))

@blueprint.route('/disable/<username>', methods=['POST'])
@utils.admin_required
def disable(username):
    "Disable the given user account."
    user = get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    with UserSaver(user) as saver:
        saver.set_status(constants.DISABLED)
    utils.get_logger().info(f"disabled user {username}")
    return flask.redirect(flask.url_for('.display', username=username))


class UserSaver(BaseSaver):
    "User document saver context."

    DOCTYPE = constants.USER
    HIDDEN_FIELDS = ['password']

    def initialize(self):
        "Set the status for a new user."
        if flask.current_app.config['USER_ENABLE_IMMEDIATELY']:
            self.doc['status'] = constants.ENABLED
        else:
            self.doc['status'] = constants.PENDING

    def finalize(self):
        "Check that required fields have been set."
        for key in ['username', 'email', 'role', 'status']:
            if not self.doc.get(key):
                raise ValueError("invalid user: %s not set" % key)

    def set_username(self, username):
        if 'username' in self.doc:
            raise ValueError('username cannot be changed')
        if not constants.ID_RX.match(username):
            raise ValueError('invalid username; must be an identifier')
        if get_user(username=username):
            raise ValueError('username already in use')
        self.doc['username'] = username

    def set_email(self, email):
        if not constants.EMAIL_RX.match(email):
            raise ValueError('invalid email')
        if get_user(email=email):
            raise ValueError('email already in use')
        self.doc['email'] = email
        if self.doc.get('status') == constants.PENDING:
            for rx in flask.current_app.config['USER_ENABLE_EMAIL_WHITELIST']:
                if re.match(rx, email):
                    self.set_status(constants.ENABLED)
                    break

    def set_status(self, status):
        if status not in constants.USER_STATUSES:
            raise ValueError('invalid status')
        self.doc['status'] = status

    def set_role(self, role):
        if role not in constants.USER_ROLES:
            raise ValueError('invalid role')
        self.doc['role'] = role

    def set_password(self, password=None):
        "Set the password; a one-time code if no password provided."
        config = flask.current_app.config
        if password is None:
            self.doc['password'] = "code:%s" % utils.get_iuid()
        else:
            if len(password) < config['MIN_PASSWORD_LENGTH']:
                raise ValueError('password too short')
            self.doc['password'] = werkzeug.security.generate_password_hash(
                password, salt_length=config['SALT_LENGTH'])


    def set_gender(self, gender):
        if gender not in flask.current_app.config['USER_GENDERS']:
            gender = None
        self.doc['gender'] = gender

    def set_birthdate(self, birthdate):
        if birthdate:
            try:
                datetime.datetime.strptime(birthdate, "%Y-%m-%d")
            except ValueError:
                birthdate = None
        self.doc['birthdate'] = birthdate


# Utility functions

def get_user(username=None, email=None, safe=False):
    """Return the user for the given username or email.
    Return None if no such user.
    """
    user = None
    if username:
        rows = flask.g.db.view('users', 'username', 
                               key=username, include_docs=True)
        if len(rows) == 1:
            user = rows[0].doc
    if user is None and email:
        rows = flask.g.db.view('users', 'email',
                               key=email, include_docs=True)
        if len(rows) == 1:
            user = rows[0].doc
    if user and safe:
        user['iuid'] = user.pop('_id')
        user.pop('_rev')
        user.pop('password', None)
    return user

def get_users(role, status=None, safe=False):
    "Get the users specified by role and optionally by status."
    assert role is None or role in constants.USER_ROLES
    assert status is None or status in constants.USER_STATUSES
    if role is None:
        result = [r.doc for r in 
                  flask.g.db.view('users', 'role', include_docs=True)]
    else:
        result = [r.doc for r in 
                  flask.g.db.view('users', 'role', key=role, include_docs=True)]
    if status is not None:
        result = [d for d in result if d['status'] == status]
    if safe:
        for user in result:
            user['iuid'] = user.pop('_id')
            user.pop('_rev')
            user.pop('password', None)
    return result

def get_current_user():
    """Return the user for the current session.
    Return None if no such user, or disabled.
    """
    user = get_user(username=flask.session.get('username'))
    if user is None or user['status'] != constants.ENABLED:
        flask.session.pop('username', None)
        return None
    return user

def do_login(username, password):
    """Set the session cookie if successful login.
    Raise ValueError if some problem.
    """
    user = get_user(username=username)
    if user is None: raise ValueError
    if not werkzeug.security.check_password_hash(user['password'], password):
        raise ValueError
    if user['status'] != constants.ENABLED:
        raise ValueError
    flask.session['username'] = user['username']
    flask.session.permanent = True
    utils.get_logger().info(f"logged in {user['username']}")

def send_password_code(user, action):
    "Send an email with the one-time code to the user's email address."
    site = flask.current_app.config['SITE_NAME']
    message = flask_mail.Message(f"{site} user account {action}",
                                 recipients=[user['email']])
    url = utils.url_for('.password',
                        username=user['username'],
                        code=user['password'][len('code:'):])
    message.body = f"To set your password, go to {url}"
    utils.mail.send(message)

def is_deletable(user):
    """Can the the given user account be deleted? 
    Only when no proposals and not admin.
    """
    from .proposals import get_proposals_count
    if user['role'] == constants.ADMIN: return False
    return not bool(get_proposals_count(username=user['username']))

def is_admin_or_self(user):
    "Is the current user admin, or the same as the given user?"
    if not flask.g.current_user: return False
    if flask.g.is_admin: return True
    return flask.g.current_user['username'] == user['username']

def is_admin_and_not_self(user):
    "Is the current user admin, but not the same as the given user?"
    if flask.g.is_admin:
        return flask.g.current_user['username'] != user['username']
    return False
