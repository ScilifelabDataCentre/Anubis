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
                                 proposals=get_proposals(call=call))

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all proposals for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'proposals/user.html', 
        user=user,
        proposals=get_proposals(username=user['username']))

@blueprint.route('/user/<username>/call/<cid>')
@utils.login_required
def user_call(username, cid):
    "List all proposals for a user in a call."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'proposals/user.html', 
        user=user,
        proposals=get_proposals(username=user['username'], call=call))

def get_proposals(username=None, call=None):
    """Get all proposals, specified by user and/or call.
    Filter by user access.
    """
    if username:
        if call:
            result = flask.g.db.view('proposals', 'user_call',
                                     key=[username, call['identifier']],
                                     reduce=False,
                                     include_docs=True)
        else:
            result = flask.g.db.view('proposals', 'user',
                                     key=username,
                                     reduce=False,
                                     include_docs=True)
        proposals = [anubis.proposal.set_proposal_cache(r.doc, call=call)
                       for r in result]        
    elif call:
        proposals = [anubis.proposal.set_proposal_cache(r.doc, call=call)
                       for r in flask.g.db.view('proposals', 'call',
                                                key=call['identifier'],
                                                reduce=False,
                                                include_docs=True)]
    else:
        raise ValueError('neither username nor call specified')
    # XXX access has not been implemented yet; currently too permissive!
    return [s for s in proposals if s['cache']['is_readable']]

def get_proposals_count(username=None, call=None):
    "Get the number of proposals, specified by user and/or call."
    if username:
        if call:
            result = flask.g.db.view('proposals', 'user_call',
                                     key=[username, call['identifier']],
                                     reduce=True)
        else:
            result = flask.g.db.view('proposals', 'user',
                                     key=username,
                                     reduce=True)
    elif call:
        result = flask.g.db.view('proposals', 'call',
                                 key=call['identifier'],
                                 reduce=True)
    else:
        raise ValueError('neither username nor call specified')
    if result:
        return result[0].value
    else:
        return 0
