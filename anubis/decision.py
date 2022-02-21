"""Decision create, display end edit.

A decision represents the result of the review and decision
process. It is intended to be shown to the proposer, but this is not
done until the switch for this is set for the call.

There are no decision lists; the decisions are shown in the proposals lists.

A decision is defined by the decision fields in the call.
"""

import os.path

import flask

import anubis.call
import anubis.proposal
from anubis import constants
from anubis import utils
from anubis.saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design("decisions", DESIGN_DOC):
        app.logger.info("Updated decisions design document.")


DESIGN_DOC = {
    "views": {
        # Decisions for all proposals in call.
        "call": {
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.call, doc.proposal);}",
        },
        # Decision for a proposal.
        "proposal": {
            "map": "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.proposal, null);}"
        },
    }
}

blueprint = flask.Blueprint("decision", __name__)


@blueprint.route("/create/<pid>", methods=["POST"])
@utils.login_required
def create(pid):
    "Create a decision for the proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error("No such proposal.", flask.url_for("home"))
    try:
        if not allow_create(proposal):
            raise ValueError("You may not create a decision for the proposal.")
        decision = get_decision(proposal.get("decision"))
        if decision is not None:
            utils.flash_message("The decision already exists.")
            return flask.redirect(flask.url_for(".display", iuid=decision["_id"]))
        with DecisionSaver(proposal=proposal) as saver:
            pass
        decision = saver.doc
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver["decision"] = decision["_id"]
    except ValueError as error:
        utils.flash_error(error)
    return flask.redirect(flask.url_for(".display", iuid=decision["_id"]))


@blueprint.route("/<iuid:iuid>")
def display(iuid):
    "Display the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))
    proposal = anubis.proposal.get_proposal(decision["proposal"])
    call = anubis.call.get_call(decision["call"])

    if not allow_link(decision):
        return utils.error(
            "You are not allowed to view this decision.",
            flask.url_for("proposal.display", pid=decision["proposal"]),
        )
    return flask.render_template(
        "decision/display.html",
        decision=decision,
        proposal=proposal,
        call=call,
        allow_edit=allow_edit(decision),
        allow_delete=allow_delete(decision),
        allow_finalize=allow_finalize(decision),
        allow_unfinalize=allow_unfinalize(decision),
    )


@blueprint.route("/<iuid:iuid>/edit", methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(iuid):
    "Edit the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))
    proposal = anubis.proposal.get_proposal(decision["proposal"])
    call = anubis.call.get_call(decision["call"])

    if utils.http_GET():
        if not allow_edit(decision):
            return utils.error("You are not allowed to edit this decision.")
        return flask.render_template(
            "decision/edit.html", decision=decision, proposal=proposal, call=call
        )

    elif utils.http_POST():
        if not allow_edit(decision):
            return utils.error("You are not allowed to edit this decision.")
        try:
            # NOTE: Repeat field has not been implemented for decision.
            with DecisionSaver(doc=decision) as saver:
                saver.set_verdict(form=flask.request.form)
                saver.set_fields_values(call["decision"], form=flask.request.form)
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(flask.url_for(".display", iuid=decision["_id"]))

    elif utils.http_DELETE():
        if not allow_delete(decision):
            return utils.error("You are not allowed to delete this decision.")
        with anubis.proposal.ProposalSaver(proposal) as saver:
            saver["decision"] = None
        utils.delete(decision)
        utils.flash_message("Deleted decision.")
        return flask.redirect(
            flask.url_for("proposal.display", pid=proposal["identifier"])
        )


@blueprint.route("/<iuid:iuid>/finalize", methods=["POST"])
@utils.login_required
def finalize(iuid):
    "Finalize the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))
    if not allow_finalize(decision):
        return utils.error("You are not allowed to finalize this decision.")

    if utils.http_POST():
        try:
            with DecisionSaver(doc=decision) as saver:
                saver["finalized"] = utils.get_time()
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for(".display", iuid=decision["_id"]))


@blueprint.route("/<iuid:iuid>/unfinalize", methods=["POST"])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))
    if not allow_unfinalize(decision):
        return utils.error("You are not allowed to unfinalize this decision.")

    if utils.http_POST():
        try:
            with DecisionSaver(doc=decision) as saver:
                saver["finalized"] = None
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for(".display", iuid=decision["_id"]))


@blueprint.route("/<iuid:iuid>/logs")
@utils.login_required
def logs(iuid):
    "Display the log records of the decision."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))

    return flask.render_template(
        "logs.html",
        title=f"Decision for {decision['proposal']}",
        back_url=flask.url_for(".display", iuid=decision["_id"]),
        logs=utils.get_logs(decision["_id"]),
    )


