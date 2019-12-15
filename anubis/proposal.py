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
    if db.put_design('proposals', DESIGN_DOC):
        print(' > Updated proposals design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.identifier, null);}"},
        # NOTE: excludes unsubmitted proposals
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal' || !doc.submitted) return; emit(doc.call, doc.user);}"},
        # NOTE: includes unsubmitted proposals
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.user, null);}"},
        # Unsubmitted proposals by user in any call.
        'unsubmitted': {'reduce': '_count',
                        'map': "function (doc) {if (doc.doctype !== 'proposal' || doc.submitted) return; emit(doc.user, null);}"},
    }
}

blueprint = flask.Blueprint('proposal', __name__)

@blueprint.route('/<pid>')
@utils.login_required
def display(pid):
    "Display the proposal."
    from .review import get_my_review
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not allow_view(proposal):
        utils.flash_error('You are not allowed to view this proposal.')
        return flask.redirect(
            flask.url_for('call.display',
                          cid=proposal['cache']['call']['identifier']))
    is_user = flask.g.current_user and \
              flask.g.current_user['username'] == proposal['user']
    is_reviewer = anubis.call.is_reviewer(proposal['cache']['call'])
    my_review = get_my_review(proposal, flask.g.current_user)
    allow_view_reviews = anubis.call.allow_view_reviews(proposal['cache']['call'])
    return flask.render_template('proposal/display.html',
                                 proposal=proposal,
                                 allow_edit=allow_edit(proposal),
                                 allow_delete=allow_delete(proposal),
                                 allow_submit=allow_submit(proposal),
                                 is_user=is_user,
                                 is_reviewer=is_reviewer,
                                 my_review=my_review,
                                 allow_view_reviews=allow_view_reviews)

@blueprint.route('/<pid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(pid):
    "Edit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        if not allow_edit(proposal):
            utils.flash_error('You are not allowed to edit this proposal.')
            return flask.redirect(
                flask.url_for('.display', pid=proposal['identifier']))
        return flask.render_template('proposal/edit.html', proposal=proposal)

    elif utils.http_POST():
        if not allow_edit(proposal):
            utils.flash_error('You are not allowed to edit this proposal.')
            return flask.redirect(
                flask.url_for('.display', pid=proposal['identifier']))
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
        if not allow_delete(proposal):
            utils.flash_error('You are not allowed to delete this proposal.')
            return flask.redirect(
                flask.url_for('.display', pid=proposal['identifier']))
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
    if not allow_submit(proposal):
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
    if not allow_submit(proposal):
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
    if not proposal['cache']['allow_read']:
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
    if not proposal['cache']['allow_read']:
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
        if not allow_submit(self.doc):
            raise ValueError('Submit is disallowed.')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not allow_submit(self.doc):
            raise ValueError('Unsubmit is disallowed.')
        self.doc.pop('submitted', None)


def get_proposal(pid, cache=True):
    "Return the proposal with the given identifier."
    result = [r.doc for r in flask.g.db.view('proposals', 'identifier',
                                             key=pid,
                                             include_docs=True)]
    if len(result) == 1:
        if cache:
            return set_cache(result[0])
        else:
            return result[0]
    else:
        return None

def allow_view(proposal):
    "Admin, the user of the proposal, and the reviewers may view it."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if anubis.call.is_reviewer(proposal['cache']['call']):
        return bool(proposal.get('submitted'))
    return flask.g.current_user['username'] == proposal['user']

def allow_edit(proposal):
    "Admin may edit the proposal. The user may edit if not submitted."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if proposal.get('submitted'): return False
    return flask.g.current_user['username'] == proposal['user']

def allow_delete(proposal):
    "Admin may delete the proposal. The user may delete if not submitted."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if proposal.get('submitted'): return False
    return flask.g.current_user['username'] == proposal['user']

def allow_submit(proposal):
    """Admin may submit the proposal if there are no errors.
    The user may submit the proposal if the call is open.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if proposal.get('submitted'): return False
    if proposal['errors']: return False
    return (flask.g.current_user['username'] == proposal['user']
            and proposal['cache']['call']['cache']['is_open'])
    
def set_cache(proposal, call=None):
    """Set the cached, non-saved fields of the review.
    This de-references the call of the proposal.
    """
    proposal['cache'] = cache = {}
    if call is None:
        cache['call'] = anubis.call.get_call(proposal['call'], cache=True)
    else:
        cache['call'] = call
    if anubis.call.allow_view_reviews(cache['call']):
        cache['all_reviews_count'] = utils.get_count('reviews', 'proposal',
                                                     proposal['identifier'])
    return proposal
