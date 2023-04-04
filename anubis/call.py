"""Call creation, display, edit; field definitions.

A call is a container of proposals. It is the fundamental entity which
all other entities (except user account) depend on. It contains all
field definitions for the other entities: proposal, review, decision
and grant.

The different sets of fields of a call may be changed at any time.
But beware: if e.g. changing a proposal field from optional to
required may inadvertenly invalidate some proposals (but not break the
system itself).  Change an open call with care.
"""

import copy
import io
import zipfile

import flask

import anubis.database
import anubis.proposal
import anubis.proposals
import anubis.user
from anubis import constants
from anubis import utils
from anubis.saver import Saver, AccessSaverMixin


blueprint = flask.Blueprint("call", __name__)


@blueprint.route("/", methods=["GET", "POST"])
@utils.login_required
def create():
    "Create a new call from scratch."
    if not allow_create():
        return utils.error("You are not allowed to create a call.")

    if utils.http_GET():
        return flask.render_template("call/create.html")

    elif utils.http_POST():
        try:
            with CallSaver() as saver:
                saver.set_identifier(flask.request.form.get("identifier"))
                saver.set_title(flask.request.form.get("title"))
                saver.add_review_field(
                    {
                        "type": constants.BOOLEAN,
                        "identifier": "conflict_of_interest",
                        "description": "Do you have a conflict of interest regarding the proposal? If yes, then you should state so here, and finalize the review without filling in any other fields.",
                        "required": True,
                    }
                )
            call = saver.doc
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(flask.url_for("call.edit", cid=call["identifier"]))


@blueprint.route("/<cid>")
def display(cid):
    "Display the call."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_view(call):
        return utils.error("You are not allowed to view the call.")

    kwargs = dict(
        am_owner=am_owner(call),
        am_reviewer=am_reviewer(call),
        allow_edit=allow_edit(call),
        allow_delete=allow_delete(call),
        allow_change_access=allow_change_access(call),
        allow_create_proposal=anubis.proposal.allow_create(call),
        allow_view_details=allow_view_details(call),
        allow_view_proposals=allow_view_proposals(call),
        allow_view_reviews=allow_view_reviews(call),
        allow_view_grants=allow_view_grants(call),
        is_undefined=is_undefined(call),
        is_open=is_open(call),
        is_closed=is_closed(call),
    )
    if allow_view_details(call):
        reviewers = [anubis.user.get_user(r) for r in call["reviewers"]]
        reviewer_emails = [r["email"] for r in reviewers if r["email"]]
        access_emails = []
        for username in [call["owner"]] + call.get("access_view", []):
            user = anubis.user.get_user(username=username)
            if user:
                access_emails.append(user["email"])
        # There may be accounts that have no email!
        access_emails = [e for e in access_emails if e]
        all_emails = reviewer_emails + access_emails
        email_lists = {
            "Persons with access to this call": ", ".join(access_emails),
            "Emails for reviewers": ", ".join(reviewer_emails),
            "All involved persons": ", ".join(all_emails),
        }
        kwargs["email_lists"] = email_lists
    if flask.g.current_user:
        kwargs["my_proposal"] = anubis.proposal.get_call_user_proposal(
            cid, flask.g.current_user["username"]
        )
        kwargs["my_reviews_count"] = anubis.database.get_count(
            "reviews", "call_reviewer", [cid, flask.g.current_user["username"]]
        )
        kwargs["my_archived_reviews_count"] = anubis.database.get_count(
            "reviews", "call_reviewer_archived", [cid, flask.g.current_user["username"]]
        )
    kwargs["call_proposals_count"] = anubis.database.get_count("proposals", "call", cid)
    # Number of archived reviews for the call.
    result = flask.g.db.view(
        "reviews",
        "call_reviewer_archived",
        startkey=[call["identifier"], ""],
        endkey=[call["identifier"], "ZZZZZZ"],
        reduce=True,
    )
    kwargs["archived_reviews_count"] = result and result[0].value or 0
    return flask.render_template("call/display.html", call=call, **kwargs)


