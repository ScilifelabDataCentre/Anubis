"Lists of submissions."

import flask

import anubis.call
import anubis.submission
import anubis.user

from . import constants
from . import utils


blueprint = flask.Blueprint('submissions', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List submissions in a call. XXX check user access!"
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('submissions/call.html', 
                                 call=call,
                                 submissions=get_submissions(call=call))

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all submissions for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's submissions.")
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'submissions/user.html', 
        user=user,
        submissions=get_submissions(username=user['username']))

@blueprint.route('/user/<username>/call/<cid>')
@utils.login_required
def user_call(username, cid):
    "List all submissions for a user in a call."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's submissions.")
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'submissions/user.html', 
        user=user,
        submissions=get_submissions(username=user['username'], call=call))

def get_submissions(username=None, call=None):
    """Get all submissions, specified by user and/or call.
    Filter by user access.
    """
    if username:
        if call:
            result = flask.g.db.view('submissions', 'user_call',
                                     key=[username, call['identifier']],
                                     reduce=False,
                                     include_docs=True)
        else:
            result = flask.g.db.view('submissions', 'user',
                                     key=username,
                                     reduce=False,
                                     include_docs=True)
        submissions = [anubis.submission.set_submission_cache(r.doc, call=call)
                       for r in result]        
    elif call:
        submissions = [anubis.submission.set_submission_cache(r.doc, call=call)
                       for r in flask.g.db.view('submissions', 'call',
                                                key=call['identifier'],
                                                reduce=False,
                                                include_docs=True)]
    else:
        raise ValueError('neither username nor call specified')
    # XXX access has not been implemented yet; currently too permissive!
    return [s for s in submissions if s['cache'].is_readable]

def get_submissions_count(username=None, call=None):
    "Get the number of submissions, specified by user and/or call."
    if username:
        if call:
            result = flask.g.db.view('submissions', 'user_call',
                                     key=[username, call['identifier']],
                                     reduce=True)
        else:
            result = flask.g.db.view('submissions', 'user',
                                     key=username,
                                     reduce=True)
    elif call:
        result = flask.g.db.view('submissions', 'call',
                                 key=call['identifier'],
                                 reduce=True)
    else:
        raise ValueError('neither username nor call specified')
    if result:
        print(result[0].value)
        return result[0].value
    else:
        print(0)
        return 0
