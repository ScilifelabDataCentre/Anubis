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
    calls = [anubis.call.set_tmp(r.doc) for r in 
             flask.g.db.view('calls', 'identifier', include_docs=True)]
    return flask.render_template('calls/all.html', calls=calls)

@blueprint.route('/owner/<username>')
@utils.login_required
def owner(username):
    """Calls owner by the given user.
    Includes calls that have not been opened,
    and those with neither opens nor closes dates set.
    """
    calls = [anubis.call.set_tmp(r.doc) for r in 
             flask.g.db.view('calls', 'owner',
                             key=username,
                             reduce=False,
                             include_docs=True)]
    return flask.render_template('calls/owner.html',
                                 calls=calls,
                                 username=username,
                                 allow_create=anubis.call.allow_create())

@blueprint.route('/closed')
def closed():
    "Closed calls."
    calls = [anubis.call.set_tmp(r.doc) 
             for r in flask.g.db.view('calls', 'closes', 
                                      startkey='',
                                      endkey=utils.normalized_local_now(),
                                      include_docs=True)]
    return flask.render_template('calls/closed.html',
                                 calls=calls,
                                 am_call_admin=anubis.call.am_call_admin,
                                 allow_create=anubis.call.allow_create())

@blueprint.route('/open')
def open():
    "Open calls."
    return flask.render_template('calls/open.html',
                                 calls=get_open_calls(),
                                 am_call_admin=anubis.call.am_call_admin,
                                 allow_create=anubis.call.allow_create())

def get_open_calls():
    result = [anubis.call.set_tmp(r.doc)
              for r in flask.g.db.view('calls', 'closes', 
                                       startkey=utils.normalized_local_now(),
                                       endkey='ZZZZZZ',
                                       include_docs=True)]
    result.extend([anubis.call.set_tmp(r.doc)
                  for r in flask.g.db.view('calls', 'open_ended', 
                                           startkey='',
                                           endkey=utils.normalized_local_now(),
                                           include_docs=True)])
    return result
