"Submissions."

import flask

import anubis.call

from . import constants
from . import utils
from .saver import AttachmentsSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    logger = utils.get_logger(app)
    if db.put_design('submissions', DESIGN_DOC):
        logger.info('Updated submissions design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'submission') return; emit(doc.identifier, null);}"},
        # NOTE: excludes submissions not marked 'submitted'
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'submission' || !doc.submitted) return; emit(doc.call, null);}"},
        # NOTE: includes submissions not marked 'submitted'
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'submission') return; emit(doc.user, null);}"},
        'user_call': {'reduce': '_count',
                      'map': "function (doc) {if (doc.doctype !== 'submission') return; emit([doc.user, doc.call], null);}"},
    }
}

blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/<sid>')
@utils.login_required
def display(sid):
    "Display the submission."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if not submission['cache']['is_readable']:
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
        if not submission['cache']['is_editable']:
            utils.flash_error('You are not allowed to edit the submission.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        return flask.render_template('submission/edit.html',
                                     submission=submission)

    elif utils.http_POST():
        if not submission['cache']['is_editable']:
            utils.flash_error('You are not allowed to edit the submission.')
            return flask.redirect(
                flask.url_for('.display', sid=submission['identifier']))
        try:
            with SubmissionSaver(submission) as saver:
                saver['title'] = flask.request.form.get('_title') or None
                for field in submission['cache']['call']['fields']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.edit', sid=submission['identifier']))
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    elif utils.http_DELETE():
        if not submission['cache']['is_editable']:
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
    if not submission['cache']['is_submittable']:
        utils.flash_error('Submit disallowed; call closed.')
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    if utils.http_POST():
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
    if not submission['cache']['is_submittable']:
        utils.flash_error('Unsubmit disallowed; call closed.')
        return flask.redirect(
            flask.url_for('.display', sid=submission['identifier']))

    if utils.http_POST():
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
    if not submission['cache']['is_readable']:
        utils.flash_error('You are not allowed to read the submission.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Submission {submission['identifier']}",
        back_url=flask.url_for('.display', sid=submission['identifier']),
        logs=utils.get_logs(submission['_id']))

@blueprint.route('/<sid>/document/<documentname>')
@utils.login_required
def document(sid, documentname):
    "Download the given submission document (attachment file)."
    submission = get_submission(sid)
    if submission is None:
        utils.flash_error('No such submission.')
        return flask.redirect(flask.url_for('home'))
    if not submission['cache']['is_readable']:
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

    def __init__(self, doc=None, call=None):
        if doc:
            super().__init__(doc=doc)
        elif call:
            super().__init__(doc=None)
            self.set_call(call)
        else:
            raise ValueError('doc or call must be specified')
        self.set_user(flask.g.current_user)

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_user(self, user):
        "Set the user for the submission; must be called at creation."
        self.doc['user'] = user['username']

    def set_call(self, call):
        "Set the call for the submission; must be called at creation."
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
        if not self.doc['cache']['is_submittable']:
            raise ValueError('Submit is disallowed.')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not self.doc['cache']['is_submittable']:
            raise ValueError('Unsubmit is disallowed.')
        self.doc.pop('submitted', None)


def get_submission(sid):
    "Return the submission with the given identifier."
    result = [r.doc for r in flask.g.db.view('submissions', 'identifier',
                                             key=sid,
                                             include_docs=True)]
    if len(result) == 1:
        return set_submission_cache(result[0])
    else:
        return None

def set_submission_cache(submission, call=None):
    """Set the 'cache' field of the submission.
    This is computed data that will not be stored with the document.
    Depends on login, access, status, etc.
    """
    from anubis.evaluations import get_submission_evaluations_count
    submission['cache'] = cache = dict(is_readable=False,
                                       is_editable=False,
                                       is_submittable=False,
                                       is_reviewer=False)
    # Get the call for the submission.
    if call is None:
        cache['call'] = anubis.call.get_call(submission['call'])
    else:
        cache['call'] = call
    if flask.g.is_admin:
        cache['is_readable'] = True
        cache['is_editable'] = True
        cache['is_submittable'] = True
        cache['is_reviewer'] = True
    elif flask.g.current_user:
        if flask.g.current_user['username'] == submission['user']:
            cache['is_readable'] = True
            cache['is_editable'] = cache['call']['cache']['is_open'] and \
                                   not submission.get('submitted')
            cache['is_submittable'] = cache['call']['cache']['is_open'] and \
                                      not submission['errors']
        elif cache['call']['cache']['is_reviewer']:
            cache['is_readable'] = True
            cache['is_reviewer'] = True
    if cache['is_reviewer']:
        cache['evaluations_count'] = get_submission_evaluations_count(submission)
    return submission
