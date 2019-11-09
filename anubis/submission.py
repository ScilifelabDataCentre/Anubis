"Submissions."

import copy

import flask

import anubis.call

from . import constants
from . import utils


blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/<sid>')
@utils.login_required
def display(sid):
    "Display the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('no such submission')
        return flask.redirect(flask.url_for('home'))
    if not submission['tmp']['is_readable']:
        utils.flash_error('you are not allowed to read the submission')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('submission/display.html',
                                 submission=submission)

@blueprint.route('/<sid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(sid):
    "Edit the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('no such submission')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        if not submission['tmp']['is_editable']:
            utils.flash_error('you are not allowed to edit the submission')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        return flask.render_template('submission/edit.html',
                                     submission=submission)

    elif utils.http_POST():
        if not submission['tmp']['is_editable']:
            utils.flash_error('you are not allowed to edit the submission')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        with SubmissionSaver(submission) as saver:
            saver['title'] = flask.request.form.get('_title') or None
            for field in submission['fields']:
                saver.set_field_value(field, form=flask.request.form)
        for field in submission['fields']:
            if field.get('error'):
                utils.flash_error('some error in input fields...')
                break
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    elif utils.http_DELETE():
        if not submission['tmp']['is_editable']:
            utils.flash_error('you are not allowed to delete the submission')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        utils.delete(submission)
        utils.flash_message(f"deleted submission {sid}")
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/<sid>/logs')
@utils.login_required
def logs(sid):
    "Display the log records of the given submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('no such submission')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Submission {submission['identifier']}",
        cancel_url=flask.url_for('.display', sid=submission['identifier']),
        logs=utils.get_logs(submission['_id']))


class SubmissionSaver(utils.BaseSaver):
    "Submission document saver context."

    DOCTYPE = constants.DOCTYPE_SUBMISSION

    def initialize(self):
        "Set the owner of the submission."
        self.doc['user'] = flask.g.current_user['username']

    def set_call(self, call):
        "Set the call for the submission; must be called first."
        if self.doc.get('call'):
            raise ValueError('call has already been set')
        self.doc['call'] = call['identifier']
        counter = call.get('counter')
        if counter is None:
            counter = 1
        else:
            counter += 1
        with anubis.call.CallSaver(call):
            call['counter'] = counter
        self.doc['identifier'] = f"{call['identifier']}:{counter:03d}"
        self.doc['fields'] = copy.deepcopy(call['fields'])

    def set_field_value(self, field, form=dict()):
        "Set the value according to field type."
        field['error'] = None
        value = form.get(field['identifier'])
        if field['required'] and not value:
            field['error'] = 'missing value'
        else:
            field['value'] = value

def get_submission(sid):
    "Return the submission with the given identifier."
    result = [r.doc for r in flask.g.db.view('submissions', 'identifier',
                                             key=sid,
                                             include_docs=True)]
    if len(result) == 1:
        return add_submission_tmp(result[0])
    else:
        return None

def add_submission_tmp(submission, call=None):
    """Set the 'tmp' property of the submission.
    This is computed data that will not be stored with the document.
    Depends on login, privileges, etc.
    """
    submission['tmp'] = tmp = {}
    if call is None:
        tmp['call'] = anubis.call.get_call(submission['call'])
    else:
        tmp['call'] = call
    if flask.g.is_admin:
        tmp['is_readable'] = True
        tmp['is_editable'] = True
    elif flask.g.current_user:
        if flask.c.current_user['username'] == submission['user']:
            tmp['is_readable'] = True
            tmp['is_editable'] = tmp['call']['is_open']
        else:
            # XXX Check reviewers privileges within call
            tmp['is_readable'] = True
            tmp['is_editable'] = False
    else:
        tmp['is_readable'] = False
        tmp['is_editable'] = False
    return submission
