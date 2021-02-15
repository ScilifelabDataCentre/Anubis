"Grant dossier based on a proposal, which (presumably) got a positive decision."

import io
import os.path
import zipfile

import flask

import anubis.call
import anubis.proposal
import anubis.user
import anubis.decision
from anubis import constants
from anubis import utils
from anubis.saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('grants', DESIGN_DOC):
        app.logger.info('Updated grants design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.identifier, doc.proposal);}"},
        'call': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.call, doc.identifier);}"},
        'proposal': {'reduce': '_count',
                     'map': "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.proposal, doc.identifier);}"},
        'user': {'reduce': '_count',
                 'map': "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.user, doc.identifier);}"},
    }
}

blueprint = flask.Blueprint('grant', __name__)

@blueprint.route('/create/<pid>', methods=['POST'])
@utils.login_required
def create(pid):
    "Create a grant dossier for the proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    try:
        if not allow_create(proposal):
            raise ValueError('You may not create a grant dossier for the proposal.')
        grant = get_grant_proposal(pid)
        if grant is not None:
            utils.flash_message('The grant dossier already exists.')
            return flask.redirect(
                flask.url_for('.display', gid=grant['identifier']))
        with GrantSaver(proposal=proposal) as saver:
            pass
        grant = saver.doc
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver['grant'] = grant['identifier']
    except ValueError as error:
        utils.flash_error(error)
    try:
        return flask.redirect(flask.request.form['_next'])
    except KeyError:
        return flask.redirect(
            flask.url_for('.display', gid=grant['identifier']))

@blueprint.route('/<gid>')
@utils.login_required
def display(gid):
    "Display the grant dossier."
    grant = get_grant(gid)
    if grant is None:
        return utils.error('No such grant dossier.', flask.url_for('home'))
    if not allow_view(grant):
        return utils.error('You are not allowed to view this grant dossier.',
                           flask.url_for('call.display', cid=grant['call']))
    proposal = anubis.proposal.get_proposal(grant['proposal'])
    call = anubis.call.get_call(grant['call'])
    call_grants_count = utils.get_count('grants', 'call', grant['call'])
    return flask.render_template('grant/display.html',
                                 grant=grant,
                                 proposal=proposal,
                                 call=call,
                                 call_grants_count=call_grants_count,
                                 allow_view=allow_view(grant),
                                 allow_edit=allow_edit(grant),
                                 allow_delete=allow_delete(grant))

