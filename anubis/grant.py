"""Grant creation, display and edit.

A grant is dossier based on a proposal, which (presumably) got a
positive decision. It may contain information and documents relating
to the payment and tracking of the grant.
"""

import io
import os.path
import zipfile

import flask

import anubis.call
import anubis.database
import anubis.decision
import anubis.proposal
import anubis.user
from anubis import constants
from anubis import utils
from anubis.saver import Saver, FieldSaverMixin, AccessSaverMixin


blueprint = flask.Blueprint("grant", __name__)


@blueprint.route("/create/<pid>", methods=["POST"])
@utils.login_required
def create(pid):
    "Create a grant dossier for the proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error("No such proposal.")
    if not allow_create(proposal):
        raise utils.error("You may not create a grant dossier for the proposal.")

    grant = get_grant_proposal(pid)
    if grant is not None:
        utils.flash_message("The grant dossier already exists.")
        return flask.redirect(flask.url_for("grant.display", gid=grant["identifier"]))

    try:
        with GrantSaver(proposal=proposal) as saver:
            pass
        grant = saver.doc
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver["grant"] = grant["identifier"]
    except ValueError as error:
        utils.flash_error(error)
    return flask.redirect(flask.url_for("grant.display", gid=grant["identifier"]))


@blueprint.route("/<gid>")
@utils.login_required
def display(gid):
    "Display the grant dossier."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant dossier.")
    if not allow_view(grant):
        return utils.error("You are not allowed to view this grant dossier.")

    receiver_email = anubis.user.get_user(username=grant["user"])["email"]
    access_emails = []
    for username in grant.get("access_view", []):
        user = anubis.user.get_user(username=username)
        if user:
            access_emails.append(user["email"])
    # There may be accounts that have no email!
    access_emails = [e for e in access_emails if e]
    all_emails = [receiver_email] + access_emails
    email_lists = {
        "Grant receiver (= proposal submitter)": receiver_email,
        "Persons with access to this grant": ", ".join(access_emails),
        "All involved persons": ", ".join(all_emails),
    }
    return flask.render_template(
        "grant/display.html",
        grant=grant,
        proposal=anubis.proposal.get_proposal(grant["proposal"]),
        call=anubis.call.get_call(grant["call"]),
        call_grants_count=anubis.database.get_count("grants", "call", gid),
        email_lists=email_lists,
        allow_view=allow_view(grant),
        allow_edit=allow_edit(grant),
        allow_change_access=allow_change_access(grant),
        allow_lock=allow_lock(grant),
        allow_delete=allow_delete(grant),
    )


@blueprint.route("/<gid>/edit", methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(gid):
    "Edit the grant dossier."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant.")
    if not allow_edit(grant):
        return utils.error("You are not allowed to edit this grant dossier.")

    call = anubis.call.get_call(grant["call"])

    if utils.http_GET():
        return flask.render_template("grant/edit.html", grant=grant, call=call)

    elif utils.http_POST():
        try:
            with GrantSaver(doc=grant) as saver:
                saver.set_fields_values(call.get("grant", []), form=flask.request.form)
        except ValueError as error:
            return utils.error(error)
        if saver.repeat_changed:
            url = flask.url_for("grant.edit", gid=grant["identifier"])
        else:
            url = flask.url_for("grant.display", gid=grant["identifier"])
        return flask.redirect(url)

    elif utils.http_DELETE():
        if not allow_delete(grant):
            return utils.error("You are not allowed to delete this grant dossier.")
        proposal = anubis.proposal.get_proposal(grant["proposal"])
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver["grant"] = None
        anubis.database.delete(grant)
        utils.flash_message("Deleted grant dossier.")
        return flask.redirect(
            flask.url_for("proposal.display", pid=proposal["identifier"])
        )


@blueprint.route("/<gid>/access", methods=["GET", "POST", "DELETE"])
@utils.login_required
def change_access(gid):
    "Change the access rights for the grant record."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant.")
    if not allow_change_access(grant):
        return utils.error(
            "You are not allowed to change access for this grant dossier."
        )
    call = anubis.call.get_call(grant["call"])

    if utils.http_GET():
        users_edit = sorted(grant.get("access_edit", []))
        users_view = sorted(set(grant.get("access_view", [])).difference(users_edit))
        return flask.render_template(
            "change_access.html",
            title=f"Grant {grant['identifier']}",
            url=flask.url_for("grant.change_access", gid=grant["identifier"]),
            users_view=users_view,
            users_edit=users_edit,
            back_url=flask.url_for("grant.display", gid=grant["identifier"]),
        )

    elif utils.http_POST():
        try:
            with GrantSaver(doc=grant) as saver:
                saver.set_access(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("grant.change_access", gid=grant["identifier"]))

    elif utils.http_DELETE():
        try:
            with GrantSaver(doc=grant) as saver:
                saver.remove_access(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("grant.change_access", gid=grant["identifier"]))


@blueprint.route("/<gid>/lock", methods=["POST"])
@utils.login_required
def lock(gid):
    "Lock the grant dossier to stop edits by the user."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant.")
    if not allow_lock(grant):
        return utils.error("You are not allowed to lock this grant dossier.")

    if utils.http_POST():
        try:
            with GrantSaver(doc=grant) as saver:
                saver["locked"] = utils.get_now()
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("grant.display", gid=grant["identifier"]))


