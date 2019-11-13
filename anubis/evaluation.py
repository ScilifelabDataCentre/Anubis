"Evaluation of a submission. Created from the outline in the call."

import types

import flask

from . import constants
from . import utils
from .saver import BaseSaver, FieldMixin


blueprint = flask.Blueprint('evaluation', __name__)

@blueprint.route('/<sid>', methods=['POST'])
@utils.login_required
def create(sid):
    """Create a new evaluation for the submission.
    Redirect to existing if the user (reviewer) already has one.
    """
    from anubis.submission import get_submission
    from anubis.call import get_call
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    evaluation = get_evaluation(submission, flask.g.current_user)
    if evaluation is None:
        call = submission['tmp'].call
        if not (flask.g.is_admin or
                flask.g.current_user['username'] in call['reviewers']):
            utils.flash_error('You are not a reviewer for the call.')
            return flask.redirect(flask.url_for('home'))
        with EvaluationSaver(submission=submission) as saver:
            pass
        evaluation = saver.doc
    flask.redirect(flask.url_for('.display', iuid=evaluation['_id']))

@blueprint.route('/<iuid:iuid>')
@utils.login_required
def display(iuid):
    "Display the evaluation for the submission."
    try:
        evaluation = get_evaluation_tmp(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('evaluation/display.html',
                                 evaluation=evaluation)

@blueprint.route('/<iuid:iuid>/edit')
@utils.login_required
def edit(iuid):
    "Edit the evaluation for the submission."
    raise NotImplementedError

@blueprint.route('/<iuid>/logs')
@utils.login_required
def logs(cid):
    "Display the log records of the call."
    evaluation = flask.g.db.get(iuid)
    if evaluation is None:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Evaluation {evaluation['identifier']}",
        cancel_url=flask.url_for('.display', iuid=evaluation['_id']),
        logs=utils.get_logs(evaluation['_id']))


class EvaluationSaver(FieldMixin, BaseSaver):
    "Evaluation document saver context."

    DOCTYPE = constants.EVALUATION

    def __init__(self, doc=None, submission=None):
        if doc:
            super().__init__(doc=doc)
        elif submission:
            super().__init__(doc=None)
            self.doc['call'] = submission['tmp'].call['identifier']
            self.doc['submission'] = submission['identifier']
        else:
            raise ValueError('doc or submission must be specified')
        self.set_reviewer(flask.g.current_user)

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_reviewer(self, user):
        "Set the reviewer for the evaluation; must be called at creation."
        self.doc['reviewer'] = user['username']


def get_evaluation(submission, reviewer):
    "Get the evaluation of the submission by the reviewer."
    result = flask.g.db.view('evaluations', 'submission_reviewer',
                             key=[submission['identifier'], 
                                  reviewer['username']],
                             include_docs=True)
    try:
        return result[0].doc
    except IndexError:
        return None

def get_evaluations(call=None):
    "Get all evaluations for submissions in a call."
    result = [r.doc for r in flask.g.db.view('evaluations', 'call',
                                             key=call['identifier'],
                                             include_docs=True)]
    
def get_evaluation_tmp(evaluation, call=None):
    """Set the'tmp' field of the evaluation.
    This is computed data that will not be stored with the document.
    Depends on login, access, status, etc.
    """
    from anubis.call import get_call
    from anubis.submission import get_submission
    evaluation['tmp'] = tmp = types.SimpleNamespace()
    if call is None:
        tmp.call = get_call(evaluation['call'])
    else:
        tmp.call = call
    tmp.submission = get_submission(evaluation['submission'])
    return evaluation
