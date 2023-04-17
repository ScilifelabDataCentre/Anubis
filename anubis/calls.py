"Lists of calls."

import io

import flask
import xlsxwriter

import anubis.call
import anubis.database
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint("calls", __name__)


@blueprint.route("")
@utils.staff_required
def all():
    "Display all calls."
    return flask.render_template("calls/all.html", calls=get_all_calls())


@blueprint.route("/all_xlsx")
@utils.staff_required
def all_xlsx():
    "All calls in XLSX format."
    return get_calls_xlsx_response("all_calls.xlsx", get_all_calls())


def get_all_calls():
    "Get all calls."
    result = [r.doc for r in flask.g.db.view("calls", "identifier", include_docs=True)]
    result.sort(key=lambda c: c.get("closes") or "", reverse=True)
    return result


@blueprint.route("/owner/<username>")
@utils.login_required
def owner(username):
    """Calls owned by the given user.
    Includes calls that have not been opened,
    and those with neither opens nor closes dates set.
    """
    if not (
        flask.g.am_admin
        or flask.g.am_staff
        or flask.g.current_user["username"] == username
    ):
        return utils.error("Either of roles 'admin' or 'staff' is required.")

    return flask.render_template(
        "calls/owner.html",
        calls=get_owner_calls(username),
        username=username,
    )


@blueprint.route("/owner/<username>.xlsx")
@utils.login_required
def owner_xlsx(username):
    """Calls owned by the given user in XLSX format.
    Includes calls that have not been opened,
    and those with neither opens nor closes dates set.
    """
    if not (
        flask.g.am_admin
        or flask.g.am_staff
        or flask.g.current_user["username"] == username
    ):
        return utils.error("Either of roles 'admin' or 'staff' is required.")

    return get_calls_xlsx_response(f"{username}_calls.xlsx", get_owner_calls(username))


def get_owner_calls(username):
    result = [
        r.doc
        for r in flask.g.db.view(
            "calls", "owner", key=username, reduce=False, include_docs=True
        )
    ]
    result.sort(key=lambda c: c.get("closes") or "", reverse=True)
    return result


@blueprint.route("/closed")
def closed():
    "Closed calls."
    return flask.render_template(
        "calls/closed.html",
        calls=get_closed_calls(),
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants,
    )


@blueprint.route("/closed_xlsx")
def closed_xlsx():
    "Closed calls in XLSX format."
    return get_calls_xlsx_response("closed_calls.xlsx", get_closed_calls(),
                                   counts=flask.g.am_admin or flask.g.am_staff)


def get_closed_calls():
    "Get all closed calls."
    return [
        r.doc
        for r in flask.g.db.view(
            "calls",
            "closes",
            startkey=utils.get_now(),
            endkey="",
            descending=True,
            include_docs=True,
        )
    ]

@blueprint.route("/open")
def open():
    "Open calls."
    return flask.render_template(
        "calls/open.html",
        calls=get_open_calls(),
        am_owner=anubis.call.am_owner,
        # Function, not value, is passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
    )


@blueprint.route("/open_xlsx")
def open_xlsx():
    "Open calls in XLSX format."
    return get_calls_xlsx_response("open_calls.xlsx", get_open_calls(),
                                   counts=flask.g.am_admin or flask.g.am_staff)


def get_open_calls():
    "Return a list of open calls, sorted according to configuration."
    # It is more computationally efficient to use closes date for first selection.
    result = [
        r.doc
        for r in flask.g.db.view(
            "calls",
            "closes",
            startkey=utils.get_now(),
            endkey="ZZZZZZ",
            include_docs=True,
        )
    ]
    # Exclude not yet open calls.
    result = [call for call in result if anubis.call.is_open(call)]
    order_key = flask.current_app.config["CALL_OPEN_ORDER_KEY"]
    # The possible values are listed in 'constants.CALL_ORDER_KEYS'
    if order_key == "closes":
        result.sort(key=lambda k: (k["closes"], k["title"]))
    elif order_key == "title":
        result.sort(key=lambda k: k["title"])
    elif order_key == "identifier":
        result.sort(key=lambda k: k["identifier"])
    else:
        result.sort(key=lambda k: k["identifier"])
    return result


@blueprint.route("/unpublished")
@utils.staff_required
def unpublished():
    "Unpublished calls; undefined opens and/or closes date, or not yet open."
    return flask.render_template("calls/unpublished.html", calls=get_unpublished_calls())