@blueprint.route("/<cid>/edit", methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(cid):
    "Edit the call, or delete it."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        return flask.render_template(
            "call/edit.html",
            call=call,
            allow_identifier_edit=allow_identifier_edit(call),
            is_open=is_open(call),
            is_closed=is_closed(call),
        )

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.set_identifier(flask.request.form.get("identifier"))
                saver.set_title(flask.request.form.get("title"))
                saver["description"] = flask.request.form.get("description")
                saver["home_description"] = (
                    flask.request.form.get("home_description").strip() or None
                )
                for key in ["opens", "closes", "reviews_due"]:
                    value = flask.request.form.get(key).strip() or None
                    if value:
                        value = utils.utc_from_timezone_isoformat(value)
                    saver[key] = value
                saver.edit_privileges(flask.request.form)
            call = saver.doc
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.display", cid=call["identifier"]))

    elif utils.http_DELETE():
        if not allow_delete(call):
            return utils.error("You are not allowed to delete the call.")
        anubis.database.delete(call)
        utils.flash_message(f"Deleted call {call['identifier']}:{call['title']}.")
        return flask.redirect(
            flask.url_for("calls.owner", username=flask.g.current_user["username"])
        )


@blueprint.route("/<cid>/access", methods=["GET", "POST", "DELETE"])
@utils.login_required
def change_access(cid):
    "Change the view & edit access rights for the call."
    call = get_call(cid)
    if call is None:
        return utils.error("No such call.")
    if not allow_change_access(call):
        return utils.error("You are not allowed to change access for this call.")

    if utils.http_GET():
        users_edit = sorted(call.get("access_edit", []))
        users_view = sorted(set(call.get("access_view", [])).difference(users_edit))
        return flask.render_template(
            "change_access.html",
            title=f"Call {call['identifier']}",
            url=flask.url_for("call.change_access", cid=call["identifier"]),
            users_view=users_view,
            users_edit=users_edit,
            back_url=flask.url_for("call.display", cid=call["identifier"]),
        )

    elif utils.http_POST():
        try:
            with CallSaver(doc=call) as saver:
                saver.set_access(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(
            flask.url_for("call.change_access", cid=call["identifier"])
        )

    elif utils.http_DELETE():
        try:
            with CallSaver(doc=call) as saver:
                saver.remove_access(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(
            flask.url_for("call.change_access", cid=call["identifier"])
        )


@blueprint.route("/<cid>/documents", methods=["GET", "POST"])
@utils.login_required
def documents(cid):
    "Display documents for delete, or add document (attachment file)."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        return flask.render_template(
            "call/documents.html",
            call=call,
            is_open=is_open(call),
            is_closed=is_closed(call),
        )

    elif utils.http_POST():
        infile = flask.request.files.get("document")
        if infile:
            description = flask.request.form.get("document_description")
            with CallSaver(call) as saver:
                saver.add_document(infile, description)
        else:
            utils.flash_error("No document selected.")
        return flask.redirect(flask.url_for("call.documents", cid=call["identifier"]))


@blueprint.route("/<cid>/documents/<documentname>", methods=["GET", "POST", "DELETE"])
def document(cid, documentname):
    "Download the given document (attachment file), or delete it."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_view(call):
        return utils.error("You may not view the call.")

    if utils.http_GET():
        try:
            stub = call["_attachments"][documentname]
        except KeyError:
            return utils.error("No such document in call.")
        outfile = flask.g.db.get_attachment(call, documentname)
        response = flask.make_response(outfile.read())
        response.headers.set("Content-Type", stub["content_type"])
        response.headers.set("Content-Disposition", "attachment", filename=documentname)
        return response

    elif utils.http_DELETE():
        if not allow_edit(call):
            return utils.error("You are not allowed to edit the call.")
        with CallSaver(call) as saver:
            saver.delete_document(documentname)
        return flask.redirect(flask.url_for("call.documents", cid=call["identifier"]))


@blueprint.route("/<cid>/proposal", methods=["GET", "POST"])
@utils.login_required
def proposal(cid):
    "Display proposal field definitions for edit, delete, or add field."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        return flask.render_template(
            "call/proposal.html",
            call=call,
            is_open=is_open(call),
            is_closed=is_closed(call),
        )

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_proposal_field(flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.proposal", cid=call["identifier"]))


@blueprint.route("/<cid>/proposal/<fid>", methods=["POST", "DELETE"])
@utils.login_required
def proposal_field(cid, fid):
    "Edit or delete the proposal field definition."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_proposal_field(fid, flask.request.form)
        except (KeyError, ValueError) as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.proposal", cid=call["identifier"]))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_proposal_field(fid)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.proposal", cid=call["identifier"]))


@blueprint.route("/<cid>/reviewers", methods=["GET", "POST", "DELETE"])
@utils.login_required
def reviewers(cid):
    "Edit the list of reviewers."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")

    if utils.http_GET():
        if not allow_view_details(call):
            return utils.error("You are not allowed to view the reviewers the call.")

        reviewers = [anubis.user.get_user(r) for r in call["reviewers"]]
        call["n_reviews"] = dict()
        for reviewer in reviewers:
            count = anubis.database.get_count(
                "reviews", "call_reviewer", [cid, reviewer["username"]]
            )
            call["n_reviews"][reviewer["username"]] = count
            reviewer["n_reviews"] = count
        reviewer_emails = [r["email"] for r in reviewers if r["email"]]
        email_lists = {"Emails for reviewers": ", ".join(reviewer_emails)}
        return flask.render_template(
            "call/reviewers.html",
            call=call,
            reviewers=reviewers,
            email_lists=email_lists,
            allow_edit=allow_edit(call),
            allow_view_reviews=allow_view_reviews(call),
        )

    elif utils.http_POST():
        if not allow_edit(call):
            return utils.error("You are not allowed to edit the call.")

        reviewer = flask.request.form.get("reviewer")
        if not reviewer:
            return flask.redirect(flask.url_for("call.display", cid=cid))
        user = anubis.user.get_user(username=reviewer)
        if user is None:
            user = anubis.user.get_user(email=reviewer)
        if user is None:
            return utils.error(
                f"No such user '{reviewer}'.", flask.url_for("call.reviewers", cid=cid)
            )
        if anubis.proposal.get_call_user_proposal(cid, user["username"]):
            utils.flash_warning(
                "The user has a proposal in the call. Allowing her to be a reviewer is questionable."
            )
        with CallSaver(call) as saver:
            try:
                saver["reviewers"].remove(user["username"])
            except ValueError:
                pass
            try:
                saver["chairs"].remove(user["username"])
            except ValueError:
                pass
            saver["reviewers"].append(user["username"])
            if utils.to_bool(flask.request.form.get("chair")):
                saver["chairs"].append(user["username"])
        return flask.redirect(flask.url_for("call.reviewers", cid=call["identifier"]))

    elif utils.http_DELETE():
        if not allow_edit(call):
            return utils.error("You are not allowed to edit the call.")

        reviewer = flask.request.form.get("reviewer")
        if anubis.database.get_count(
            "reviews", "call_reviewer", [call["identifier"], reviewer]
        ):
            return utils.error(
                "Cannot remove reviewer which has reviews in the call.",
                flask.url_for("call.reviewers", cid=cid),
            )
        with CallSaver(call) as saver:
            try:
                saver["reviewers"].remove(reviewer)
            except ValueError:
                pass
            try:
                saver["chairs"].remove(reviewer)
            except ValueError:
                pass
        return flask.redirect(flask.url_for("call.reviewers", cid=call["identifier"]))


@blueprint.route("/<cid>/review", methods=["GET", "POST"])
@utils.login_required
def review(cid):
    "Display review field definitions for delete, and add field."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        return flask.render_template(
            "call/review.html", call=call, is_closed=is_closed(call)
        )

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_review_field(flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.review", cid=call["identifier"]))


@blueprint.route("/<cid>/review/<fid>", methods=["POST", "DELETE"])
@utils.login_required
def review_field(cid, fid):
    "Edit or delete the review field definition."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_review_field(fid, flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.review", cid=call["identifier"]))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_review_field(fid)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.review", cid=call["identifier"]))


@blueprint.route("/<cid>/decision", methods=["GET", "POST"])
@utils.login_required
def decision(cid):
    "Display decision field definitions for delete, and add field."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        return flask.render_template("call/decision.html", call=call)

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_decision_field(flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.decision", cid=call["identifier"]))


@blueprint.route("/<cid>/decision/<fid>", methods=["POST", "DELETE"])
@utils.login_required
def decision_field(cid, fid):
    "Edit or delete the decision field definition."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_decision_field(fid, flask.request.form)
        except (KeyError, ValueError) as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.decision", cid=call["identifier"]))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_decision_field(fid)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.decision", cid=call["identifier"]))


@blueprint.route("/<cid>/grant", methods=["GET", "POST"])
@utils.login_required
def grant(cid):
    "Display grant field definitions for delete, and add field."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_GET():
        repeat_fields = [
            f for f in call.get("grant", []) if f["type"] == constants.REPEAT
        ]
        return flask.render_template(
            "call/grant.html",
            call=call,
            repeat_fields=repeat_fields,
            reviews_count=anubis.database.get_count(
                "reviews", "call", call["identifier"]
            ),
        )

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_grant_field(flask.request.form)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.grant", cid=call["identifier"]))


@blueprint.route("/<cid>/grant/<fid>", methods=["POST", "DELETE"])
@utils.login_required
def grant_field(cid, fid):
    "Edit or delete the grant field definition."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_grant_field(fid, flask.request.form)
        except (KeyError, ValueError) as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.grant", cid=call["identifier"]))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_grant_field(fid)
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for("call.grant", cid=call["identifier"]))


