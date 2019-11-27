"Proposals."

import flask

import anubis.call
import anubis.user

from . import constants
from . import utils
from .saver import AttachmentsSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    logger = utils.get_logger(app)
    if db.put_design('proposals', DESIGN_DOC):
        logger.info('Updated proposals design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.identifier, null);}"},
        # NOTE: excludes proposals not marked 'submitted'
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal' || !doc.submitted) return; emit(doc.call, null);}"},
        # NOTE: includes proposals not marked 'submitted'
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.user, null);}"},
    }
}

blueprint = flask.Blueprint('proposal', __name__)

@blueprint.route('/<pid>')
@utils.login_required
def display(pid):
    "Display the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this proposal.')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('proposal/display.html', proposal=proposal)

@blueprint.route('/<pid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(pid):
    "Edit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this proposal.')
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

    if utils.http_GET():
        return flask.render_template('proposal/edit.html', proposal=proposal)

    elif utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                saver['title'] = flask.request.form.get('_title') or None
                for field in proposal['cache']['call']['proposal']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.edit', pid=proposal['identifier']))
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

    elif utils.http_DELETE():
        utils.delete(proposal)
        utils.flash_message(f"Deleted proposal {pid}.")
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/<pid>/submit', methods=['POST'])
@utils.login_required
def submit(pid):
    "Submit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_submittable']:
        utils.flash_error('Submit disallowed; call closed.')
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

    if utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                saver.set_submitted()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', pid=pid))

@blueprint.route('/<pid>/unsubmit', methods=['POST'])
@utils.login_required
def unsubmit(pid):
    "Unsubmit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_submittable']:
        utils.flash_error('Unsubmit disallowed; call closed.')
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

    if utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                saver.set_unsubmitted()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', pid=pid))

@blueprint.route('/<pid>/logs')
@utils.login_required
def logs(pid):
    "Display the log records of the given proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this proposal.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Proposal {proposal['identifier']}",
        back_url=flask.url_for('.display', pid=proposal['identifier']),
        logs=utils.get_logs(proposal['_id']))

@blueprint.route('/<pid>/document/<documentname>')
@utils.login_required
def document(pid, documentname):
    "Download the given proposal document (attachment file)."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not proposal['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this proposal.')
        return flask.redirect(flask.url_for('home'))

    try:
        stub = proposal['_attachments'][documentname]
    except KeyError:
        utils.flash_error('No such document in proposal.')
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))
    outfile = flask.g.db.get_attachment(proposal, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=documentname)
    return response


class ProposalSaver(FieldMixin, AttachmentsSaver):
    "Proposal document saver context."

    DOCTYPE = constants.PROPOSAL

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
        "Set the user for the proposal; must be called at creation."
        self.doc['user'] = user['username']

    def set_call(self, call):
        "Set the call for the proposal; must be called at creation."
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
                                   for f in call['proposal']])

    def set_submitted(self):
        if not self.doc['cache']['is_submittable']:
            raise ValueError('Submit is disallowed.')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not self.doc['cache']['is_submittable']:
            raise ValueError('Unsubmit is disallowed.')
        self.doc.pop('submitted', None)


def get_proposal(pid):
    "Return the proposal with the given identifier."
    result = [r.doc for r in flask.g.db.view('proposals', 'identifier',
                                             key=pid,
                                             include_docs=True)]
    if len(result) == 1:
        return set_proposal_cache(result[0])
    else:
        return None

def set_proposal_cache(proposal, call=None):
    """Set the 'cache' field of the proposal.
    This is computed data that will not be stored with the document.
    Depends on login, access, status, etc.
    """
    from .reviews import get_proposal_reviews_count
    proposal['cache'] = cache = dict(is_readable=False,
                                       is_editable=False,
                                       is_submittable=False,
                                       is_reviewer=False)
    # Get the call for the proposal.
    if call is None:
        cache['call'] = anubis.call.get_call(proposal['call'])
    else:
        cache['call'] = call
    if flask.g.is_admin:
        cache['is_readable'] = True
        cache['is_editable'] = True
        cache['is_submittable'] = True
        cache['is_reviewer'] = True
        cache['reviews_count'] = get_proposal_reviews_count(proposal)
    elif flask.g.current_user:
        if flask.g.current_user['username'] == proposal['user']:
            cache['is_readable'] = True
            cache['is_editable'] = cache['call']['cache']['is_open'] and \
                                   not proposal.get('submitted')
            cache['is_submittable'] = cache['call']['cache']['is_open'] and \
                                      not proposal['errors']
        elif cache['call']['cache']['is_reviewer']:
            cache['is_readable'] = True
            cache['is_reviewer'] = True
    return proposal