@blueprint.route('/<gid>/edit', methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(gid):
    "Edit the grant record."
    grant = get_grant(gid)
    if grant is None:
        return utils.error('No such grant.', flask.url_for('home'))
    call = anubis.call.get_call(grant['call'])

    if utils.http_GET():
        if not allow_edit(grant):
            return utils.error(
                'You are not allowed to edit this grant dossier.',
                flask.url_for('.display', gid=grant['identifier']))
        return flask.render_template('grant/edit.html',
                                     grant=grant,
                                     call=call)

    elif utils.http_POST():
        if not allow_edit(grant):
            return utils.error(
                'You are not allowed to edit this grant dossier.',
                flask.url_for('.display', gid=grant['identifier']))
        try:
            with GrantSaver(doc=grant) as saver:
                saver.set_fields_values(call.get('grant', []),
                                        form=flask.request.form)
        except ValueError as error:
            return utils.error(error)
        if saver.repeat_changed:
            url = flask.url_for('.edit', gid=grant['identifier'])
        else:
            url = flask.url_for('.display', gid=grant['identifier'])
        return flask.redirect(url)

    elif utils.http_DELETE():
        if not allow_delete(grant):
            return utils.error(
                'You are not allowed to delete this grant dossier.',
                flask.url_for('.display', gid=grant['identifier']))
        proposal = anubis.proposal.get_proposal(grant['proposal'])
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver['grant'] = None
        utils.delete(grant)
        utils.flash_message('Deleted grant dossier.')
        return flask.redirect(
            flask.url_for('proposal.display', pid=proposal['identifier']))

@blueprint.route('/<gid>/document/<fid>')
@utils.login_required
def document(gid, fid):
    "Download the grant document (attachment file) for the given field id."
    try:
        grant = get_grant(gid)
    except KeyError:
        return utils.error('No such grant dossier.', flask.url_for('home'))
    if not allow_view(grant):
        return utils.error('You are not allowed to read this grant dossier.',
                           flask.url_for('home'))

    try:
        documentname = grant['values'][fid]
        stub = grant['_attachments'][documentname]
    except KeyError:
        return utils.error('No such document in grant dossier.',
                           flask.url_for('.display',
                                         iuid=grant['identifier']))
    # Colon ':' is a problematic character in filenames; replace by dash '-'.
    gid = gid.replace(':', '-')
    ext = os.path.splitext(documentname)[1]
    # Add the appropriate file extension to the filename.
    filename = f"{gid}-{fid}{ext}"
    outfile = flask.g.db.get_attachment(grant, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response

@blueprint.route('/<gid>.zip')
@utils.login_required
def grant_zip(gid):
    "Return a zip file containing all documents in the grant dossier."
    try:
        grant = get_grant(gid)
    except KeyError:
        return utils.error('No such grant dossier.', flask.url_for('home'))
    if not allow_view(grant):
        return utils.error('You are not allowed to read this grant dossier.',
                           flask.url_for('home'))
    call = anubis.call.get_call(grant['call'])
    # Colon ':' is a problematic character in filenames; replace by dash '_'
    gid = gid.replace(':', '-')
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zip:
        # First non-repeated document fields.
        for field in call['grant']:
            if field.get('repeat'): continue
            if field['type'] != constants.DOCUMENT: continue
            try:
                documentname = grant['values'][field['identifier']]
            except KeyError:
                continue
            ext = os.path.splitext(documentname)[1]
            stub = grant['_attachments'][documentname]
            outfile = flask.g.db.get_attachment(grant, documentname)
            filename = f"{gid}-{field['identifier']}{ext}"
            zip.writestr(filename, outfile.read())
        # Then repeated document fields.
        for field in call['grant']:
            if field['type'] != constants.REPEAT: continue
            n_fields = grant['values'].get(field['identifier']) or 0
            for n in range(1, n_fields + 1):
                for field2 in call['grant']:
                    if field2.get('repeat') != field['identifier']: continue
                    if field2['type'] != constants.DOCUMENT: continue
                    field2name = f"{field2['identifier']}-{n}"
                    try:
                        documentname = grant['values'][field2name]
                    except KeyError:
                        continue
                    ext = os.path.splitext(documentname)[1]
                    stub = grant['_attachments'][documentname]
                    outfile = flask.g.db.get_attachment(grant, documentname)
                    filename = f"{gid}-{field2['identifier']}-{n}{ext}"
                    zip.writestr(filename, outfile.read())
    response = flask.make_response(output.getvalue())
    response.headers.set('Content-Type', constants.ZIP_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{gid}.zip")
    return response


@blueprint.route('/<gid>/logs')
@utils.login_required
def logs(gid):
    "Display the log records of the given grant dossier."
    grant = get_grant(gid)
    if grant is None:
        return utils.error('No such grant dossier.', flask.url_for('home'))
    if not allow_view(grant):
        return utils.error('You are not allowed to read this grant dossier.',
                           flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Grant {grant['identifier']}",
        back_url=flask.url_for('.display', gid=grant['identifier']),
        logs=utils.get_logs(grant['_id']))


class GrantSaver(FieldMixin, AttachmentSaver):
    "Grant dossier document saver context."

    DOCTYPE = constants.GRANT

    def __init__(self, doc=None, proposal=None):
        if doc:
            super().__init__(doc=doc)
        elif proposal:
            super().__init__(doc=None)
            self.set_proposal(proposal)
            self['user'] = proposal['user']
        else:
            raise ValueError('doc or proposal must be specified')

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_proposal(self, proposal):
        "Set the proposal for the grant dossier; must be called when creating."
        if self.doc.get('proposal'):
            raise ValueError('proposal has already been set')
        self.doc['proposal'] = proposal['identifier']
        self.doc['call'] = proposal['call']
        self.doc['identifier'] = "{}:G:{}".format(*proposal['identifier'].split(":"))
        call = anubis.call.get_call(proposal['call'])
        self.set_fields_values(call.get('grant', []))


def get_grant(gid):
    """Return the grant dossier with the given identifier.
    Return None if not found.
    """
    docs = [r.doc for r in flask.g.db.view('grants', 'identifier',
                                           key=gid,
                                           include_docs=True)]
    if len(docs) == 1:
        return docs[0]
    else:
        return None

def get_grant_proposal(pid):
    """Return the grant dossier for the proposal with the given identifier.
    Return None if not found.
    """
    docs = [r.doc for r in flask.g.db.view('grants', 'proposal',
                                           key=pid,
                                           include_docs=True)]
    if len(docs) == 1:
        return docs[0]
    else:
        return None

def allow_create(proposal):
    "The admin and staff may create a grant dossier."
    if not flask.g.current_user: return False
    if not proposal.get('submitted'): return False  # Sanity check.
    if not proposal.get('decision'): return False   # Sanity check.
    decision = anubis.decision.get_decision(proposal['decision'])
    if not (decision and decision.get('finalized')):  # Sanity check.
        return False
    # Can't check for positive decision, since that encoding is not hard-wired.
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    return False

def allow_view(grant):
    """The admin, staff and proposal user (= grant receiver) may 
    view the grant dossier.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    if flask.g.current_user['username'] == grant['user']: return True
    return False

def allow_edit(grant):
    """The admin, staff and proposal user (= grant receiver) may in general
    edit the grant dossier. Some fields have special edit privileges.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    # XXX special field privileges!
    if flask.g.current_user['username'] == grant['user']: return True
    return False

def allow_link(grant):
    """Admin and staff may view link to any grant dossier.
    User may link to her own grant dossier.
    """
    if not grant: return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    if flask.g.current_user['username'] == grant['user']: return True
    return False

def allow_delete(grant):
    "Only the admin may delete a grant dossier."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    return False