@blueprint.route("/<cid>/reset_counter", methods=["POST"])
@utils.login_required
def reset_counter(cid):
    "Reset the counter of the call. Only if no proposals in it."
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not allow_edit(call):
        return utils.error("You are not allowed to edit the call.")
    if anubis.database.get_count("proposals", "call", cid) != 0:
        return utils.error(
            "Cannot reset counter when there are proposals in the call.",
            flask.url_for("call.display", cid=cid),
        )

    with CallSaver(call) as saver:
        saver["counter"] = None
    utils.flash_message("Counter for proposals in call reset.")
    return flask.redirect(flask.url_for("call.display", cid=call["identifier"]))


@blueprint.route("/<cid>/clone", methods=["GET", "POST"])
@utils.login_required
def clone(cid):
    """Clone the call. Copies:
    - Title
    - Description
    - Privileges fields
    - Proposal fields
    - Review fields
    - Decision fields
    - Grant fields
    Does not copy:
    - Dates
    - Documents
    - Reviewers
    """
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")

    if not allow_create():
        return utils.error("You are not allowed to create a call.")

    if utils.http_GET():
        return flask.render_template("call/clone.html", call=call)

    elif utils.http_POST():
        try:
            with CallSaver() as saver:
                saver.set_identifier(flask.request.form.get("identifier"))
                saver.set_title(flask.request.form.get("title"))
                saver.doc["description"] = call["description"]
                saver.doc["privileges"] = call["privileges"]
                saver.doc["proposal"] = copy.deepcopy(call["proposal"])
                saver.doc["review"] = copy.deepcopy(call["review"])
                saver.doc["decision"] = copy.deepcopy(call.get("decision", []))
                saver.doc["grant"] = copy.deepcopy(call.get("grant", []))
                # Do not copy dates.
                # Do not copy documents.
                # Do not copy reviewers or chairs.
            new = saver.doc
        except ValueError as error:
            return utils.error(error)
        return flask.redirect(flask.url_for("call.edit", cid=new["identifier"]))


