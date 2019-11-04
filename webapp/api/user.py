"User profile API endpoints."

import http.client

import flask

import webapp.user
from .. import utils


blueprint = flask.Blueprint('api_user', __name__)

@blueprint.route('/')
def all():
    users = [get_user_basic(u) for u in webapp.user.get_users(role=None)]
    return utils.jsonify(utils.get_json(users=users), schema='/users')

@blueprint.route('/<name:username>')
def profile(username):
    user = webapp.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not webapp.user.is_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    user.pop('password', None)
    user.pop('apikey', None)
    user['logs'] = {'href': utils.url_for('.logs', username=user['username'])}
    return utils.jsonify(utils.get_json(**user), schema='/user')

@blueprint.route('/<name:username>/logs')
def logs(username):
    user = webapp.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not webapp.user.is_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    return utils.jsonify(
        utils.get_json(user=get_user_basic(user),
                       logs=utils.get_logs(user['_id'])),
        schema='/logs')

def get_user_basic(user):
    "Return the basic JSON data for a user."
    return {'username': user['username'],
            'href': utils.url_for('.profile',username=user['username'])}