@blueprint.route("/unpublished.xlsx")
@utils.staff_required
def unpublished_xlsx():
    "XLSX of unpublished calls; undefined opens and/or closes date, or not yet open."
    return get_calls_xlsx_response("unpublished_calls.xlsx", calls=get_unpublished_calls())


def get_unpublished_calls():
    "Get all unpublished calls; undefined opens and/or closes date, or not yet open."
    result = [r.doc for r in flask.g.db.view("calls", "undefined", include_docs=True)]
    result.extend(
        [
            r.doc
            for r in flask.g.db.view(
                "calls",
                "opens",
                startkey=utils.get_now(),
                endkey="ZZZZZZ",
                include_docs=True,
            )
        ]
    )
    result.sort(key=lambda c: c.get("closes") or "", reverse=True)
    return result

@blueprint.route("/reviews")
@utils.staff_required
def reviews():
    "All calls with reviews."
    return flask.render_template(
        "calls/reviews.html",
        calls=get_reviews_calls(),
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants,
    )


@blueprint.route("/reviews_xlsx")
@utils.staff_required
def reviews_xlsx():
    "XLSX for all calls with reviews."
    return get_calls_xlsx_response("reviews_calls.xlsx", calls=get_reviews_calls())


def get_reviews_calls():
    "Get all calls with reviews."
    result = set([r.key for r in flask.g.db.view("reviews", "call", reduce=False)])
    result = [anubis.call.get_call(c) for c in result]
    result.sort(key=lambda c: c.get("closes") or "", reverse=True)
    return result


@blueprint.route("/grants")
@utils.staff_required
def grants():
    "All calls with grants."
    return flask.render_template(
        "calls/grants.html",
        calls=get_grants_calls(),
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants,
    )


@blueprint.route("/grants_xlsx")
@utils.staff_required
def grants_xlsx():
    "XLSX for all calls with grants."
    return get_calls_xlsx_response("grants_calls.xlsx", calls=get_grants_calls())


def get_grants_calls():
    "Get all calls with grants."
    result = set([r.key for r in flask.g.db.view("grants", "call", reduce=False)])
    result = [anubis.call.get_call(c) for c in result]
    result.sort(key=lambda c: c.get("closes") or "", reverse=True)
    return result


def get_calls_xlsx_response(filename, calls, counts=True):
    "Return the XLSX contents as a file attachment response."
    response = flask.make_response(get_calls_xlsx(calls, counts=counts))
    response.headers.set("Content-Type", constants.XLSX_MIMETYPE)
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response
    

def get_calls_xlsx(calls, counts):
    "Return the content of an XLSX file for all closed calls."
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {"in_memory": True})
    formats = utils.create_xlsx_formats(wb)
    ws = wb.add_worksheet("Closed calls")
    ws.freeze_panes(1, 1)
    ws.set_row(0, 60, formats["head"])
    ws.set_column(0, 0, 16, formats["normal"])
    ws.set_column(1, 1, 60, formats["normal"])
    ws.set_column(2, 3, 20, formats["normal"])
    ws.set_column(4, 6, 10, formats["normal"])

    nrow = 0
    row = ["Call",
           "Call title",
           f"Opens\n({flask.current_app.config['TIMEZONE']})",
           f"Closes\n({flask.current_app.config['TIMEZONE']})"]
    if counts:
        row.extend(["# proposals",
                    "# reviews",
                    "# grants"])
    ws.write_row(nrow, 0, row)
    nrow += 1

    for call in calls:
        ncol = 0
        ws.write_url(
            nrow,
            ncol,
            flask.url_for("call.display", cid=call["identifier"], _external=True),
            string=call["identifier"]
        )
        ncol += 1
        ws.write_string(nrow, ncol, call.get("title") or "[No title]")
        ncol += 1
        ws.write_string(nrow, ncol, utils.timezone_from_utc_isoformat(call["opens"], tz=False))
        ncol += 1
        ws.write_string(nrow, ncol, utils.timezone_from_utc_isoformat(call["closes"], tz=False))
        ncol += 1
        if counts:
            ws.write(nrow, ncol, anubis.database.get_count("proposals", "call", call["identifier"]))
            ncol += 1
            ws.write(nrow, ncol, anubis.database.get_count("reviews", "call", call["identifier"]))
            ncol += 1
            ws.write(nrow, ncol, anubis.database.get_count("grants", "call", call["identifier"]))
            ncol += 1
        nrow += 1

    wb.close()
    return output.getvalue()