@blueprint.route("/<cid>/logs")
@utils.login_required
def logs(cid):
    "Display the log records of the call."
    call = get_call(cid)
    if call is None:
        return utils.error("No such call.")

    if not allow_edit(call):
        return utils.error("You are not allowed to view the logs of the call.")

    return flask.render_template(
        "logs.html",
        title=f"Call {call['identifier']}",
        back_url=flask.url_for("call.display", cid=call["identifier"]),
        logs=anubis.database.get_logs(call["_id"]),
    )


@blueprint.route("/<cid>/create_proposal", methods=["POST"])
@utils.login_required
def create_proposal(cid):
    "Create a new proposal within the call. Redirect to an existing proposal."
    call = get_call(cid)
    if call is None:
        return utils.error("No such call.")
    if not anubis.proposal.allow_create(call):
        return utils.error("You may not create a proposal in the call.")

    if utils.http_POST():
        proposal = anubis.proposal.get_call_user_proposal(
            cid, flask.g.current_user["username"]
        )
        if proposal:
            return utils.message(
                "Proposal already exists for the call.",
                flask.url_for("proposal.display", pid=proposal["identifier"]),
            )
        else:
            with anubis.proposal.ProposalSaver(
                call=call, user=flask.g.current_user
            ) as saver:
                pass
            return flask.redirect(
                flask.url_for("proposal.edit", pid=saver.doc["identifier"])
            )


