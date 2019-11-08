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
    call = anubis.call.get_call(submission['call'])
    # XXX Check access
    return flask.render_template('submission/display.html',
                                 submission=submission,
                                 call=call)

@blueprint.route('/<sid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(sid):
    "Edit the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('no such submission')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        # XXX Check access
        is_deletable = True         # XXX
        return flask.render_template('submission/edit.html',
                                     submission=submission,
                                     is_deletable=is_deletable)

    elif utils.http_POST():
        # XXX Check access
        with SubmissionSaver(submission) as saver:
            saver['title'] = flask.request.form.get('title') or None
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    elif utils.http_DELETE():
        # XXX Check access
        is_deletable = True         # XXX
        if not is_deletable:
            utils.flash_error('submission cannot be deleted')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        utils.delete(submission)
        utils.flash_message(f"deleted submission {submission['sid']}")
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


def get_submission(sid):
    "Return the submission with the given identifier."
    result = [r.doc for r in flask.g.db.view('submissions', 'identifier',
                                             key=sid,
                                             include_docs=True)]
    if len(result) == 1:
        return result[0]
    else:
        return None
