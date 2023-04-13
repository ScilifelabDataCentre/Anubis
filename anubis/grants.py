"Lists of grants."

import io
import zipfile

import flask
import xlsxwriter

import anubis.call
import anubis.database
import anubis.grant
import anubis.proposal
import anubis.user

from anubis import constants
from anubis import utils

blueprint = flask.Blueprint("grants", __name__)


@blueprint.route("/call/<cid>")
@utils.login_required
def call(cid):
    "List all grants for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error("No such call.")
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.")
    if not anubis.call.allow_view_grants(call):
        return utils.error("You may not view the grants of the call.")

    grants = anubis.database.get_docs("grants", "call", call["identifier"])
    # Convert username for grant to full user dict.
    for grant in grants:
        grant["user"] = anubis.user.get_user(grant["user"])
    # There may be accounts that have no emails.
    receiver_emails = [g["user"]["email"] for g in grants]
    receiver_emails = [e for e in receiver_emails if e]
    access_emails = []
    field_emails = []
    for grant in grants:
        access_emails.extend(
            [anubis.user.get_user(a)["email"] for a in grant.get("access_view", [])]
        )
        for field in call["grant"]:
            if field["type"] == constants.EMAIL:
                if field.get("repeat"):
                    n_repeat = grant["values"].get(field["repeat"]) or 0
                    for n in range(1, n_repeat + 1):
                        key = f"{field['identifier']}-{n}"
                        field_emails.append(grant["values"].get(key))
                else:
                    field_emails.append(grant["values"].get(field["identifier"]))
    field_emails = sorted(set([e for e in field_emails if e]))
    access_emails = sorted(set([e for e in access_emails if e]))
    all_emails = sorted(set(receiver_emails).union(access_emails).union(field_emails))
    email_lists = {
        "Grant receivers (= proposal submitters)": ", ".join(receiver_emails),
        "Persons with access to a grant": ", ".join(access_emails),
        "Emails provided in grant fields": ", ".join(field_emails),
        "All emails": ", ".join(all_emails),
    }
    return flask.render_template(
        "grants/call.html", call=call, grants=grants, email_lists=email_lists
    )


@blueprint.route("/call/<cid>.xlsx")
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all grants for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error("No such call.")
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.")
    if not anubis.call.allow_view_grants(call):
        return utils.error("You may not view the grants of the call.")

    grants = anubis.database.get_docs("grants", "call", call["identifier"])
    grants.sort(key=lambda g: g["identifier"])
    content = get_call_grants_xlsx(call, grants)
    response = flask.make_response(content)
    response.headers.set("Content-Type", constants.XLSX_MIMETYPE)
    response.headers.set(
        "Content-Disposition", "attachment", filename=f"{cid}_grants.xlsx"
    )
    return response