@blueprint.route("/<gid>/unlock", methods=["POST"])
@utils.login_required
def unlock(gid):
    "Unlock the grant dossier to allow edits by the user."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant.")
    if not allow_lock(grant):
        return utils.error("You are not allowed to unlock this grant dossier.")

    if utils.http_POST():
        try:
            with GrantSaver(doc=grant) as saver:
                saver["locked"] = False
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("grant.display", gid=grant["identifier"]))


@blueprint.route("/<gid>/document/<fid>")
@utils.login_required
def document(gid, fid):
    "Download the grant document (attachment file) for the given field id."
    try:
        grant = get_grant(gid)
    except KeyError:
        return utils.error("No such grant dossier.")
    if not allow_view(grant):
        return utils.error("You are not allowed to read this grant dossier.")

    try:
        documentname = grant["values"][fid]
        stub = grant["_attachments"][documentname]
    except KeyError:
        return utils.error(
            "No such document in grant dossier.",
            flask.url_for("grant.display", gid=gid),
        )

    # Colon ':' is a problematic character in filenames; replace by dash '-'.
    gid = gid.replace(":", "-")
    ext = os.path.splitext(documentname)[1]
    # Add the appropriate file extension to the filename.
    filename = f"{gid}-{fid}{ext}"
    outfile = flask.g.db.get_attachment(grant, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set("Content-Type", stub["content_type"])
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response


@blueprint.route("/<gid>.zip")
@utils.login_required
def grant_zip(gid):
    "Return a zip file containing all documents in the grant dossier."
    try:
        grant = get_grant(gid)
    except KeyError:
        return utils.error("No such grant dossier.")
    if not allow_view(grant):
        return utils.error("You are not allowed to read this grant dossier.")

    # Colon ':' is a problematic character in filenames; replace by dash '_'
    gid = gid.replace(":", "-")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as outfile:
        for document in get_grant_documents(grant):
            outfile.writestr(document["filename"], document["content"])
    response = flask.make_response(output.getvalue())
    response.headers.set("Content-Type", constants.ZIP_MIMETYPE)
    response.headers.set("Content-Disposition", "attachment", filename=f"{gid}.zip")
    return response


def get_grant_documents(grant):
    "Get all documents in a grant as a list of dict(filename, content)."
    result = []
    call = anubis.call.get_call(grant["call"])
    # Colon ':' is a problematic character in filenames; replace by dash '_'
    gid = grant["identifier"].replace(":", "-")
    # First non-repeated document fields.
    for field in call["grant"]:
        if field.get("repeat"):
            continue
        if field["type"] != constants.DOCUMENT:
            continue
        try:
            documentname = grant["values"][field["identifier"]]
        except KeyError:
            continue
        stub = grant["_attachments"][documentname]
        ext = os.path.splitext(documentname)[1]
        filename = f"{gid}-{field['identifier']}{ext}"
        outfile = flask.g.db.get_attachment(grant, documentname)
        result.append(dict(filename=filename, content=outfile.read()))
    # Then repeated document fields.
    for field in call["grant"]:
        if field["type"] != constants.REPEAT:
            continue
        n_fields = grant["values"].get(field["identifier"]) or 0
        for n in range(1, n_fields + 1):
            for field2 in call["grant"]:
                if field2.get("repeat") != field["identifier"]:
                    continue
                if field2["type"] != constants.DOCUMENT:
                    continue
                field2name = f"{field2['identifier']}-{n}"
                try:
                    documentname = grant["values"][field2name]
                    stub = grant["_attachments"][documentname]
                except KeyError:
                    continue
                outfile = flask.g.db.get_attachment(grant, documentname)
                ext = os.path.splitext(documentname)[1]
                filename = f"{gid}-{field2['identifier']}-{n}{ext}"
                result.append(dict(filename=filename, content=outfile.read()))
    return result


@blueprint.route("/<gid>/logs")
@utils.login_required
def logs(gid):
    "Display the log records of the given grant dossier."
    grant = get_grant(gid)
    if grant is None:
        return utils.error("No such grant dossier.")
    if not allow_view(grant):
        return utils.error("You are not allowed to read this grant dossier.")

    return flask.render_template(
        "logs.html",
        title=f"Grant {grant['identifier']}",
        back_url=flask.url_for("grant.display", gid=grant["identifier"]),
        logs=anubis.database.get_logs(grant["_id"]),
    )


class GrantSaver(AccessSaverMixin, FieldSaverMixin, Saver):
    "Grant dossier document saver context."

    DOCTYPE = constants.GRANT

    def __init__(self, doc=None, proposal=None):
        if doc:
            super().__init__(doc=doc)
        elif proposal:
            super().__init__(doc=None)
            self.set_proposal(proposal)
            self["user"] = proposal["user"]
        else:
            raise ValueError("doc or proposal must be specified")

    def initialize(self):
        self.doc["values"] = {}
        self.doc["errors"] = {}
        self.doc["access_view"] = []
        self.doc["access_edit"] = []

    def set_proposal(self, proposal):
        "Set the proposal for the grant dossier; must be called when creating."
        if self.doc.get("proposal"):
            raise ValueError("proposal has already been set")
        self.doc["proposal"] = proposal["identifier"]
        self.doc["call"] = proposal["call"]
        self.doc["identifier"] = "{}:G:{}".format(*proposal["identifier"].split(":"))
        call = anubis.call.get_call(proposal["call"])
        self.set_fields_values(call.get("grant", []))


def get_grant(gid):
    """Return the grant dossier with the given identifier.
    Return None if not found.
    """
    key = f"grant {gid}"
    try:
        return utils.cache_get(key)
    except KeyError:
        docs = [
            r.doc
            for r in flask.g.db.view("grants", "identifier", key=gid, include_docs=True)
        ]
        if len(docs) == 1:
            grant = docs[0]
            return utils.cache_put(
                f"grant {grant['proposal']}", utils.cache_put(key, grant)
            )
        else:
            return None


def get_grant_proposal(pid):
    """Return the grant dossier for the proposal with the given identifier.
    Return None if not found.
    """
    key = f"grant {pid}"
    try:
        return utils.cache_get(key)
    except KeyError:
        docs = [
            r.doc
            for r in flask.g.db.view("grants", "proposal", key=pid, include_docs=True)
        ]
        if len(docs) == 1:
            grant = docs[0]
            return utils.cache_put(
                f"grant {grant['identifier']}", utils.cache_put(key, grant)
            )
        else:
            return None


def allow_create(proposal):
    "The admin and staff may create a grant dossier."
    if not flask.g.current_user:
        return False
    if not proposal.get("decision"):
        return False
    decision = anubis.decision.get_decision(proposal["decision"])
    if not decision.get("finalized"):
        return False
    if not decision.get("verdict"):
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    return False


def allow_view(grant):
    """The admin, staff and proposal user (= grant receiver) may view the grant dossier.
    An account with view access to the call may also view the grant.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if flask.g.current_user["username"] == grant["user"]:
        return True
    if flask.g.current_user["username"] in grant.get("access_view", []):
        return True
    call = anubis.call.get_call(grant["call"])
    if anubis.call.allow_view(call):
        return True
    return False


def allow_edit(grant):
    """The admin, staff and proposal user (= grant receiver) and accounts
    with edit access may edit the grant dossier.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if grant.get("locked"):
        return False
    if flask.g.current_user["username"] == grant["user"]:
        return True
    if flask.g.current_user["username"] in grant.get("access_edit", []):
        return True
    return False


def allow_change_access(grant):
    """The admin, staff and proposal user (= grant receiver) and accounts
    with edit access may change access for the grant dossier.
    Lock status does not affect this.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if flask.g.current_user["username"] == grant["user"]:
        return True
    if flask.g.current_user["username"] in grant.get("access_edit", []):
        return True
    return False


def allow_lock(grant):
    "The admin and staff can lock/unlock the grant whenever."
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    return False


def allow_link(grant):
    """Admin and staff may view link to any grant dossier.
    User may link to her own grant dossier.
    """
    if not grant:
        return False
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if flask.g.current_user["username"] == grant["user"]:
        return True
    return False


def allow_delete(grant):
    "Only the admin may delete a grant dossier."
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    return False
