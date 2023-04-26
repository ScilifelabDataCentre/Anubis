"Lists of proposals."

import io
import statistics

import flask
import xlsxwriter

import anubis.call
import anubis.database
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
        return utils.error("No such call.")
    if not anubis.call.allow_view_proposals(call):
        return utils.error("You may not view the proposals of the call.")

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
        proposal["n_reviews"] = anubis.database.get_count(
            "reviews", "proposal", proposal["identifier"]
        )
    # There may be accounts that have no email!
    all_emails = sorted(set([e for e in all_emails if e]))
    submitted_emails = sorted(set([e for e in submitted_emails if e]))
    email_lists = {
        "Emails to for submitted proposals": ", ".join(submitted_emails),
        "Emails for all proposals": ", ".join(all_emails),
    }
    rank_fields, rank_errors = get_rank_fields_errors(call, proposals)
    return flask.render_template(
        "proposals/call.html",
        call=call,
        proposals=proposals,
        email_lists=email_lists,
        review_score_fields=get_review_score_fields(call, proposals),
        review_rank_fields=rank_fields,
        review_rank_errors=rank_errors,
        am_reviewer=anubis.call.am_reviewer(call),
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
        return utils.error("No such call.")
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.")

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
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    if allow_view_reviews:
        score_fields = get_review_score_fields(call, proposals)
        rank_fields, rank_errors = get_review_rank_fields_errors(call, proposals)
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True})
    formats = utils.create_xlsx_formats(wb)
    # Hard str(len) limit for worksheet title.
    ws = wb.add_worksheet(title[:31])
    ws.freeze_panes(1, 1)
    ws.set_row(0, 60, formats["head"])
    ws.set_column(0, 0, 16, formats["normal"])
    ws.set_column(1, 1, 40, formats["normal"])
    ws.set_column(2, 2, 10, formats["normal"])
    ws.set_column(3, 4, 20, formats["normal"])

    nrow = 0
    row = ["Proposal", "Proposal title"]
    row.extend(["Submitted", "Submitter", "Email", "Affiliation"])
    ncol = len(row)
    for field in call["proposal"]:
        row.append(field["title"] or field["identifier"].capitalize())
        if field["type"] in (constants.LINE, constants.EMAIL):
            ws.set_column(ncol, ncol, 40, formats["normal"])
        elif field["type"] == constants.TEXT:
            ws.set_column(ncol, ncol, 60, formats["normal"])
        ncol += 1
    if allow_view_reviews:
        row.append("# Reviews")
        row.append("# Finalized reviews")
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
        ws.write_string(nrow, ncol, proposal.get("submitted") and "Yes" or "No")
        ncol += 1
        user = anubis.user.get_user(username=proposal["user"])
        ws.write_string(nrow, ncol, anubis.user.get_fullname(user))
        ncol += 1
        ws.write_string(nrow, ncol, user.get("email") or "")
        ncol += 1
        ws.write_string(nrow, ncol, user.get("affiliation") or "")
        ncol += 1

        for field in call["proposal"]:
            value = proposal["values"].get(field["identifier"])
            # Ugly, but necessary...
            if value is not None and field["type"] == constants.DOCUMENT:
                value = flask.url_for(
                    "proposal.document",
                    pid=proposal["identifier"],
                    fid=field["identifier"],
                    _external=True,
                )
            utils.write_xlsx_field(ws, nrow, ncol, value, field["type"], formats)
            ncol += 1

        if allow_view_reviews:
            ws.write_number(nrow, ncol, proposal["number_reviews"])
            ncol += 1
            ws.write_number(nrow, ncol, proposal["number_finalized_reviews"])
            ncol += 1
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
        return utils.error("No such user.")
    if not anubis.user.allow_view(user):
        return utils.error("You may not view the user's proposals.")

    proposals = get_user_proposals(user["username"])
    proposals.extend(anubis.database.get_docs("proposals", "access", user["username"]))
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
        utils.cache_put(f"proposal {proposal['identifier']}", proposal)
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
        utils.cache_put(f"proposal {proposal['identifier']}", proposal)
    return result


def get_review_score_fields(call, proposals):
    """Return a dictionary of the score banner fields in the reviews.
    Compute the score means and stdevs. If there are more than two score
    fields, then also compute the mean of the means and the stdev of the means.
    This is done over all finalized non-conflict-of-interest reviews for each proposal.
    Store the values in the proposal document.
    Also store the total number of reviews and finalized in the proposal document.
    """
    fields = dict(
        [
            (f["identifier"], f)
            for f in call["review"]
            if f.get("banner") and f["type"] == constants.SCORE
        ]
    )
    for proposal in proposals:
        reviews = anubis.database.get_docs(
            "reviews", "proposal", proposal["identifier"]
        )
        proposal["number_reviews"] = len(reviews)
        reviews = [r for r in reviews if r.get("finalized")]
        proposal["number_finalized_reviews"] = len(reviews)
        reviews = [r for r in reviews if not r["values"].get("conflict_of_interest")]
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


def get_rank_fields_errors(call, proposals):
    """Return a tuple containing a dictionary of the rank banner fields
    in the reviews and a list of reviewers with rank field errors.
    Check that the ranks are consecutive for all reviewers.
    Compute the ranking factors of each proposal from all finalized
    non-conflict-of-interest reviews.
    """
    rank_fields = dict(
        [
            (f["identifier"], f)
            for f in call["review"]
            if f.get("banner") and f["type"] == constants.RANK
        ]
    )
    rank_errors = []
    for id in rank_fields.keys():
        # Collect the ranks set by each reviewer for each proposal under their review.
        ranks = dict()  # key: reviewerid, value: dict(pid: rank)
        for proposal in proposals:
            reviews = anubis.database.get_docs(
                "reviews", "proposal", proposal["identifier"]
            )
            reviews = [r for r in reviews if r.get("finalized")]
            reviews = [
                r for r in reviews if not r["values"].get("conflict_of_interest")
            ]
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
        # Check that ranking values start with 1 and are consecutive.
        for reviewer, values in ranks.items():
            series = list(values.values())
            if series:
                if set(series) != set(range(1, max(series) + 1)):
                    rank_errors.append(anubis.user.get_user(username=reviewer))
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
    return rank_fields, rank_errors
