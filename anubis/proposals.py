"Lists of proposals."

import io
import statistics

import flask
import xlsxwriter

import anubis.call
import anubis.decision
import anubis.proposal
import anubis.user
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint("proposals", __name__)


@blueprint.route("/call/<cid>")
@utils.login_required
def call(cid):
    "List all proposals in a call."
    call = anubis.call.get_call(cid)
    if not call:
        return utils.error("No such call.", flask.url_for("home"))
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.", flask.url_for("home"))
    proposals = get_call_proposals(call)
    all_emails = []
    submitted_emails = []
    for proposal in proposals:
        user = anubis.user.get_user(username=proposal["user"])
        if not user:
            continue
        all_emails.append(user["email"])
        if proposal.get("submitted"):
            submitted_emails.append(user["email"])
    # There may be accounts that have no email!
    all_emails = sorted(set([e for e in all_emails if e]))
    submitted_emails = sorted(set([e for e in submitted_emails if e]))
    email_lists = {
        "Emails to for submitted proposals": ", ".join(submitted_emails),
        "Emails for all proposals": ", ".join(all_emails),
    }
    rank_fields, rank_errors = get_review_rank_fields_errors(call, proposals)
    for error in rank_errors:
        utils.flash_warning(error)
    return flask.render_template(
        "proposals/call.html",
        call=call,
        proposals=proposals,
        email_lists=email_lists,
        review_score_fields=get_review_score_fields(call, proposals),
        review_rank_fields=rank_fields,
        review_rank_errors=rank_errors,
        am_reviewer=anubis.call.am_reviewer(call),
        allow_view_details=anubis.call.allow_view_details(call),
        allow_view_reviews=anubis.call.allow_view_reviews(call),
        allow_view_decisions=anubis.call.allow_view_decisions(call),
        allow_view_grants=anubis.call.allow_view_grants(call),
        get_reviewer_review=anubis.review.get_reviewer_review,
    )


@blueprint.route("/call/<cid>.xlsx")
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all proposals in a call."
    call = anubis.call.get_call(cid)
    if not call:
        return utils.error("No such call.", flask.url_for("home"))
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.", flask.url_for("home"))
    submitted = utils.to_bool(flask.request.args.get("submitted", ""))
    response = flask.make_response(get_call_xlsx(call, submitted=submitted))
    response.headers.set("Content-Type", constants.XLSX_MIMETYPE)
    response.headers.set(
        "Content-Disposition",
        "attachment",
        filename=f"{call['identifier']}_proposals.xlsx",
    )
    return response


