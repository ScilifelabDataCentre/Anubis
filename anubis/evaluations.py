"Evaluations lists."

import flask

import anubis.user

from . import constants
from . import utils
from .evaluation import get_evaluation_cache


blueprint = flask.Blueprint('evaluations', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all evaluations for a call."
    from anubis.call import get_call
    call = get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not call['cache']['is_reviewer']:
        utils.flash_error('You are not a reviewer in the call.')
        return flask.redirect(flask.url_for('home'))

    scorefields = [f for f in call['evaluation']
                   if f['type'] == constants.SCORE]
    evaluations = [get_evaluation_cache(r.doc)
                   for r in flask.g.db.view('evaluations', 'call',
                                            key=cid,
                                            reduce=False,
                                            include_docs=True)]
    # XXX filter for evaluations access
    return flask.render_template('evaluations/call.html',
                                 call=call,
                                 scorefields=scorefields,
                                 evaluations=evaluations)

@blueprint.route('/submission/<sid>')
@utils.login_required
def submission(sid):
    "List all evaluations for a submission."
    from anubis.submission import get_submission
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    call = submission['cache']['call']
    if not call['cache']['is_reviewer']:
        utils.flash_error("You are not a reviewer of the submission's call.")
        return flask.redirect(flask.url_for('home'))

    evaluations = [get_evaluation_cache(r.doc)
                   for r in flask.g.db.view('evaluations', 'call',
                                            key=call['identifier'],
                                            reduce=False,
                                            include_docs=True)]
    # XXX filter for evaluations access
    return flask.render_template('evaluations/submission.html',
                                 submission=submission,
                                 evaluations=evaluations)

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all evaluations for a user (reviewer)."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's evaluations.")
        return flask.redirect(flask.url_for('home'))
    evaluations = [get_evaluation_cache(r.doc)
                   for r in flask.g.db.view('evaluations', 'reviewer',
                                            key=user['username'],
                                            reduce=False,
                                            include_docs=True)]
    return flask.render_template('evaluations/user.html', 
                                 user=user,
                                 submissions=evaluations)

def get_call_evaluations_count(call):
    "Get the number of evaluations for the call."
    result = flask.g.db.view('evaluations', 'call',
                             key=call['identifier'],
                             reduce=True)
    if result:
        return result[0].value
    else:
        return 0

def get_submission_evaluations_count(submission):
    "Get the number of evaluations for the submission."
    result = flask.g.db.view('evaluations', 'submission_reviewer',
                             startkey=[submission['identifier'], ''],
                             endkey=[submission['identifier'], 'ZZZZZZ'],
                             reduce=True)
    if result:
        return result[0].value
    else:
        return 0
