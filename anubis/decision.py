"Decision regarding a proposal."

import flask

import anubis.proposal

from . import constants
from . import utils
from .saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('decisions', DESIGN_DOC):
        print(' > Updated decisions design document.')

DESIGN_DOC = {
    'views': {
        # Decisions for all proposals in call.
        'call': {'reduce': '_count',
                 'map': "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.call, doc.proposal);}"},
        # Decision for a proposal.
        'proposal': {'map': "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.proposal, null);}"},
    }
}

blueprint = flask.Blueprint('decision', __name__)

@blueprint.route('/create/<pid>', methods=['POST'])
@utils.login_required
def create(pid):
    "Create a new decision for the proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    try:
        if not allow_create(proposal):
            utils.flash_error('You may not create a decision for the proposal.')
            raise ValueError
        decision = get_decision(proposal.get('decision'))
        if decision is not None:
            utils.flash_message('The decision already exists.')
            return flask.redirect(
                flask.url_for('.display', iuid=decision['_id']))
        with DecisionSaver(proposal=proposal) as saver:
            pass
        decision = saver.doc
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver['decision'] = decision['_id']
    except ValueError as error:
        pass
    try:
        return flask.redirect(flask.request.form['_next'])
    except KeyError:
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

@blueprint.route('/<iuid:iuid>')
def display(iuid):
    "Display the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))
    if not allow_link(decision):
        utils.flash_error('You are not allowed to view this decision.')
        return flask.redirect(
            flask.url_for('proposal.display',
                          pid=decision['cache']['proposal']['identifier']))
    return flask.render_template('decision/display.html',
                                 decision=decision,
                                 allow_edit=allow_edit(decision),
                                 allow_delete=allow_delete(decision),
                                 allow_finalize=allow_finalize(decision),
                                 allow_unfinalize=allow_unfinalize(decision))

@blueprint.route('/<iuid:iuid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(iuid):
    "Edit the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        if not allow_edit(decision):
            utils.flash_error('You are not allowed to edit this decision.')
            return flask.redirect(
                flask.url_for('.display', iuid=decision['_id']))
        return flask.render_template('decision/edit.html', decision=decision)

    elif utils.http_POST():
        if not allow_edit(decision):
            utils.flash_error('You are not allowed to edit this decision.')
            return flask.redirect(
                flask.url_for('.display', iuid=decision['_id']))
        try:
            with DecisionSaver(doc=decision) as saver:
                for field in decision['cache']['call']['decision']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(utils.referrer_or_home())
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

    elif utils.http_DELETE():
        if not allow_delete(decision):
            utils.flash_error('You are not allowed to delete this decision.')
            return flask.redirect(
                flask.url_for('.display', iuid=decision['_id']))
        proposal = decision['cache']['proposal']
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver['decision'] = None
        utils.delete(decision)
        utils.flash_message('Deleted decision.')
        return flask.redirect(
            flask.url_for('proposal.display', pid=proposal['identifier']))

@blueprint.route('/<iuid:iuid>/finalize', methods=['POST'])
@utils.login_required
def finalize(iuid):
    "Finalize the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))
    if not allow_finalize(decision):
        utils.flash_error('You are not allowed to finalize this decision.')
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

    if utils.http_POST():
        try:
            with DecisionSaver(doc=decision) as saver:
                saver['finalized'] = utils.get_time()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

@blueprint.route('/<iuid:iuid>/unfinalize', methods=['POST'])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))
    if not allow_unfinalize(decision):
        utils.flash_error('You are not allowed to unfinalize this decision.')
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

    if utils.http_POST():
        try:
            with DecisionSaver(doc=decision) as saver:
                saver['finalized'] = None
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', iuid=decision['_id']))

@blueprint.route('/<iuid:iuid>/logs')
@utils.login_required
def logs(iuid):
    "Display the log records of the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title="Decision for" \
              f" {decision['cache']['proposal']['identifier']}",
        back_url=flask.url_for('.display', iuid=decision['_id']),
        logs=utils.get_logs(decision['_id']))

@blueprint.route('/<iuid:iuid>/document/<documentname>')
@utils.login_required
def document(iuid, documentname):
    "Download the given decision document (attachment file)."
    try:
        decision = get_decision(iuid)
    except KeyError:
        utils.flash_error('No such decision.')
        return flask.redirect(flask.url_for('home'))
    if not allow_link(decision):
        utils.flash_error('You are not allowed to read this decision.')
        return flask.redirect(flask.url_for('home'))

    try:
        stub = decision['_attachments'][documentname]
    except KeyError:
        utils.flash_error('No such document in decision.')
        return flask.redirect(
            flask.url_for('.display', iuid=decision['identifier']))
    outfile = flask.g.db.get_attachment(decision, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=documentname)
    return response


class DecisionSaver(FieldMixin, AttachmentSaver):
    "Decision document saver context."

    DOCTYPE = constants.DECISION

    def __init__(self, doc=None, proposal=None):
        if doc:
            super().__init__(doc=doc)
        elif proposal:
            super().__init__(doc=None)
            self.set_proposal(proposal)
        else:
            raise ValueError('doc or proposal must be specified')

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_proposal(self, proposal):
        "Set the proposal for the decision; must be called when creating."
        if self.doc.get('call'):
            raise ValueError('call has already been set')
        self.doc['proposal'] = proposal['identifier']
        call = proposal['cache']['call']
        self.doc['call'] = call['identifier']
        for field in call['decision']:
            self.set_field_value(field)


def get_decision(iuid, cache=True):
    "Get the decision by its iuid."
    if not iuid: return None
    decision = flask.g.db[iuid]
    if decision['doctype'] != constants.DECISION: raise ValueError
    if cache:
        return set_cache(decision)
    else:
        return decision

def allow_create(proposal):
    "Admin and chair may create a decision for a submitted proposal."
    if not proposal.get('submitted'): return False
    if not flask.g.current_user: return False
    if proposal.get('decision'): return False
    if flask.g.am_admin: return True
    return anubis.call.am_chair(decision['cache']['call'])

def allow_link(decision):
    """Admin may view link to any decision.
    Reviewer may view link to any decision in a call.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return anubis.call.am_reviewer(decision['cache']['call'])

def allow_edit(decision):
    "Admin and chair may edit an unfinalized decision."
    if decision.get('finalized'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return anubis.call.am_chair(decision['cache']['call'])

def allow_delete(decision):
    "Admin may delete a decision."
    return flask.g.am_admin

def allow_finalize(decision):
    "Admin and chaie may finalize if the decision contains no errors."
    if decision.get('finalized'): return False
    if decision.get('errors'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return anubis.call.am_chair(decision['cache']['call'])

def allow_unfinalize(decision):
    "Admin and decisioner may unfinalize the decision."
    if not decision.get('finalized'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return anubis.call.am_chair(decision['cache']['call'])

def set_cache(decision, call=None):
    """Set the cached, non-saved fields of the decision.
    This de-references the call and proposal of the decision.
    """
    decision['cache'] = cache = {}
    if call is None:
        cache['call'] = call = anubis.call.get_call(decision['call'])
    else:
        cache['call'] = call
    cache['proposal'] = anubis.proposal.get_proposal(decision['proposal'])
    return decision