@blueprint.route("/<cid>.zip")
def call_zip(cid):
    """Download a zip file containing the XLSX for all submitted proposals,
    the DOCX for each proposal, and all documents attached to those proposals.
    """
    call = get_call(cid)
    if not call:
        return utils.error("No such call.")
    if not (allow_view_details(call) or allow_view_grants(call)):
        return utils.error("You are not allowed to view the call proposals.")

    proposals = anubis.proposals.get_call_proposals(call, submitted=True)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zip:
        zip.writestr(
            f"{call['identifier']}_proposals.xlsx",
            anubis.proposals.get_call_xlsx(call, submitted=True),
        )
        for proposal in proposals:
            content = anubis.proposal.get_proposal_docx(proposal)
            filename = f"{proposal['identifier'].replace(':','-')}.docx"
            zip.writestr(filename, content.getvalue())
            for field in call["proposal"]:
                if field["type"] == constants.DOCUMENT:
                    try:
                        doc = anubis.proposal.get_document(
                            proposal, field["identifier"]
                        )
                    except KeyError:
                        pass
                    else:
                        zip.writestr(doc["filename"], doc["content"])
    response = flask.make_response(output.getvalue())
    response.headers.set("Content-Type", constants.ZIP_MIMETYPE)
    response.headers.set(
        "Content-Disposition", "attachment", filename=f"{call['identifier']}.zip"
    )
    return response


