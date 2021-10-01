"User display and login/logout HTMl endpoints."

import datetime
import fnmatch
import http.client
import json
import re

import flask
import werkzeug.security

import anubis.call
from anubis import constants
from anubis import utils
from anubis.saver import BaseSaver


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('users', DESIGN_DOC):
        app.logger.info('Updated users design document.')

DESIGN_DOC = {
    'views': {
        'username': {'reduce': '_count',
                     'map': "function(doc) {if (doc.doctype !== 'user') return; emit(doc.username, null);}"},
        'email': {'map': "function(doc) {if (doc.doctype !== 'user' || !doc.email) return; emit(doc.email, null);}"},
        'role': {'map': "function(doc) {if (doc.doctype !== 'user') return; emit(doc.role, doc.username);}"},
        'status': {'map': "function(doc) {if (doc.doctype !== 'user') return; emit(doc.status, doc.username);}"},
        'last_login': {'map': "function(doc) {if (doc.doctype !== 'user') return; if (!doc.last_login) return; emit(doc.last_login, doc.username);}"},
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
            do_login(username, password)
        except ValueError:
            return utils.error('Invalid user or password, or account disabled.',
                               url=flask.url_for('.login'))
        try:
            return flask.redirect(flask.request.form['next'])
        except KeyError:
            pass
        return flask.redirect(flask.url_for('home'))

    # HEAD request gets here: return No_Content
    return '', 204

@blueprint.route('/logout', methods=['POST'])
def logout():
    "Logout from the user account."
    flask.session.pop('username', None)
    return flask.redirect(flask.url_for('home'))

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    "Register a new user account."
    if utils.http_GET():
        return flask.render_template("user/register.html",
                                     gdpr=utils.get_site_text("gdpr.md"))

    elif utils.http_POST():
        try:
            with UserSaver() as saver:
                saver.set_username(flask.request.form.get('username'))
                saver.set_email(flask.request.form.get('email'))
                if flask.g.am_admin and utils.to_bool(flask.request.form.get('enable')):
                    saver.set_status(constants.ENABLED)
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
                saver.set_call_creator(False)
                saver.set_password()
            user = saver.doc
        except ValueError as error:
            return utils.error(error, flask.url_for('.register'))
        # Directly enabled; send code to the user, if so instructed.
        if user['status'] == constants.ENABLED:
            if utils.to_bool(flask.request.form.get('send_email')):
                send_password_code(user, 'registered')
                utils.flash_message('User account created; an email with a link'
                                    ' to set password has been sent.')
            else:
                utils.flash_message('User account created.')
        # Was set to 'pending'; send email to admins.
        else:
            utils.flash_message('User account created; an email will be sent'
                                ' when it has been enabled by the admin.')
            admins = get_users(role=constants.ADMIN, status=constants.ENABLED)
            recipients = [u['email'] for u in admins if u['email']]
            site = flask.current_app.config['SITE_NAME']
            title = f"{site} user account pending"
            url = flask.url_for('.display', username=user['username'], _external=True)
            text = f"To enable the user account, go to {url}\n\n" \
                   "/The Anubis system"
            utils.send_email(recipients, title, text)
        if flask.g.am_admin:
            return flask.redirect(flask.url_for('user.all'))
        else:
            return flask.redirect(flask.url_for('home'))

@blueprint.route('/reset', methods=['GET', 'POST'])
def reset():
    "Reset the password for a user account and send email."
    if utils.http_GET():
        email = flask.request.args.get('email') or ''
        email = email.lower()
        return flask.render_template('user/reset.html', email=email)

    elif utils.http_POST():
        try:
            user = get_user(email=flask.request.form['email'])
            if user is None: raise KeyError
            if user['status'] != constants.ENABLED: raise KeyError
        except KeyError:
            pass                # Silent when no user found.
        else:
            with UserSaver(user) as saver:
                saver.set_password()
            send_password_code(user, 'password reset')
        # Don't advertise whether user exists or not.
        utils.flash_message(
            'An email has been sent, if the user account exists.')
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
            username = flask.request.form.get('username') or ''
            if not username:
                raise ValueError('No such user or wrong code.')
            user = get_user(username=username)
            if user is None:
                raise ValueError('No such user or wrong code.')
            if flask.g.am_admin:
                code = ''
            else:
                code = flask.request.form.get('code') or ''
                if user['password'] != f"code:{code}":
                    raise ValueError('No such user or wrong code.')
            password = flask.request.form.get('password') or ''
            if len(password) < flask.current_app.config['MIN_PASSWORD_LENGTH']:
                raise ValueError('Too short password.')
        except ValueError as error:
            return utils.error(error, flask.url_for('.password',
                                                    username=username,
                                                    code=code))
        with UserSaver(user) as saver:
            saver.set_password(password)
        utils.flash_message('Password set.')
        if flask.g.am_admin:
            return flask.redirect(flask.url_for('.all'))
        else:
            do_login(username, password)
            return flask.redirect(flask.url_for('home'))

@blueprint.route('/display/<username>')
@utils.login_required
def display(username):
    "Display the given user."
    user = get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not allow_view(user):
        return utils.error('Access to user display not allowed.')
    reviewer_calls = [anubis.call.get_call(r.value)
                      for r in flask.g.db.view('calls', 'reviewer', 
                                               key=user['username'],
                                               reduce=False)]
    user_proposals_count = utils.get_count('proposals', 'user', user['username']) + \
        utils.get_count('proposals', 'access', user['username'])
    return flask.render_template(
        'user/display.html',
        user=user,
        reviewer_calls=reviewer_calls,
        allow_create_call=anubis.call.allow_create(user),
        user_calls_count=utils.get_count('calls', 'owner', user['username']),
        user_proposals_count=user_proposals_count,
        user_reviews_count=utils.get_count('reviews', 'reviewer', user['username']),
        user_grants_count=utils.get_user_grants_count(user['username']),
        allow_enable_disable=allow_enable_disable(user),
        allow_edit=allow_edit(user),
        allow_delete=allow_delete(user),
        gdpr=utils.get_site_text("gdpr.md"))

@blueprint.route('/display/<username>/edit',
                 methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(username):
    "Edit the user. Or delete the user."
    user = get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not allow_edit(user):
        return utils.error('Access to user edit not allowed.')

    if utils.http_GET():
        return flask.render_template('user/edit.html',
                                     user=user,
                                     allow_change_role=allow_change_role(user))

    elif utils.http_POST():
        try:
            with UserSaver(user) as saver:
                if flask.g.am_admin:
                    email = flask.request.form.get('email')
                    saver.set_email(email, require=bool(email))
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
                if allow_change_role(user):
                    saver.set_role(flask.request.form.get('role'))
                    saver.set_call_creator(
                        utils.to_bool(flask.request.form.get('call_creator')))
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(
            flask.url_for('.display', username=user['username']))

    elif utils.http_DELETE():
        if not allow_delete(user):
            return utils.error('Cannot delete the user account; admin or not empty.',
                               flask.url_for('.display', username=username))
        flask.g.db.delete(user)
        utils.flash_message(f"Deleted user {username}.")
        if flask.g.am_admin:
            return flask.redirect(flask.url_for('.all'))
        else:
            return flask.redirect(flask.url_for('home'))

@blueprint.route('/logs/<username>')
@utils.login_required
def logs(username):
    "Display the log records for the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not allow_view(user):
        return utils.error('Access to user logs not allowed.')
    return flask.render_template(
        'logs.html',
        title=f"User {user['username']}",
        back_url=flask.url_for('.display', username=user['username']),
        logs=utils.get_logs(user['_id']))

@blueprint.route('/all')
@utils.admin_or_staff_required
def all():
    "Display list of all user accounts."
    users = get_users()
    result = flask.g.db.view('proposals', 'user', group_level=1, reduce=True)
    proposals_counts = dict([(r.key, r.value) for r in result])
    result = flask.g.db.view('reviews', 'reviewer', group_level=1, reduce=True)
    reviews_counts = dict([(r.key, r.value) for r in result])
    result = flask.g.db.view('grants', 'user', group_level=1, reduce=True)
    grants_counts = dict([(r.key, r.value) for r in result])
    result = flask.g.db.view('grants', 'access', group_level=1, reduce=True)
    for row in result:
        try:
            grants_counts[row.key] += row.value
        except KeyError:
            grants_counts[row.key] = row.value
    for user in users:
        username = user['username']
        user['all_proposals_count'] = proposals_counts.get(username)
        user['all_reviews_count'] = reviews_counts.get(username)
        user['all_grants_count'] = grants_counts.get(username)
    return flask.render_template('user/all.html', users=users)

@blueprint.route('/pending')
@utils.admin_or_staff_required
def pending():
    "Display list of all pending user accounts."
    users = get_users(status=constants.PENDING)
    return flask.render_template('user/pending.html', users=users)

@blueprint.route('/enable/<username>', methods=['POST'])
@utils.admin_required
def enable(username):
    "Enable the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    with UserSaver(user) as saver:
        saver.set_status(constants.ENABLED)
        saver.set_password()
    send_password_code(user, 'enabled')
    utils.flash_message('User account enabled; email sent.')
    return flask.redirect(flask.url_for('.display', username=username))

@blueprint.route('/disable/<username>', methods=['POST'])
@utils.admin_required
def disable(username):
    "Disable the given user account."
    user = get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    with UserSaver(user) as saver:
        saver.set_status(constants.DISABLED)
    return flask.redirect(flask.url_for('.display', username=username))


class UserSaver(BaseSaver):
    "User document saver context manager."

    DOCTYPE = constants.USER
    HIDDEN_FIELDS = ['password']

    def initialize(self):
        "Set the status for a new user."
        if flask.current_app.config['USER_ENABLE_IMMEDIATELY']:
            self.doc['status'] = constants.ENABLED
        else:
            self.doc['status'] = constants.PENDING

    def finish(self):
        "Check that required fields have been set."
        for key in ['username', 'role', 'status']:
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

    def set_email(self, email, require=True):
        if email:
            if email == self.doc.get('email'): return
            email = email.lower()
            if not constants.EMAIL_RX.match(email):
                raise ValueError('invalid email')
            if get_user(email=email):
                raise ValueError('email already in use')
            self.doc['email'] = email
            if self.doc.get('status') == constants.PENDING:
                # Filename matching instead of regexp; easier to specify.
                for ep in flask.current_app.config['USER_ENABLE_EMAIL_WHITELIST']:
                    if fnmatch.fnmatch(email, ep):
                        self.set_status(constants.ENABLED)
                        break
        elif require:
            raise ValueError('No email address provided.')
        else:
            self.doc['email'] = None

    def set_status(self, status):
        if status not in constants.USER_STATUSES:
            raise ValueError('invalid status')
        self.doc['status'] = status

    def set_role(self, role):
        if role not in constants.USER_ROLES:
            raise ValueError('invalid role')
        self.doc['role'] = role

    def set_call_creator(self, yes):
        self.doc['call_creator'] = bool(yes)

    def set_password(self, password=None):
        "Set the password; a one-time code if no password provided."
        config = flask.current_app.config
        if password:
            if len(password) < config['MIN_PASSWORD_LENGTH']:
                raise ValueError('password too short')
            self.doc['password'] = werkzeug.security.generate_password_hash(
                password, salt_length=config['SALT_LENGTH'])
        else:
            self.doc['password'] = "code:%s" % utils.get_iuid()

    def set_last_login(self):
        self.doc['last_login'] = utils.get_time()

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


def get_user(username=None, email=None):
    """Return the user for the given username or email.
    Return None if no such user.
    """
    if username:
        key = f"username {username}"
        try:
            return flask.g.cache[key]
        except KeyError:
            docs = [r.doc for r in flask.g.db.view('users', 'username', 
                                                   key=username,
                                                   include_docs=True)]
            if len(docs) == 1:
                user = docs[0]
                flask.g.cache[key] = user
                if user['email']:
                    flask.g.cache[f"email {user['email']}"] = user
                return user
            else:
                return None
    elif email:
        email = email.lower()
        key = f"email {email}"
        try:
            return flask.g.cache[key]
        except KeyError:
            docs = [r.doc for r in flask.g.db.view('users', 'email',
                                                   key=email,
                                                   include_docs=True)]
            if len(docs) == 1:
                user = docs[0]
                flask.g.cache[key] = user
                flask.g.cache[f"username {user['username']}"] = user
                return user
            else:
                return None
    else:
        return None

def get_users(role=None, status=None, safe=False):
    "Return the users specified by role and optionally by status."
    assert role is None or role in constants.USER_ROLES
    assert status is None or status in constants.USER_STATUSES
    if role is None:
        if status is None:
            result = [r.doc for r in 
                      flask.g.db.view('users', 'role', include_docs=True)]
        else:
            result = [r.doc for r in 
                      flask.g.db.view('users', 'status',
                                      key=status, include_docs=True)]
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
    if not user: raise ValueError
    if not password: raise ValueError
    if not werkzeug.security.check_password_hash(user['password'], password):
        raise ValueError
    if user['status'] != constants.ENABLED:
        raise ValueError
    with UserSaver(user) as saver:
        saver.set_last_login()
    flask.session['username'] = user['username']
    flask.session.permanent = True

def send_password_code(user, action):
    """Send an email with the one-time code to the user's email address.
    No action if no email address for user.
    """
    if not user['email']: return
    site = flask.current_app.config['SITE_NAME']
    title = f"{site} user account {action}"
    url = flask.url_for('.password',
                        username=user['username'],
                        code=user['password'][len('code:'):],
                        _external=True)
    if action == 'registration':
        action = 'has been created'
    elif action == 'password reset':
        action = 'has had its password reset'
    elif action == 'enabled':
        action = 'has been enabled'
    text = f"Your account {user['username']} in the {site} system" \
           f" {action}.\n\nTo set your password, go to {url}\n\n" \
           "/The Anubis system"
    utils.send_email(user['email'], title, text)

def am_admin(user=None):
    "Is the user admin? Default user: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['role'] == constants.ADMIN

def am_staff(user=None):
    "Is the user staff? Default user: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['role'] == constants.STAFF

def allow_view(user):
    """Is the current user allowed to view the user account?
    Yes, if current user is admin, staff or self.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    if flask.g.current_user['username'] == user['username']: return True
    return False

def allow_edit(user):
    """Is the current user allowed to edit the user account?
    Yes, if current user is admin or self.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user['username'] == user['username']: return True
    return False

def allow_delete(user):
    """Can the the given user account be deleted? 
    Only when user is not admin, and has no proposals and no reviews,
    and is not reviewer in any call.
    Note that the user herself may be able to delete the account.
    """
    if user['role'] == constants.ADMIN: return False
    if utils.get_count('proposals', 'user', user['username']): return False
    if utils.get_count('reviews', 'reviewer', user['username']): return False
    if utils.get_count('calls', 'reviewer', user['username']): return False
    return True

def allow_enable_disable(user):
    """Is the current user allowed to enable or disable the user account?
    Yes, if current user is admin an not self.
    """
    if flask.g.am_admin and \
       flask.g.current_user['username'] != user['username']: return True
    return False

def allow_change_role(user):
    """Is the current user allowed to change the role of the user account?
    Yes, if current user is admin an not self.
    """
    if flask.g.am_admin and \
       flask.g.current_user['username'] != user['username']: return True
    return False
