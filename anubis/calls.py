"Lists of calls for proposals."

import flask

import anubis.call

from . import constants
from . import utils


blueprint = flask.Blueprint('calls', __name__)

@blueprint.route('')
@utils.admin_required
def all():
    """All calls.
    Includes calls that have not been opened,
    and those with neither opens nor closes dates set.
    """
    return flask.render_template('calls/all.html', calls=get_all_calls())

@blueprint.route('/closed')
def closed():
    "Closed calls."
    return flask.render_template('calls/closed.html', calls=get_closed_calls())

@blueprint.route('/open')
def open():
    "Open calls."
    return flask.render_template('calls/open.html', calls=get_open_calls())

@blueprint.route('/user')
@blueprint.route('/user/<username>')
@utils.login_required
def user(username=''):
    "Calls in which the user is involved (submitter or reviewer)."
    raise NotImplementedError

def get_all_calls():
    return [anubis.call.set_cache(r.doc) for r in 
            flask.g.db.view('calls', 'identifier', include_docs=True)]

def get_closed_calls():
    "Get all currently closed calls."
    result = [anubis.call.set_cache(r.doc) 
             for r in flask.g.db.view('calls', 'closes', 
                                      startkey='',
                                      endkey=utils.normalized_local_now(),
                                      include_docs=True)]
    result = [c for c in result if c['cache']['is_closed']]
    return result

def get_open_calls():
    "Get all currently open calls."
    result = [anubis.call.set_cache(r.doc)
              for r in flask.g.db.view('calls', 'closes', 
                                       startkey=utils.normalized_local_now(),
                                       endkey='ZZZZZZ',
                                       include_docs=True)]
    result.extend([anubis.call.set_cache(r.doc)
                   for r in flask.g.db.view('calls', 'open_ended', 
                                            startkey='',
                                            endkey=utils.normalized_local_now(),
                                            include_docs=True)])
    return result