def get_call_grants_xlsx(call, grants):
    "Return the content for the XLSX file for the list of grants."
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True})
    formats = utils.create_xlsx_formats(wb)
    ws = wb.add_worksheet(f"Grants in call {call['identifier']}"[:31])  # Hard len(str) limit.
    ws.freeze_panes(2, 1)
    ws.set_row(0, 60, formats["head"])
    ws.set_row(1, 60, formats["head"])
    ws.set_column(0, 0, 16, formats["normal"])
    ws.set_column(1, 2, 10, formats["normal"])
    ws.set_column(3, 3, 40, formats["normal"])
    ws.set_column(4, 6, 20, formats["normal"])
    # More set below, after grant fields (including repeats)

    nrow = 0
    row = [
        "Grant",
        "Status",
        "Proposal",
        "Proposal title",
        "Submitter",
        "Email",
        "Affiliation",
    ]
    ws.write_row(nrow, 0, row)

    # Repeated fields are those fields to be repeated N number
    # of times as given in a repeat field. Notice the difference!
    # Repeated fields are in a certain sense dependent on their repeat field.

    # First all non-repeated fields, including any repeat fields.
    pos = len(row) - 1
    start_pos = pos
    for field in call["grant"]:
        if field.get("repeat"):
            continue
        title = field["title"] or field["identifier"].capitalize()
        pos += 1
        n_repeat = len(
            [f for f in call["grant"] if f.get("repeat") == field["identifier"]]
        )
        if n_repeat:
            ws.merge_range(0, pos, 0, pos + n_repeat - 1, title)
            pos += n_repeat - 1
        else:
            ws.write_row(nrow, pos, [title])
    nrow += 1

    # Then repeated fields; their titles beneath the repeat field.
    pos = start_pos
    for field in call["grant"]:
        if field.get("repeat"):
            continue
        pos += 1
        repeat = [
            f["title"] or f["identifier"].capitalize()
            for f in call["grant"]
            if f.get("repeat") == field["identifier"]
        ]
        n_repeat = len(repeat)
        if n_repeat:
            ws.write_row(nrow, pos, repeat)
            pos += n_repeat - 1
    nrow += 1

    for grant in grants:
        # Find the maximum number of rows to merge for this grant.
        n_merge = 1
        for field in call["grant"]:
            if field["type"] != constants.REPEAT:
                continue
            try:
                n_merge = max(n_merge, grant["values"][field["identifier"]] or 0)
            except KeyError:
                pass

        ncol = 0
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        ws.write_url(
            nrow,
            ncol,
            flask.url_for("grant.display", gid=grant["identifier"], _external=True),
            string=grant["identifier"],
        )
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        ws.write_string(nrow, ncol, grant["errors"] and "Incomplete" or "Complete")
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        ws.write_url(
            nrow,
            ncol,
            flask.url_for("proposal.display", pid=grant["proposal"], _external=True),
            string=grant["proposal"],
        )
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        proposal = anubis.proposal.get_proposal(grant["proposal"])
        ws.write_string(nrow, ncol, proposal["title"])
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        user = anubis.user.get_user(username=proposal["user"])
        ws.write_string(nrow, ncol, anubis.user.get_fullname(user))
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        ws.write_string(nrow, ncol, user.get("email") or "")
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
        ws.write_string(nrow, ncol, user.get("affiliation") or "")
        max_ncol = ncol
        ncol += 1

        for field in call["grant"]:
            if field.get("repeat"):
                continue
            if field["type"] == constants.REPEAT:
                n_repeat = grant["values"][field["identifier"]]
                if not n_repeat:
                    continue
                col_offset = 0
                for repeated in call["grant"]:
                    if repeated.get("repeat") != field["identifier"]:
                        continue
                    for row_offset in range(n_repeat):
                        fid = f"{repeated['identifier']}-{row_offset+1}"
                        _write_xlsx_field(
                            ws,
                            nrow + row_offset,
                            ncol + col_offset,
                            grant["values"].get(fid),
                            repeated["type"],
                            grant["identifier"],
                            fid,
                            formats
                        )
                        max_ncol = max(max_ncol, ncol + col_offset)
                    col_offset += 1
            else:
                if n_merge > 1:
                    ws.merge_range(nrow, ncol, nrow + n_merge - 1, ncol, "")
                _write_xlsx_field(
                    ws,
                    nrow,
                    ncol,
                    grant["values"].get(field["identifier"]),
                    field["type"],
                    grant["identifier"],
                    field["identifier"],
                    formats
                )
                max_ncol = max(max_ncol, ncol)
            ncol += 1

        nrow += n_merge

    # Set formatting for additional columns.
    if max_ncol > 6:
        ws.set_column(6 + 1, max_ncol, 20, formats["normal"])

    wb.close()
    return output.getvalue()


def _write_xlsx_field(ws, nrow, ncol, value, field_type, gid, fid, formats):
    "Small wrapper function for computing the relevant URL."
    # Ugly, but necessary...
    if value is not None and field_type == constants.DOCUMENT:
        value = flask.url_for(
            "grant.document",
            gid=gid,
            fid=fid,
            _external=True,
        )
    utils.write_xlsx_field(ws, nrow, ncol, value, field_type, formats)


@blueprint.route("/call/<cid>.zip")
@utils.login_required
def call_zip(cid):
    """Return a zip file containing the XLSX file of all grants for a call
    and all documents in all grant dossiers.
    """
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error("No such call.")
    if not anubis.call.allow_view(call):
        return utils.error("You may not view the call.")
    if not anubis.call.allow_view_grants(call):
        return utils.error("You may not view the grants of the call.")

    # Colon ':' is a problematic character in filenames; replace by dash '_'
    cid = cid.replace(":", "-")
    grants = anubis.database.get_docs("grants", "call", call["identifier"])
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as outfile:
        outfile.writestr(f"{cid}_grants.xlsx", get_call_grants_xlsx(call, grants))
        for grant in grants:
            for document in anubis.grant.get_grant_documents(grant):
                outfile.writestr(document["filename"], document["content"])
    response = flask.make_response(output.getvalue())
    response.headers.set("Content-Type", constants.ZIP_MIMETYPE)
    response.headers.set(
        "Content-Disposition", "attachment", filename=f"{cid}_grants.zip"
    )
    return response


@blueprint.route("/user/<username>")
@utils.login_required
def user(username):
    "List all grants for a user, including the grants the user has access to."
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error("No such user.")
    if not anubis.user.allow_view(user):
        return utils.error("You may not view the user's grants.")

    grants = anubis.database.get_docs("grants", "user", user["username"])
    grants.extend(anubis.database.get_docs("grants", "access", user["username"]))
    return flask.render_template("grants/user.html", user=user, grants=grants)