class CallSaver(AccessSaverMixin, Saver):
    "Call document saver context handler."

    DOCTYPE = constants.CALL

    def initialize(self):
        self.doc["owner"] = flask.g.current_user["username"]
        self.doc["opens"] = None
        self.doc["closes"] = None
        self.doc["proposal"] = []
        self.doc["documents"] = []
        self.doc["review"] = []
        self.doc["reviewers"] = []
        self.doc["chairs"] = []
        self.doc["privileges"] = {k: False for k in constants.PRIVILEGES}
        self.doc["decision"] = []
        self.doc["grant"] = []
        self.doc["access_view"] = []
        self.doc["access_edit"] = []

    def set_identifier(self, identifier):
        "Call identifier."
        if identifier == self.doc.get("identifier"):
            return
        if not allow_identifier_edit(self.doc):
            raise ValueError("Identifier for this call may not be changed.")
        if not identifier:
            raise ValueError("Identifier must be provided.")
        if not constants.ID_RX.match(identifier):
            raise ValueError("Invalid identifier.")
        if get_call(identifier):
            raise ValueError("Identifier is already in use.")
        self.doc["identifier"] = identifier

    def set_title(self, title):
        "Call title: non-blank required."
        title = title.strip()
        if not title:
            raise ValueError("Title must be provided.")
        self.doc["title"] = title

    def add_field(self, form):
        "Get the field definition from the form."
        fid = form.get("identifier")
        if not (fid and constants.ID_RX.match(fid)):
            raise ValueError("Invalid field identifier.")
        field = {"type": form.get("type"), "identifier": fid}
        self.edit_field_definition(field, form)
        return field

    def edit_field(self, fieldlist, fid, form):
        "Edit or move the field definition using data in the form."
        for pos, field in enumerate(fieldlist):
            if field["identifier"] == fid:
                break
        else:
            raise KeyError("No such field.")
        move = form.get("_move")
        if move == "up":
            fieldlist.pop(pos)
            if pos == 0:
                fieldlist.append(field)
            else:
                fieldlist.insert(pos - 1, field)
        else:
            self.edit_field_definition(field, form)

    def edit_field_definition(self, field, form):
        "Edit the field definition with values from the form."
        title = form.get("title")
        if not title:
            title = " ".join(
                [w.capitalize() for w in field["identifier"].replace("_", " ").split()]
            )
        field["title"] = title
        field["description"] = form.get("description") or None
        field["staff"] = bool(form.get("staff"))
        field["staffonly"] = bool(form.get("staffonly"))
        # A staffonly field must not be required. An incompleteness error
        # due to such a field would be incomprehensible for the user.
        if field["staffonly"]:
            field["required"] = False
        else:
            field["required"] = bool(form.get("required"))
        field["banner"] = bool(form.get("banner"))
        field["repeat"] = form.get("repeat") or None

        if field["type"] in (constants.LINE, constants.TEXT):
            try:
                maxlength = int(form.get("maxlength"))
                if maxlength <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                maxlength = None
            field["maxlength"] = maxlength

        elif field["type"] == constants.SELECT:
            field["menu"] = bool(form.get("menu"))
            field["multiple"] = bool(form.get("multiple"))
            selection = [s.strip() for s in form.get("selection", "").split("\n")]
            field["selection"] = [s for s in selection if s]

        elif field["type"] == constants.INTEGER:
            try:
                minimum = int(form.get("minimum"))
            except (TypeError, ValueError):
                minimum = None
            field["minimum"] = minimum
            try:
                maximum = int(form.get("maximum"))
            except (TypeError, ValueError):
                maximum = None
            if minimum is not None and maximum is not None and maximum <= minimum:
                raise ValueError("Invalid min/max: no value would be valid.")
            field["maximum"] = maximum

        elif field["type"] == constants.FLOAT:
            try:
                minimum = float(form.get("minimum"))
            except (TypeError, ValueError):
                minimum = None
            field["minimum"] = minimum
            try:
                maximum = float(form.get("maximum"))
            except (TypeError, ValueError):
                maximum = None
            if minimum is not None and maximum is not None and maximum <= minimum:
                raise ValueError("Invalid min/max: no value would be valid.")
            field["maximum"] = maximum

        elif field["type"] == constants.SCORE:
            try:
                minimum = int(form.get("minimum"))
            except (TypeError, ValueError):
                minimum = None
            try:
                maximum = int(form.get("maximum"))
            except (TypeError, ValueError):
                maximum = None
            if minimum is None or maximum is None or maximum <= minimum:
                raise ValueError("Invalid score range.")
            field["minimum"] = minimum
            field["maximum"] = maximum
            field["slider"] = utils.to_bool(form.get("slider"))

        elif field["type"] == constants.RANK:
            field["minimum"] = 1

        elif field["type"] == constants.DOCUMENT:
            extensions = [
                e.strip().lstrip(".").lower()
                for e in form.get("extensions", "").split(",")
            ]
            field["extensions"] = [e for e in extensions if e]

        elif field["type"] == constants.REPEAT:
            try:
                minimum = int(form.get("minimum"))
            except (TypeError, ValueError):
                minimum = None
            if minimum is not None and minimum < 1:
                raise ValueError(
                    "Invalid minimum value; if given"
                    " must be larger than or equal to 1."
                )
            field["minimum"] = minimum
            try:
                maximum = int(form.get("maximum"))
            except (TypeError, ValueError):
                maximum = None
            if maximum is not None and maximum < 2:
                raise ValueError(
                    "Invalid maximum value;" " must be larger than or equal to 2."
                )
            field["maximum"] = maximum
            field["blocktitle"] = form.get("blocktitle")

    def add_proposal_field(self, form):
        "Add a field to the proposal definition."
        if form["type"] not in constants.PROPOSAL_FIELD_TYPES:
            raise ValueError("Invalid field type.")
        field = self.add_field(form)
        if field["identifier"] in [f["identifier"] for f in self.doc["proposal"]]:
            raise ValueError("Field identifier is already in use.")
        self.doc["proposal"].append(field)

    def edit_proposal_field(self, fid, form):
        "Edit the field for the proposal definition."
        self.edit_field(self.doc["proposal"], fid, form)

    def delete_proposal_field(self, fid):
        "Delete the given field from proposal definition."
        for pos, field in enumerate(self.doc["proposal"]):
            if field["identifier"] == fid:
                self.doc["proposal"].pop(pos)
                break

    def add_review_field(self, form):
        "Add a field to the review definition."
        if form["type"] not in constants.REVIEW_FIELD_TYPES:
            raise ValueError("Invalid field type for review.")
        field = self.add_field(form)
        if field["identifier"] in [f["identifier"] for f in self.doc["review"]]:
            raise ValueError("Field identifier is already in use.")
        self.doc["review"].append(field)

    def edit_review_field(self, fid, form):
        "Edit the review definition field."
        self.edit_field(self.doc["review"], fid, form)

    def delete_review_field(self, fid):
        "Delete the field from the review definition."
        for pos, field in enumerate(self.doc["review"]):
            if field["identifier"] == fid:
                self.doc["review"].pop(pos)
                break

    def add_decision_field(self, form):
        "Add a field to the decision definition."
        if form["type"] not in constants.DECISION_FIELD_TYPES:
            raise ValueError("Invalid field type.")
        field = self.add_field(form)
        if field["identifier"] in [f["identifier"] for f in self.doc["decision"]]:
            raise ValueError("Field identifier is already in use.")
        self.doc["decision"].append(field)

    def edit_decision_field(self, fid, form):
        "Edit the decision definition field."
        self.edit_field(self.doc["decision"], fid, form)

    def delete_decision_field(self, fid):
        "Delete the field from the decision definition."
        for pos, field in enumerate(self.doc["decision"]):
            if field["identifier"] == fid:
                self.doc["decision"].pop(pos)
                break

    def add_grant_field(self, form):
        "Add a field to the grant dossier definition."
        if not "grant" in self.doc:  # To upgrade from older versions.
            self.doc["grant"] = []
        if form["type"] not in constants.GRANT_FIELD_TYPES:
            raise ValueError("Invalid field type.")
        field = self.add_field(form)
        if field["identifier"] in [f["identifier"] for f in self.doc["grant"]]:
            raise ValueError("Field identifier is already in use.")
        self.doc["grant"].append(field)

    def edit_grant_field(self, fid, form):
        "Edit the grant dossier definition field."
        self.edit_field(self.doc["grant"], fid, form)

    def delete_grant_field(self, fid):
        """Delete the field from the grant dossier definition.
        If any repeat fields for it, then remove also those.
        """
        for pos, field in enumerate(self.doc["grant"]):
            if field["identifier"] == fid:
                self.doc["grant"][pos] = None
            elif field.get("repeat") == fid:
                self.doc["grant"][pos] = None
        self.doc["grant"] = [f for f in self.doc["grant"] if f is not None]

    def add_document(self, infile, description):
        "Add a document to the call."
        filename = self.add_attachment(infile.filename, infile.read(), infile.mimetype)
        for document in self.doc["documents"]:
            if document["name"] == filename:
                document["description"] = description
                break
        else:
            self.doc["documents"].append({"name": filename, "description": description})

    def delete_document(self, documentname):
        "Delete the named document from the call."
        for pos, document in enumerate(self.doc["documents"]):
            if document["name"] == documentname:
                self.delete_attachment(documentname)
                self.doc["documents"].pop(pos)
                break

    def edit_privileges(self, form):
        "Edit the privileges flags."
        self.doc["privileges"] = {}
        for flag in constants.PRIVILEGES:
            self.doc["privileges"][flag] = utils.to_bool(form.get(flag))


