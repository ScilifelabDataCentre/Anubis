"Proposal in a call."

import os.path

import flask

import anubis.call
import anubis.user
import anubis.decision
import anubis.grant
import anubis.review
from anubis import constants
from anubis import utils
from anubis.saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('proposals', DESIGN_DOC):
        app.logger.info('Updated proposals design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.identifier, doc.title);}"},
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.call, doc.user);}"},
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.user, doc.identifier);}"},
        'call_user': {'map': "function (doc) {if (doc.doctype !== 'proposal') return; emit([doc.call, doc.user], doc.identifier);}"},
        'unsubmitted': {'reduce': '_count',
                        'map': "function (doc) {if (doc.doctype !== 'proposal' || doc.submitted) return; emit(doc.user, doc.identifier);}"},
        'call_category': {'reduce': '_count',
                          'map': "function (doc) {if (doc.doctype !== 'proposal' || !doc.category) return; emit([doc.call, doc.category], doc.identifier);}"},
    }
}

blueprint = flask.Blueprint('proposal', __name__)

@blueprint.route('/<pid>')
@utils.login_required
def display(pid):
    "Display the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])
    if not allow_view(proposal):
        return utils.error('You are not allowed to view this proposal.',
                           flask.url_for('call.display',
                                         cid=call['identifier']))
    am_submitter = flask.g.current_user and \
                   flask.g.current_user['username'] == proposal['user']
    am_reviewer = anubis.call.am_reviewer(call)
    my_review = anubis.review.get_reviewer_review(proposal,flask.g.current_user)
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    decision = anubis.decision.get_decision(proposal.get('decision'))
    allow_create_decision = anubis.decision.allow_create(proposal)
    allow_link_decision = anubis.decision.allow_link(decision)
    allow_view_decision = decision and \
                          decision.get('finalized') and \
                          call['access'].get('allow_submitter_view_decision')
    grant = anubis.grant.get_grant_proposal(proposal['identifier'])
    allow_create_grant = anubis.grant.allow_create(proposal)
    allow_link_grant = anubis.grant.allow_link(grant)
    return flask.render_template('proposal/display.html',
                                 proposal=proposal,
                                 call=call,
                                 allow_edit=allow_edit(proposal),
                                 allow_delete=allow_delete(proposal),
                                 allow_submit=allow_submit(proposal),
                                 allow_transfer=allow_transfer(proposal),
                                 am_submitter=am_submitter,
                                 am_reviewer=am_reviewer,
                                 my_review=my_review,
                                 allow_view_reviews=allow_view_reviews,
                                 decision=decision,
                                 allow_create_decision=allow_create_decision,
                                 allow_link_decision=allow_link_decision,
                                 allow_view_decision=allow_view_decision,
                                 grant=grant,
                                 allow_create_grant=allow_create_grant,
                                 allow_link_grant=allow_link_grant)