@blueprint.route("/<iuid:iuid>/document/<fid>")
@utils.login_required
def document(iuid, fid):
    "Download the decision document (attachment file) for the given field id."
    try:
        decision = get_decision(iuid)
    except KeyError:
        return utils.error("No such decision.", flask.url_for("home"))
    if not allow_link(decision):
        return utils.error(
            "You are not allowed to read this decision.", flask.url_for("home")
        )

    try:
        documentname = decision["values"][fid]
        stub = decision["_attachments"][documentname]
    except KeyError:
        return utils.error("No such document in decision.")
    # Colon ':' is a problematic character in filenames.
    # Replace it by dash '-'; used as general glue character here.
    pid = decision["proposal"].replace(":", "-")
    ext = os.path.splitext(documentname)[1]
    # Include 'decision' in filename to indicate decision document.
    filename = f"{pid}-decision-{fid}{ext}"
    outfile = flask.g.db.get_attachment(decision, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set("Content-Type", stub["content_type"])
    response.headers.set("Content-Disposition", "attachment", filename=filename)
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
            raise ValueError("doc or proposal must be specified")

    def initialize(self):
        self.doc["verdict"] = None
        self.doc["values"] = {}
        self.doc["errors"] = {}

    def set_proposal(self, proposal):
        "Set the proposal for the decision; must be called when creating."
        if self.doc.get("call"):
            raise ValueError("call has already been set")
        self.doc["proposal"] = proposal["identifier"]
        call = anubis.call.get_call(proposal["call"])
        self.doc["call"] = call["identifier"]
        self.set_fields_values(call["decision"])

    def set_verdict(self, form=dict()):
        "Set the value of verdict."
        value = form.get("_verdict") or None
        if value:
            value = utils.to_bool(value)
        self.doc["verdict"] = value


def get_decision(iuid):
    """Get the decision by its iuid.
    Return None if not found.
    Raise ValueError if the iuid is for a document of another type.
    """
    if not iuid:
        return None
    key = f"decision {iuid}"
    try:
        return flask.g.cache[key]
    except KeyError:
        try:
            decision = flask.g.db[iuid]
        except KeyError:
            return None
        if decision["doctype"] != constants.DECISION:
            raise ValueError
        flask.g.cache[key] = decision
        return decision


def allow_create(proposal):
    "Admin and chair may create a decision for a submitted proposal."
    if not flask.g.current_user:
        return False
    if not proposal.get("submitted"):
        return False
    if proposal.get("decision"):
        return False
    if flask.g.am_admin:
        return True
    call = anubis.call.get_call(proposal["call"])
    if anubis.call.am_owner(call):
        return True
    if anubis.call.am_chair(call):
        return True
    return False


def allow_view(decision):
    """Submitter may view decision for her proposal
    once it has been finalized and the call-wide flag set.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    call = anubis.call.get_call(decision["call"])
    if anubis.call.am_owner(call):
        return True
    if not call["access"]["allow_submitter_view_decision"]:
        return False
    proposal = anubis.proposal.get_proposal(decision["proposal"])
    if proposal["user"] != flask.g.current_user["username"]:
        return False
    if decision.get("finalized"):
        return True
    return False


def allow_link(decision):
    """Admin may view link to any decision.
    Reviewer may view link to any decision in a call.
    """
    if not decision:
        return False
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    call = anubis.call.get_call(decision["call"])
    if anubis.call.am_owner(call):
        return True
    if anubis.call.am_reviewer(call):
        return True
    return False


def allow_edit(decision):
    "Admin and chair may edit an unfinalized decision."
    if not flask.g.current_user:
        return False
    if decision.get("finalized"):
        return False
    if flask.g.am_admin:
        return True
    call = anubis.call.get_call(decision["call"])
    if anubis.call.am_owner(call):
        return True
    if anubis.call.am_chair(call):
        return True
    return False


def allow_delete(decision):
    "Admin may delete an unfinalized decision."
    if decision.get("finalized"):
        return False
    return flask.g.am_admin


def allow_finalize(decision):
    "Admin and chair may finalize if the decision contains no errors."
    if not flask.g.current_user:
        return False
    if decision.get("finalized"):
        return False
    if decision.get("errors"):
        return False
    if decision.get("verdict") is None:
        return False
    if flask.g.am_admin:
        return True
    call = anubis.call.get_call(decision["call"])
    if anubis.call.am_owner(call):
        return True
    if anubis.call.am_chair(call):
        return True
    return False


def allow_unfinalize(decision):
    "Admin and chair may unfinalize the decision."
    if not flask.g.current_user:
        return False
    if not decision.get("finalized"):
        return False
    if flask.g.am_admin:
        return True
    call = anubis.call.get_call(decision["call"])
    if anubis.call.am_owner(call):
        return True
    if anubis.call.am_chair(call):
        return True
    return False
