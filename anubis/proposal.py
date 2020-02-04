"Proposals."

import flask

import anubis.call
import anubis.user
import anubis.decision

from . import constants
from . import utils
from .saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('proposals', DESIGN_DOC):
        print(' > Updated proposals design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.identifier, null);}"},
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.call, doc.user);}"},
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.user, null);}"},
        'call_user': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit([doc.call, doc.user], null);}"},
        'unsubmitted': {'reduce': '_count',
                        'map': "function (doc) {if (doc.doctype !== 'proposal' || doc.submitted) return; emit(doc.user, null);}"},
    }
}

blueprint = flask.Blueprint('proposal', __name__)

@blueprint.route('/<pid>')
@utils.login_required
def display(pid):
    "Display the proposal."
    from .review import get_reviewer_review
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])
    decision = anubis.decision.get_decision(proposal['decision'])
    if not allow_view(proposal):
        utils.flash_error('You are not allowed to view this proposal.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))
    am_submitter = flask.g.current_user and \
                   flask.g.current_user['username'] == proposal['user']
    am_reviewer = anubis.call.am_reviewer(call)
    my_review = get_reviewer_review(proposal, flask.g.current_user)
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    allow_link_decision = anubis.decision.allow_link(decision)
    allow_create_decision = anubis.decision.allow_create(proposal)
    allow_view_decision = decision and \
                          decision.get('finalized') and \
                          call['access'].get('allow_submitter_view_decision')
    return flask.render_template('proposal/display.html',
                                 proposal=proposal,
                                 call=call,
                                 allow_edit=allow_edit(proposal),
                                 allow_delete=allow_delete(proposal),
                                 allow_submit=allow_submit(proposal),
                                 am_submitter=am_submitter,
                                 am_reviewer=am_reviewer,
                                 my_review=my_review,
                                 allow_view_reviews=allow_view_reviews,
                                 decision=decision,
                                 allow_link_decision=allow_link_decision,
                                 allow_create_decision=allow_create_decision,
                                 allow_view_decision=allow_view_decision)

@blueprint.route('/<pid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(pid):
    "Edit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])

    if utils.http_GET():
        if not allow_edit(proposal):
            utils.flash_error('You are not allowed to edit this proposal.')
            return flask.redirect(utils.referrer_or_home())
        return flask.render_template('proposal/edit.html',
                                     proposal=proposal,
                                     call=call)

    elif utils.http_POST():
        if not allow_edit(proposal):
            utils.flash_error('You are not allowed to edit this proposal.')
            return flask.redirect(
                flask.url_for('.display', pid=proposal['identifier']))
        try:
            with ProposalSaver(proposal) as saver:
                saver['title'] = flask.request.form.get('_title') or None
                value = flask.request.form.get('_user')
                if value and value != proposal['user']:
                    user = anubis.user.get_user(username=value, email=value)
                    if user:
                        saver.set_user(user)
                    else:
                        raise ValueError('No such user.')
                for field in call['proposal']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(utils.referrer_or_home())
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
    if not allow_view(proposal):
        utils.flash_error('You are not allowed to read this proposal.')
        return flask.redirect(utils.referrer_or_home())

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
    if not allow_view(proposal):
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


class ProposalSaver(FieldMixin, AttachmentSaver):
    "Proposal document saver context."

    DOCTYPE = constants.PROPOSAL

    def __init__(self, doc=None, call=None):
        if doc:
            super().__init__(doc=doc)
        elif call:
            super().__init__(doc=None)
            self.set_call(call)
            self.set_user(flask.g.current_user)
        else:
            raise ValueError('doc or call must be specified')

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_user(self, user):
        "Set the user for the proposal; must be called when creating."
        if get_call_user_proposal(self.doc['call'], user['username']):
            raise ValueError('User already has a proposal in the call.')
        self.doc['user'] = user['username']

    def set_call(self, call):
        "Set the call for the proposal; must be called when creating."
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
        for field in call['proposal']:
            self.set_field_value(field)

    def set_submitted(self):
        if not allow_submit(self.doc):
            raise ValueError('Submit is disallowed.')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not allow_submit(self.doc):
            raise ValueError('Unsubmit is disallowed.')
        self.doc.pop('submitted', None)


def get_proposal(pid, refetch=False):
    "Return the proposal with the given identifier."
    try:
        if refetch: raise KeyError
        return flask.g.cache[pid]
    except KeyError:
        result = [r.doc for r in flask.g.db.view('proposals', 'identifier',
                                                 key=pid,
                                                 include_docs=True)]
        if len(result) == 1:
            proposal = result[0]
            flask.g.cache[pid] = proposal
            return proposal
        else:
            return None

def allow_view(proposal):
    "Admin, the user of the proposal, and the reviewers may view a proposal."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if anubis.call.am_reviewer(anubis.call.get_call(proposal['call'])):
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
    if proposal.get('submitted'): return False
    if proposal['errors']: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    return (flask.g.current_user['username'] == proposal['user']
            and call['cache']['is_open'])
    
def get_call_user_proposal(cid, username):
    "Get the proposal created by the user in the call."
    result = [r.doc for r in flask.g.db.view('proposals', 'call_user',
                                             key=[cid, username],
                                             reduce=False,
                                             include_docs=True)]
    if len(result) == 1:
        return result[0]
    else:
        return None
