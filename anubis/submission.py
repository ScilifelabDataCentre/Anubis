"Submissions."

import types

import flask

import anubis.call

from . import constants
from . import utils
from .saver import AttachmentsSaver, FieldMixin


blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/<sid>')
@utils.login_required
def display(sid):
    "Display the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if not submission['tmp'].is_readable:
        utils.flash_error('You are not allowed to read the submission.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('submission/display.html',
                                 submission=submission)

@blueprint.route('/<sid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(sid):
    "Edit the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        if not submission['tmp'].is_editable:
            utils.flash_error('You are not allowed to edit the submission.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        return flask.render_template('submission/edit.html',
                                     submission=submission)

    elif utils.http_POST():
        if not submission['tmp'].is_editable:
            utils.flash_error('You are not allowed to edit the submission.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        try:
            with SubmissionSaver(submission) as saver:
                saver['title'] = flask.request.form.get('_title') or None
                for field in submission['tmp'].call['fields']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.edit', sid=submission['identifier']))
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    elif utils.http_DELETE():
        if not submission['tmp'].is_editable:
            utils.flash_error('You are not allowed to delete the submission.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        utils.delete(submission)
        utils.flash_message(f"Deleted submission {sid}.")
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/<sid>/submit', methods=['POST'])
@utils.login_required
def submit(sid):
    "Submit the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if utils.http_POST():
        if not submission['tmp'].is_submittable:
            utils.flash_error('You cannot submit; edit not allowed, or call closed.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        try:
            with SubmissionSaver(submission) as saver:
                saver.set_submitted()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', sid=sid))

@blueprint.route('/<sid>/unsubmit', methods=['POST'])
@utils.login_required
def unsubmit(sid):
    "Unsubmit the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if utils.http_POST():
        if not submission['tmp'].is_editable:
            utils.flash_error('You cannot unsubmit; edit not allowed, or call closed.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        try:
            with SubmissionSaver(submission) as saver:
                saver.set_unsubmitted()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', sid=sid))

@blueprint.route('/<sid>/logs')
@utils.login_required
def logs(sid):
    "Display the log records of the given submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if not submission['tmp'].is_readable:
        utils.flash_error('You are not allowed to read the submission.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Submission {submission['identifier']}",
        cancel_url=flask.url_for('.display', sid=submission['identifier']),
        logs=utils.get_logs(submission['_id']))

@blueprint.route('/<sid>/document/<documentname>')
@utils.login_required
def document(sid, documentname):
    "Download the given submission document (attachment file)."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if not submission['tmp'].is_readable:
        utils.flash_error('You are not allowed to read the submission.')
        return flask.redirect(flask.url_for('home'))

    try:
        stub = submission['_attachments'][documentname]
    except KeyError:
        utils.flash_error('No such document in submission.')
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))
    outfile = flask.g.db.get_attachment(submission, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=documentname)
    return response


class SubmissionSaver(FieldMixin, AttachmentsSaver):
    "Submission document saver context."

    DOCTYPE = constants.SUBMISSION

    def initialize(self):
        "Set the owner of the submission."
        self.doc['user'] = flask.g.current_user['username']
        self.doc['values'] = {}
        self.doc['errors'] = {}

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
        self.doc['values'] = dict([(f['identifier'], None) 
                                   for f in call['fields']])

    def set_submitted(self):
        if not self.doc['tmp'].call['tmp'].is_open:
            raise ValueError('the call for the submission is not open')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not self.doc['tmp'].call['tmp'].is_open:
            raise ValueError('the call for the submission is not open')
        self.doc.pop('submitted', None)


def get_submission(sid):
    "Return the submission with the given identifier."
    result = [r.doc for r in flask.g.db.view('submissions', 'identifier',
                                             key=sid,
                                             include_docs=True)]
    if len(result) == 1:
        return set_submission_tmp(result[0])
    else:
        return None

def set_submission_tmp(submission, call=None):
    """Set the 'tmp' property of the submission.
    This is computed data that will not be stored with the document.
    Depends on login, privileges, etc.
    """
    submission['tmp'] = tmp = types.SimpleNamespace(is_readable=False,
                                                    is_editable=False,
                                                    is_submittable=False,
                                                    is_reviewer=False)
    # Get the call for the submission.
    if call is None:
        tmp.call = anubis.call.get_call(submission['call'])
    else:
        tmp.call = call
    if flask.g.is_admin:
        tmp.is_readable = True
        tmp.is_editable = True
        tmp.is_submittable = True
    elif flask.g.current_user:
        if flask.g.current_user['username'] == submission['user']:
            tmp.is_readable = True
            tmp.is_editable = True
            tmp.is_submittable = tmp.call['tmp'].is_open
        elif flask.g.current_user['username'] in tmp.call['reviewers']:
            tmp.is_reviewer = True
            tmp.is_readable = True
    return submission
