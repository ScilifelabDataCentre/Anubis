"Lists of proposals."

import flask

import anubis.call
import anubis.proposal
import anubis.user

from . import constants
from . import utils


blueprint = flask.Blueprint('proposals', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List proposals in a call. XXX check user access!"
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('proposals/call.html', 
                                 call=call,
                                 proposals=get_call_proposals(call))

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all proposals for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.am_admin_or_self(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'proposals/user.html', 
        user=user,
        proposals=get_user_proposals(user['username']))

@blueprint.route('/user/<username>/call/<cid>')
@utils.login_required
def user_call(username, cid):
    "List all proposals for a user in a call."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.am_admin_or_self(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    proposals = [p for p in get_user_proposals(username)
                 if p['cache']['call']['identifier'] == call['identifier']]
    return flask.render_template('proposals/user.html', 
                                 user=user,
                                 proposals=proposals)

def get_user_proposals(username, call=None):
    "Get all proposals created by the user. Cache not set."
    return [anubis.proposal.set_cache(r.doc, call=call)
            for r in flask.g.db.view('proposals', 'user',
                                     key=username,
                                     reduce=False,
                                     include_docs=True)]

def get_call_user_proposal(call, username):
    """Get the proposal created by the user in the call. Cache not set.
    Excludes no proposals.
    """
    proposals = [p for p in get_user_proposals(username, call=call)
                 if p['call'] == call['identifier']]
    if proposals:
        return proposals[0]
    else:
        return None

def get_call_proposals(call):
    """Get all submitted proposals in the call. Cache not set.
    NOTE: No check for user access!
    """
    return [anubis.proposal.set_cache(r.doc)
            for r in flask.g.db.view('proposals', 'call',
                                     key=call['identifier'],
                                     reduce=False,
                                     include_docs=True)]

def get_call_submitters(call):
    "Get the set of users who have submitted a proposal in the call."
    result = flask.g.db.view('proposals', 'call',
                             key=call['identifier'],
                             reduce=False)
    return set([r.value for r in result])