def get_call_xlsx(call, submitted=False, proposals=None):
    """Return the content of an XLSX file for all proposals in a call.
    Optionally only the submitted ones.
    Optionally for the given list proposals.
    """
    if proposals is None:
        title = f"Proposals in {call['identifier']}"
        proposals = get_call_proposals(call, submitted=submitted)
    else:
        title = f"Selected proposals in {call['identifier']}"
    score_fields = get_review_score_fields(call, proposals)
    rank_fields, rank_errors = get_review_rank_fields_errors(call, proposals)
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True})
    head_text_format = wb.add_format(
        {
            "bold": True,
            "text_wrap": True,
            "bg_color": "#9ECA7F",
            "font_size": 15,
            "align": "center",
            "border": 1,
        }
    )
    normal_text_format = wb.add_format(
        {"font_size": 14, "align": "left", "valign": "vcenter"}
    )
    ws = wb.add_worksheet(title[:31])
    ws.freeze_panes(1, 1)
    ws.set_row(0, 60, head_text_format)
    ws.set_column(1, 1, 40, normal_text_format)
    ws.set_column(2, 2, 10, normal_text_format)
    ws.set_column(3, 4, 20, normal_text_format)

    nrow = 0
    row = ["Proposal", "Proposal title"]
    row.extend(["Submitted", "Submitter", "Email", "Affiliation"])
    ncol = len(row)
    for field in call["proposal"]:
        row.append(field["title"] or field["identifier"].capitalize())
        if field["type"] in (constants.LINE, constants.EMAIL):
            ws.set_column(ncol, ncol, 40, normal_text_format)
        elif field["type"] == constants.TEXT:
            ws.set_column(ncol, ncol, 60, normal_text_format)
        ncol += 1
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    if allow_view_reviews:
        for rf in rank_fields.values():
            row.append(f"Reviews {rf['title']}: ranking factor")
            row.append(f"Reviews {rf['title']}: stdev")
        if len(score_fields) >= 2:
            row.append("Reviews all scores: mean of means")
            row.append("Reviews all scores: stdev of means")
        for rf in score_fields.values():
            row.append(f"Reviews {rf['title']}: N")
            row.append(f"Reviews {rf['title']}: mean")
            row.append(f"Reviews {rf['title']}: stdev")
    allow_view_decisions = anubis.call.allow_view_decisions(call)
    if allow_view_decisions:
        row.append("Decision")
        row.append("Decision status")
        for field in call["decision"]:
            if not field.get("banner"):
                continue
            title = field["title"] or field["identifier"].capitalize()
            row.append(title)
    ws.write_row(nrow, 0, row)
    nrow += 1

    for proposal in proposals:
        ncol = 0
        ws.write_url(
            nrow,
            ncol,
            flask.url_for(
                "proposal.display", pid=proposal["identifier"], _external=True
            ),
            string=proposal["identifier"],
        )
        ncol += 1
        ws.write_string(nrow, ncol, proposal.get("title") or "")
        ncol += 1
        ws.write_string(nrow, ncol, proposal.get("submitted") and "yes" or "no")
        ncol += 1
        user = anubis.user.get_user(username=proposal["user"])
        ws.write_string(nrow, ncol, utils.get_fullname(user))
        ncol += 1
        ws.write_string(nrow, ncol, user.get("email") or "")
        ncol += 1
        ws.write_string(nrow, ncol, user.get("affiliation") or "")
        ncol += 1

        for field in call["proposal"]:
            value = proposal["values"].get(field["identifier"])
            if value is None:
                ws.write_string(nrow, ncol, "")
            elif field["type"] == constants.TEXT:
                ws.write_string(nrow, ncol, value)
            elif field["type"] == constants.DOCUMENT:
                ws.write_url(
                    nrow,
                    ncol,
                    flask.url_for(
                        "proposal.document",
                        pid=proposal["identifier"],
                        fid=field["identifier"],
                        _external=True,
                    ),
                    string="Download",
                )
            elif field["type"] == constants.SELECT:
                if isinstance(value, list):  # Multiselect
                    ws.write(nrow, ncol, "\n".join(value))
                else:
                    ws.write(nrow, ncol, value)
            else:
                ws.write(nrow, ncol, value)
            ncol += 1

        if allow_view_reviews:
            for id in rank_fields.keys():
                value = proposal["ranking"][id]["factor"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal["ranking"][id]["stdev"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
            if len(score_fields) >= 2:
                value = proposal["scores"]["__mean__"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal["scores"]["__stdev__"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
            for id in score_fields:
                ws.write_number(nrow, ncol, proposal["scores"][id]["n"])
                ncol += 1
                value = proposal["scores"][id]["mean"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal["scores"][id]["stdev"]
                if value is None:
                    ws.write_string(nrow, ncol, "")
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1

        if allow_view_decisions:
            decision = anubis.decision.get_decision(proposal.get("decision")) or {}
            if decision:
                verdict = decision.get("verdict")
                if verdict:
                    ws.write(nrow, ncol, "Accepted")
                elif verdict is None:
                    ws.write(nrow, ncol, "Undecided")
                else:
                    ws.write(nrow, ncol, "Declined")
            else:
                ws.write(nrow, ncol, "-")
            ncol += 1
            if decision.get("finalized"):
                ws.write(nrow, ncol, "Finalized")
            else:
                ws.write(nrow, ncol, "-")
            ncol += 1
            for field in call["decision"]:
                if not field.get("banner"):
                    continue
                if decision.get("finalized"):
                    value = decision["values"].get(field["identifier"])
                    ws.write(nrow, ncol, value)
                else:
                    ws.write_string(nrow, ncol, "")
                ncol += 1

        nrow += 1

    wb.close()
    return output.getvalue()


@blueprint.route("/user/<username>")
@utils.login_required
def user(username):
    "List all proposals for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error("No such user.", flask.url_for("home"))
    if not anubis.user.allow_view(user):
        return utils.error(
            "You may not view the user's proposals.", flask.url_for("home")
        )
    proposals = get_user_proposals(user["username"])
    proposals.extend(utils.get_docs_view("proposals", "access", user["username"]))
    return flask.render_template(
        "proposals/user.html",
        user=user,
        proposals=proposals,
        allow_view_decision=anubis.decision.allow_view,
    )


def get_call_proposals(call, submitted=False):
    """Get the proposals in the call.
    Only include those allowed to view, unless allowed to view call.
    Optionally only the submitted ones.
    """
    result = [
        i.doc
        for i in flask.g.db.view(
            "proposals", "call", key=call["identifier"], reduce=False, include_docs=True
        )
    ]
    if not anubis.call.allow_view(call):
        result = [p for p in result if anubis.proposal.allow_view(p)]
    if submitted:
        result = [p for p in result if p.get("submitted")]
    result.sort(key=lambda p: p["identifier"])
    for proposal in result:
        flask.g.cache[f"proposal {proposal['identifier']}"] = proposal
    return result


def get_user_proposals(username):
    "Get all proposals created by the user."
    result = [
        i.doc
        for i in flask.g.db.view(
            "proposals", "user", key=username, reduce=False, include_docs=True
        )
    ]
    result.sort(key=lambda p: p["identifier"])
    for proposal in result:
        flask.g.cache[f"proposal {proposal['identifier']}"] = proposal
    return result


def get_review_score_fields(call, proposals):
    """Return a dictionary of the score banner fields in the reviews.
    Compute the score means and stdevs. If there are more than two score
    fields, then also compute the mean of the means and the stdev of the means.
    This is done over all finalized reviews for each proposal.
    Store the values in the proposal document.
    """
    fields = dict(
        [
            (f["identifier"], f)
            for f in call["review"]
            if f.get("banner") and f["type"] == constants.SCORE
        ]
    )
    for proposal in proposals:
        reviews = utils.get_docs_view("reviews", "proposal", proposal["identifier"])
        # Only include finalized reviews in the calculation.
        reviews = [r for r in reviews if r.get("finalized")]
        scores = dict([(id, list()) for id in fields])
        for review in reviews:
            for id in fields:
                value = review["values"].get(id)
                if value is not None:
                    scores[id].append(float(value))
        proposal["scores"] = dict()
        for id in fields:
            proposal["scores"][id] = d = dict()
            d["n"] = len(scores[id])
            try:
                d["mean"] = round(statistics.mean(scores[id]), 1)
            except statistics.StatisticsError:
                d["mean"] = None
            try:
                d["stdev"] = round(statistics.stdev(scores[id]), 1)
            except statistics.StatisticsError:
                d["stdev"] = None
        if len(fields) >= 2:
            mean_scores = [
                d["mean"] for d in proposal["scores"].values() if d["mean"] is not None
            ]
            try:
                mean_means = round(statistics.mean(mean_scores), 1)
            except statistics.StatisticsError:
                mean_means = None
            proposal["scores"]["__mean__"] = mean_means
            try:
                stdev_means = round(statistics.stdev(mean_scores), 1)
            except statistics.StatisticsError:
                stdev_means = None
            proposal["scores"]["__mean__"] = mean_means
            proposal["scores"]["__stdev__"] = stdev_means
    return fields


def get_review_rank_fields_errors(call, proposals):
    """Return a tuple containing a dictionary of the rank banner fields
    in the reviews and a list of errors.
    Compute the ranking factors of each proposal from all finalized reviews.
    Check that the ranks are consecutive for all reviewers.
    """
    fields = dict(
        [
            (f["identifier"], f)
            for f in call["review"]
            if f.get("banner") and f["type"] == constants.RANK
        ]
    )
    errors = []
    for id in fields.keys():
        ranks = dict()  # key: reviewer, value: dict(proposal: rank)
        for proposal in proposals:
            reviews = utils.get_docs_view("reviews", "proposal", proposal["identifier"])
            # Only include finalized reviews in the calculation.
            reviews = [r for r in reviews if r.get("finalized")]
            for review in reviews:
                try:
                    value = review["values"][id]
                    if value is None:
                        raise KeyError
                except KeyError:
                    pass
                else:
                    d = ranks.setdefault(review["reviewer"], dict())
                    d[proposal["identifier"]] = value
        # Check that ranking values start with 1 and are consecutiive.
        for reviewer, values in ranks.items():
            series = list(values.values())
            if series:
                user = anubis.user.get_user(reviewer)
                name = utils.get_fullname(user)
                if min(series) != 1:
                    errors.append(f"{name} reviews '{id}' do not start with 1.")
                elif set(series) != set(range(1, max(series) + 1)):
                    errors.append(f"{name} reviews '{id}' are not consecutive.")
        # For each proposal, compute ranking factor.
        for proposal in proposals:
            factors = []
            for reviewer, values in ranks.items():
                try:
                    value = values[proposal["identifier"]]
                except KeyError:
                    pass
                else:
                    factors.append(float(len(values) - value + 1) / len(values))
            rf = proposal.setdefault("ranking", dict())
            rf[id] = dict()
            try:
                rf[id]["factor"] = round(10.0 * statistics.mean(factors), 1)
            except statistics.StatisticsError:
                rf[id]["factor"] = None
            try:
                rf[id]["stdev"] = round(10.0 * statistics.stdev(factors), 1)
            except statistics.StatisticsError:
                rf[id]["stdev"] = None
    return fields, errors
