"User profile API endpoints."

import http.client

import flask

import anubis.user
from .. import utils


blueprint = flask.Blueprint('api_user', __name__)

@blueprint.route('/')
def all():
    users = anubis.user.get_users(role=None, safe=True)
    return utils.jsonify(utils.get_json(users=users),
                         schema_url=utils.url_for('api_schema.users'))

@blueprint.route('/<id:username>')
def profile(username):
    user = anubis.user.get_user(username=username, safe=True)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not anubis.user.is_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    user.pop('password', None)
    user.pop('apikey', None)
    user['logs'] = {'href': utils.url_for('.logs', username=user['username'])}
    return utils.jsonify(utils.get_json(**user),
                         schema_url=utils.url_for('api_schema.user'))

@blueprint.route('/<id:username>/logs')
def logs(username):
    user = anubis.user.get_user(username=username)
    if not user:
        flask.abort(http.client.NOT_FOUND)
    if not anubis.user.is_admin_or_self(user):
        flask.abort(http.client.FORBIDDEN)
    data = {'username': user['username'],
            'href': utils.url_for('.profile', username=user['username'])}
    return utils.jsonify(utils.get_json(user=data,
                                        logs=utils.get_logs(user['_id'])),
                         schema_url=utils.url_for('api_schema.logs'))
