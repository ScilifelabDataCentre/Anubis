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
    "List submissions in a call according to user access privileges."
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    submissions = [s for s in get_submissions(call) if s['tmp']['is_readable']]
    return flask.render_template('submissions/call.html', 
                                 call=call,
                                 submissions=submissions)

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List submissions for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('no such user')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("you may not view the user's submissions")
        return flask.redirect(flask.url_for('home'))

    submissions = [s for s in get_user_submissions(user['username'])
                   if s['tmp']['is_readable']]
    return flask.render_template('submissions/user.html', 
                                 user=user,
                                 submissions=submissions)

def get_submissions(call):
    "Get all submissions for the call."
    return [anubis.submission.add_submission_tmp(r.doc, call=call)
            for r in flask.g.db.view('submissions', 'call',
                                     key=call['identifier'],
                                     reduce=False,
                                     include_docs=True)]

def get_user_submissions(username):
    "Get all submissions from the user."
    return [anubis.submission.add_submission_tmp(r.doc, call=call)
            for r in flask.g.db.view('submissions', 'user',
                                     key=username,
                                     reduce=False,
                                     include_docs=True)]

def get_user_submissions_count(username):
    "Get the number of submissions from the user."
    result = list(flask.g.db.view('submissions', 'user',
                                  key=username,
                                  reduce=True))
    if result:
        return result[0].value
    else:
        return 0