def get_call(cid):
    "Return the call with the given identifier."
    key = f"call {cid}"
    try:
        return utils.cache_get(key)
    except KeyError:
        result = [
            r.doc
            for r in flask.g.db.view("calls", "identifier", key=cid, include_docs=True)
        ]
        if len(result) == 1:
            return utils.cache_put(key, result[0])
        else:
            return None


def get_banner_fields(fields):
    "Return fields flagged as banner fields. Avoid repeated fields."
    return [f for f in fields if f.get("banner") and not f.get("repeat")]


def allow_create(user=None):
    """Allow admin, staff (depending on configuration) and users with
    'call_creator' flag set to create a call.
    """
    if user is None:
        user = flask.g.current_user
    if not user:
        return False
    if user["role"] == constants.ADMIN:
        return True
    if user["role"] == constants.STAFF and flask.current_app.config.get(
        "CALL_STAFF_CREATE"
    ):
        return True
    if user.get("call_creator"):
        return True
    return False


def allow_view(call):
    """The admin, staff and call owner may view any call.
    Others may view a call if it has an opens date, i.e. is published.
    """
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    if has_access_view(call):
        return True
    if call["opens"]:
        return True
    return False


def allow_edit(call):
    """The admin, staff (depending on configuration) and call owner
    may edit a call, and accounts with edit access.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff and flask.current_app.config.get("CALL_STAFF_EDIT"):
        return True
    if am_owner(call):
        return True
    if has_access_edit(call):
        return True
    return False


def allow_identifier_edit(call):
    """Is the identifier of the call editable?
    Only if no dependent objects have been created, and it has not been opened.
    """
    if not call.get("identifier"):
        return True
    if anubis.database.get_count("proposals", "call", call["identifier"]):
        return False
    if anubis.database.get_count("reviews", "call", call["identifier"]):
        return False
    if anubis.database.get_count("decisions", "call", call["identifier"]):
        return False
    if anubis.database.get_count("grants", "call", call["identifier"]):
        return False
    if is_open(call):
        return False
    return True


def allow_delete(call):
    "Allow the admin or call owner to delete a call if it has no proposals."
    if not (flask.g.am_admin or am_owner(call)):
        return False
    if anubis.database.get_count("proposals", "call", call["identifier"]) == 0:
        return True
    return False


def allow_change_access(call):
    """The admin, staff, call owner and accounts with edit access
    may change access for the call.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    if has_access_edit(call):
        return True
    return False


