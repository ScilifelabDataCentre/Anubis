"Lists of calls."

import flask

import anubis.call
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint("calls", __name__)


@blueprint.route("")
@utils.admin_or_staff_required
def all():
    "Display All calls."
    calls = [r.doc for r in flask.g.db.view("calls", "identifier", include_docs=True)]
    return flask.render_template("calls/all.html", calls=calls)


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

    calls = [
        r.doc
        for r in flask.g.db.view(
            "calls", "owner", key=username, reduce=False, include_docs=True
        )
    ]
    return flask.render_template(
        "calls/owner.html",
        calls=calls,
        username=username,
        allow_create=anubis.call.allow_create(),
    )


@blueprint.route("/closed")
def closed():
    "Closed calls."
    calls = [
        r.doc
        for r in flask.g.db.view(
            "calls",
            "closes",
            startkey="",
            endkey=utils.get_now(),
            include_docs=True,
        )
    ]
    return flask.render_template(
        "calls/closed.html",
        calls=calls,
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants,
    )


@blueprint.route("/open")
def open():
    "Open calls."
    return flask.render_template(
        "calls/open.html",
        calls=get_open_calls(),
        am_owner=anubis.call.am_owner,
        allow_create=anubis.call.allow_create(),
        # Function, not value, is passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
    )


@blueprint.route("/unpublished")
@utils.admin_or_staff_required
def unpublished():
    "Unpublished calls; undefined opens and/or closes date, or not yet open."
    calls = [r.doc for r in flask.g.db.view("calls", "undefined", include_docs=True)]
    calls.extend(
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
    return flask.render_template("calls/unpublished.html", calls=calls)


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


@blueprint.route("/grants")
@utils.admin_or_staff_required
def grants():
    "All calls with grants."
    calls = set([r.key for r in flask.g.db.view("grants", "call", reduce=False)])
    calls = [anubis.call.get_call(c) for c in calls]
    return flask.render_template(
        "calls/grants.html",
        calls=calls,
        # Functions, not values, are passed.
        allow_view_proposals=anubis.call.allow_view_proposals,
        allow_view_reviews=anubis.call.allow_view_reviews,
        allow_view_grants=anubis.call.allow_view_grants,
    )