@blueprint.route('/<pid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(pid):
    "Edit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])

    if utils.http_GET():
        if not allow_edit(proposal):
            return utils.error('You are not allowed to edit this proposal.')
        return flask.render_template('proposal/edit.html',
                                     proposal=proposal,
                                     call=call)

    elif utils.http_POST():
        if not allow_edit(proposal):
            return utils.error('You are not allowed to edit this proposal.',
                               flask.url_for('.display',
                                             pid=proposal['identifier']))
        try:
            with ProposalSaver(proposal) as saver:
                saver['title'] = flask.request.form.get('_title') or None
                category = flask.request.form.get('_category')
                if category in call.get('categories', []):
                    saver['category'] = category
                elif category == '__none__':
                    saver['category'] = None
                for field in call['proposal']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            return utils.error(error)
        if flask.request.form.get('_save') == 'submit':
            proposal = get_proposal(pid, refresh=True)
            try:
                with ProposalSaver(proposal) as saver:
                    saver.set_submitted()  # Tests whether allowed or not.
            except ValueError as error:
                utils.flash_error(error)
            else:
                utils.flash_message('Proposal saved and submitted.')
                send_submission_email(proposal)

        elif allow_submit(proposal) and not proposal.get('submitted'):
            utils.flash_warning('Proposal was saved but not submitted.'
                                ' You must explicitly submit it!')
        # NOTE: Repeat field has not been implemented for proposal.
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

    elif utils.http_DELETE():
        if not allow_delete(proposal):
            return utils.error('You are not allowed to delete this proposal.',
                               flask.url_for('.display',
                                             pid=proposal['identifier']))
        decision = anubis.decision.get_decision(proposal.get('decision'))
        if decision:
            utils.delete(decision)
        reviews = utils.get_docs_view('reviews', 'proposal',
                                      proposal['identifier'])
        for review in reviews:
            utils.delete(review)
        utils.delete(proposal)
        utils.flash_message(f"Deleted proposal {pid}.")
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/<pid>/transfer', methods=['GET', 'POST'])
@utils.login_required
def transfer(pid):
    "Transfer ownership of he proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    if not allow_transfer(proposal):
        return utils.error('You are not allowed to transfer ownership of'
                           ' this proposal.')

    if utils.http_GET():
        return flask.render_template('proposal/transfer.html',proposal=proposal)

    elif utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                value = flask.request.form.get('user')
                if value:
                    user = anubis.user.get_user(username=value, email=value)
                    if user:
                        saver.set_user(user)
                    else:
                        raise ValueError('No such user.')
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(
            flask.url_for('.display', pid=proposal['identifier']))

@blueprint.route('/<pid>/submit', methods=['POST'])
@utils.login_required
def submit(pid):
    "Submit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))

    if utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                saver.set_submitted()  # Tests whether allowed or not.
        except ValueError as error:
            utils.flash_error(error)
        else:
            utils.flash_message('Proposal was submitted.')
            send_submission_email(proposal)
        return flask.redirect(flask.url_for('.display', pid=pid))

def send_submission_email(proposal):
    "Send an email to the user verifying the proposal submission."
    user = anubis.user.get_user(username=proposal['user'])
    if not (user and user['email']): return
    site = flask.current_app.config['SITE_NAME']
    title = f"Proposal {proposal['identifier']} has been submitted in {site}"
    url = utils.url_for('.display', pid=proposal['identifier'])
    text = "Your proposal\n\n" \
           f"  {proposal['identifier']} {proposal['title']}\n\n"\
           f"has been submitted in the {site} system.\n\n" \
           f"View it at {url}\n\n" \
           "/The Anubis system"
    utils.send_email(user['email'], title, text)

@blueprint.route('/<pid>/unsubmit', methods=['POST'])
@utils.login_required
def unsubmit(pid):
    "Unsubmit the proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))

    if utils.http_POST():
        try:
            with ProposalSaver(proposal) as saver:
                saver.set_unsubmitted()  # Tests whether allowed or not.
        except ValueError as error:
            utils.flash_error(error)
        else:
            utils.flash_warning('Proposal was unsubmitted.')
        return flask.redirect(flask.url_for('.display', pid=pid))

@blueprint.route('/<pid>/logs')
@utils.login_required
def logs(pid):
    "Display the log records of the given proposal."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    if not allow_view(proposal):
        return utils.error('You are not allowed to read this proposal.',
                           flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Proposal {proposal['identifier']}",
        back_url=flask.url_for('.display', pid=proposal['identifier']),
        logs=utils.get_logs(proposal['_id']))

@blueprint.route('/<pid>/document/<fid>')
@utils.login_required
def document(pid, fid):
    "Download the proposal document (attachment file) for the given field id."
    proposal = get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    if not allow_view(proposal):
        return utils.error('You are not allowed to read this proposal.',
                           flask.url_for('home'))
    try:
        doc = get_document(proposal, fid)
    except KeyError:
        return utils.error('No such document in proposal.',
                           flask.url_for('.display',pid=proposal['identifier']))
    response = flask.make_response(doc['content'])
    response.headers.set('Content-Type', doc['content_type'])
    response.headers.set('Content-Disposition',
                         'attachment',
                         filename=doc['filename'])
    return response

def get_document(proposal, fid):
    "Return a dictionary containing the document in the field of the proposal."
    documentname = proposal['values'][fid]
    # This may generate a KeyError, which is correct.
    stub = proposal['_attachments'][documentname]
    # Colon ':' is a problematic character in filenames.
    # Replace it by dash '-'; used as general glue character here.
    pid = proposal['identifier'].replace(':', '-')
    ext = os.path.splitext(documentname)[1]
    outfile = flask.g.db.get_attachment(proposal, documentname)
    return dict(filename=f"{pid}-{fid}{ext}",
                content=outfile.read(),
                content_type=stub['content_type'])
    

class ProposalSaver(FieldMixin, AttachmentSaver):
    "Proposal document saver context."

    DOCTYPE = constants.PROPOSAL

    def __init__(self, doc=None, call=None, user=None):
        if doc:
            super().__init__(doc=doc)
        elif call and user:
            super().__init__(doc=None)
            self.set_call(call)
            self.set_user(user)
        else:
            raise ValueError('doc or call+user must be specified')

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_user(self, user):
        "Set the user (owner) for the proposal; must be called when creating."
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
        self.set_fields_values(call['proposal'])

    def set_submitted(self):
        if not allow_submit(self.doc):
            raise ValueError('Submit cannot be done; proposal is incomplete,'
                             ' or call is closed.')
        self.doc['submitted'] = utils.get_time()

    def set_unsubmitted(self):
        if not allow_submit(self.doc):
            raise ValueError('Unsubmit cannot be done; call is closed.')
        self.doc.pop('submitted', None)


def get_proposal(pid, refresh=False):
    """Return the proposal with the given identifier.
    Return None if not found.
    """
    try:
        if refresh: raise KeyError
        return flask.g.cache[pid]
    except KeyError:
        docs = [r.doc for r in flask.g.db.view('proposals', 'identifier',
                                               key=pid,
                                               include_docs=True)]
        if len(docs) == 1:
            proposal = docs[0]
            flask.g.cache[pid] = proposal
            flask.g.cache[proposal["_id"]] = proposal
            return proposal
        else:
            return None

def allow_view(proposal):
    """The admin, staff and call owner may view a proposal.
    The user of the proposal may view it.
    The reviewers may view it.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    call = anubis.call.get_call(proposal['call'])
    if anubis.call.am_call_owner(call): return True
    if anubis.call.am_reviewer(call): return bool(proposal.get('submitted'))
    if flask.g.current_user['username'] == proposal['user']: return True
    return False

def allow_edit(proposal):
    """The admin and call owner may edit the proposal.
    The user may edit if not submitted.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    if anubis.call.am_call_owner(call): return True
    if proposal.get('submitted'): return False
    if flask.g.current_user['username'] == proposal['user']: return True
    return False

def allow_delete(proposal):
    """The admin, and call owner may delete the proposal.
    The user may delete if not submitted.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    if anubis.call.am_call_owner(call): return True
    if proposal.get('submitted'): return False
    if flask.g.current_user['username'] == proposal['user']: return True
    return False

def allow_submit(proposal):
    """Only if there are no errors.
    The admin and owner of the call may submit/unsubmit the proposal.
    The user may submit/unsubmit the proposal if the call is open.
    """
    if not flask.g.current_user: return False
    if proposal['errors']: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    if anubis.call.am_call_owner(call): return True
    if flask.g.current_user['username'] == proposal['user'] and \
       call['tmp']['is_open']: return True
    return False
    
def allow_transfer(proposal):
    """The admin and staff may transfer ownership of a proposal.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    return False

def get_call_user_proposal(cid, username):
    "Get the proposal created by the user in the call."
    result = [r.doc for r in flask.g.db.view('proposals', 'call_user',
                                             key=[cid, username],
                                             include_docs=True)]
    if len(result) == 1:
        return result[0]
    else:
        return None
