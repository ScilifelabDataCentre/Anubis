"Lists of calls for submissions."

import flask

import anubis.call

from . import constants
from . import utils


blueprint = flask.Blueprint('calls', __name__)

@blueprint.route('')
@utils.admin_required
def all():
    "All calls."
    return flask.render_template('calls/all.html', calls=get_all_calls())

@blueprint.route('/user')
@blueprint.route('/user/<username>')
@utils.login_required
def user(username=''):
    "Calls in which the user is involved (submitter or reviewer)."
    raise NotImplementedError

def get_all_calls():
    calls = [r.doc for r in 
             flask.g.db.view('calls', 'identifier', include_docs=True)]
    for call in calls:
        anubis.call.set_call_tmp(call)
    return calls

def get_open_calls():
    "Get all currently open calls."
    result = flask.g.db.view('calls', 'closes', 
                             startkey=utils.normalized_local_now(),
                             endkey='ZZZZZZ',
                             include_docs=True)
    calls = [r.doc for r in result]
    result = flask.g.db.view('calls', 'open_ended', 
                             startkey='',
                             endkey=utils.normalized_local_now(),
                             include_docs=True)
    calls.extend([r.doc for r in result])
    for call in calls:
        anubis.call.set_call_tmp(call)
    return calls
