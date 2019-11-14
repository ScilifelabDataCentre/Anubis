"Evaluation of a submission. Created from the outline in the call."

import flask

from . import constants
from . import utils
from .saver import BaseSaver, FieldMixin


EVALUATIONS_DESIGN_DOC = {
    'views': {
        'call': {'reduce': '_count',
                 'map': "function(doc) {if (doc.doctype !== 'evaluation') return; emit(doc.call, null);}"},
        'submission_reviewer': {'reduce': '_count',
                                'map': "function(doc) {if (doc.doctype !== 'evaluation') return; emit([doc.submission, doc.reviewer], null);}"},
    }
}

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
        call = submission['cache']['call']
        if not (flask.g.is_admin or
                flask.g.current_user['username'] in call['reviewers']):
            utils.flash_error('You are not a reviewer for the call.')
            return flask.redirect(flask.url_for('home'))
        with EvaluationSaver(submission=submission) as saver:
            pass
        evaluation = saver.doc
    elif not evaluation['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this evaluation.')
        return flask.redirect(flask.url_for('home'))
    return flask.redirect(flask.url_for('.display', iuid=evaluation['_id']))

@blueprint.route('/<iuid:iuid>')
@utils.login_required
def display(iuid):
    "Display the evaluation for the submission."
    try:
        evaluation = get_evaluation_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))
    if not evaluation['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this evaluation.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template('evaluation/display.html',
                                 evaluation=evaluation)

@blueprint.route('/<iuid:iuid>/edit', methods=['GET', 'POST'])
@utils.login_required
def edit(iuid):
    "Edit the evaluation for the submission."
    try:
        evaluation = get_evaluation_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))
    if not evaluation['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this evaluation.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('evaluation/edit.html',
                                     evaluation=evaluation)

    elif utils.http_POST():
        try:
            with EvaluationSaver(doc=evaluation) as saver:
                for field in evaluation['cache']['call']['evaluation']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.edit', iuid=evaluation['_id']))
        return flask.redirect(
            flask.url_for('.display', iuid=evaluation['_id']))

@blueprint.route('/<iuid:iuid>/finalize', methods=['POST'])
@utils.login_required
def finalize(iuid):
    "Finalize the evaluation for the submission."
    try:
        evaluation = get_evaluation_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))
    if not evaluation['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this evaluation.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with EvaluationSaver(doc=evaluation) as saver:
                saver['finalized'] = utils.get_time()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.display', iuid=evaluation['_id']))

@blueprint.route('/<iuid:iuid>/unfinalize', methods=['POST'])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the evaluation for the submission."
    try:
        evaluation = get_evaluation_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))
    if not evaluation['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this evaluation.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with EvaluationSaver(doc=evaluation) as saver:
                saver['finalized'] = None
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.display', iuid=evaluation['_id']))

@blueprint.route('/<iuid>/logs')
@utils.login_required
def logs(iuid):
    "Display the log records of the call."
    evaluation = flask.g.db.get(iuid)
    if evaluation is None:
        utils.flash_error('No such evaluation.')
        return flask.redirect(flask.url_for('home'))

    evaluation = get_evaluation_cache(evaluation)
    return flask.render_template(
        'logs.html',
        title=f"Evaluation of {evaluation['cache']['submission']['identifier']}" \
              f" by {evaluation['reviewer']}",
        back_url=flask.url_for('.display', iuid=evaluation['_id']),
        logs=utils.get_logs(evaluation['_id']))


class EvaluationSaver(FieldMixin, BaseSaver):
    "Evaluation document saver context."

    DOCTYPE = constants.EVALUATION

    def __init__(self, doc=None, submission=None):
        if doc:
            super().__init__(doc=doc)
        elif submission:
            super().__init__(doc=None)
            self.doc['call'] = submission['cache']['call']['identifier']
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
        return get_evaluation_cache(result[0].doc)
    except IndexError:
        return None

def get_evaluations(call=None):
    "Get all evaluations for submissions in a call."
    result = [get_evaluation_cache(r.doc)
              for r in flask.g.db.view('evaluations', 'call',
                                       key=call['identifier'],
                                       include_docs=True)]

def get_evaluation_cache(evaluation, call=None):
    """Set the'cache' field of the evaluation.
    This is computed data that will not be stored with the document.
    Depends on login, access, status, etc.
    """
    from anubis.call import get_call
    from anubis.submission import get_submission
    evaluation['cache'] = cache = dict(is_readable=False,
                                       is_editable=False)
    if call is None:
        cache['call'] = call = get_call(evaluation['call'])
    else:
        cache['call'] = call
    cache['submission'] = get_submission(evaluation['submission'])
    if flask.g.is_admin:
        cache['is_readable'] = True
        cache['is_editable'] = True
    elif flask.g.current_user:
        cache['is_readable'] = flask.g.current_user['username'] in call['reviewers']
        cache['is_editable'] = flask.g.current_user['username'] == evaluation['reviewer']
    return evaluation