def allow_view_details(call):
    """The admin, staff, call owner, reviewers and accounts with view access
    may view certain details of the call, such as call field definitions,
    call owner, reviewers and access flags.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    if am_reviewer(call):
        return True
    if has_access_view(call):
        return True
    return False


def allow_view_proposals(call):
    """The admin, staff, call owner, reviewers and accounts with view access
    may view all proposals of the call.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    if am_reviewer(call):
        return True
    if has_access_view(call):
        return True
    return False


def allow_view_reviews(call):
    """The admin, staff and call owner may view all reviews in the call.
    Review chairs may view all reviews.
    Other reviewers may view depending on the privileges flag for the call.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    if am_reviewer(call):
        if am_chair(call):
            return True
        return bool(call["privileges"].get("allow_reviewer_view_all_reviews"))
    return False


def allow_view_decisions(call):
    """The admin, staff and call owner may view all decisions in the call.
    Reviewer may view all decisions in a call once the review
    due date has passed; this should reduce confusion.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if am_owner(call):
        return True
    due = call.get("reviews_due")
    if due:
        return am_reviewer(call) and due < utils.get_now()
    return False


def allow_view_grants(call):
    """The admin, staff and accounts with view access may view
    all grants in the call.
    """
    if not flask.g.current_user:
        return False
    if flask.g.am_admin:
        return True
    if flask.g.am_staff:
        return True
    if has_access_view(call):
        return True
    return False


def am_reviewer(call):
    "Is the current user a reviewer in the call?"
    if not flask.g.current_user:
        return False
    if flask.g.current_user["username"] in call["reviewers"]:
        return True
    return False


def am_chair(call):
    "Is the current user a chair in the call?"
    if not flask.g.current_user:
        return False
    if flask.g.current_user["username"] in call["chairs"]:
        return True
    return False


def am_owner(call):
    "Is the current user the owner of the call?"
    if not flask.g.current_user:
        return False
    if flask.g.current_user["username"] == call["owner"]:
        return True
    return False


def has_access_view(call):
    "Does the current user have explicit view access to the call?"
    if not flask.g.current_user:
        return False
    if flask.g.current_user["username"] in call.get("access_view", []):
        return True
    return False


def has_access_edit(call):
    "Does the current user have explicit edit access to the call?"
    if not flask.g.current_user:
        return False
    if flask.g.current_user["username"] in call.get("access_edit", []):
        return True
    return False


def is_open(call):
    "Is the call open? Excludes undefined."
    if is_undefined(call):
        return False
    now = utils.get_now()
    if call["opens"] > now:
        return False
    if call["closes"] < now:
        return False
    return True


def is_closed(call):
    "Is the call closed? Excludes undefined."
    if is_undefined(call):
        return False
    if call["closes"] > utils.get_now():
        return False
    return True


def is_undefined(call):
    "Is either of the call opens or closes dates undefined?"
    return not call["opens"] or not call["closes"]


def is_unpublished(call):
    "Are the call opens and closes dates undefined, or has opens date not been reached?"
    if is_undefined(call):
        return True
    if calls["open"] > utils.get_now():
        return True
    return False
