"Lists of calls for proposals."

import flask

import anubis.call
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint('calls', __name__)

@blueprint.route('')
@utils.admin_or_staff_required
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
    """Calls owned by the given user.
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
    return flask.render_template(
        'calls/closed.html',
        calls=calls,
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants)

@blueprint.route('/open')
def open():
    "Open calls."
    return flask.render_template('calls/open.html',
                                 calls=get_open_calls(),
                                 am_owner=anubis.call.am_owner,
                                 allow_create=anubis.call.allow_create())

def get_open_calls():
    "Return a list of open calls, sorted according to configuration."
    limited = [anubis.call.set_tmp(r.doc)
               for r in flask.g.db.view('calls', 'closes', 
                                        startkey=utils.normalized_local_now(),
                                        endkey='ZZZZZZ',
                                        include_docs=True)]
    open_ended = [anubis.call.set_tmp(r.doc)
                  for r in flask.g.db.view('calls', 'open_ended', 
                                           startkey='',
                                           endkey=utils.normalized_local_now(),
                                           include_docs=True)]
    order_key = flask.current_app.config['CALLS_OPEN_ORDER_KEY']
    if order_key == 'closes':
        limited.sort(key=lambda k: (k['closes'], k['title']))
        open_ended.sort(key=lambda k: k['title'])
        result = limited + open_ended
    elif order_key == 'title':
        result = limited + open_ended
        result.sort(key=lambda k: k['title'])
    elif order_key == 'identifier':
        result = limited + open_ended
        result.sort(key=lambda k: k['identifier'])
    else:
        result = limited + open_ended
        result.sort(key=lambda k: k['identifier'])
    return result

@blueprint.route('/grants')
@utils.admin_or_staff_required
def grants():
    "All calls with grants."
    calls = set([r.key for r in flask.g.db.view('grants', 'call', reduce=False)])
    calls = [anubis.call.set_tmp(anubis.call.get_call(c)) for c in calls]
    return flask.render_template(
        'calls/grants.html',
        calls=calls,
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants)
