"""API endpoints.

Currently only one single fetch endpoint.
"""

import flask

import anubis.calls
from anubis import utils


blueprint = flask.Blueprint("api", __name__)

@blueprint.route("/calls/open")
def calls_open():
    "Return JSON for open calls."
    data = {"$id": flask.request.url,
            "timestamp": utils.get_now(),
            "title": "All open calls."}
    data["calls"] = [get_call_json(c) for c in anubis.calls.get_open_calls()]
    return flask.jsonify(data)

@blueprint.route("/calls/closed")
def calls_closed():
    "Return JSON for closed calls."
    data = {"$id": flask.request.url,
            "timestamp": utils.get_now(),
            "title": "All closed calls."}
    data["calls"] = [get_call_json(c) for c in anubis.calls.get_closed_calls()]
    return flask.jsonify(data)


def get_call_json(call):
    "Return a dictionary for JSON output of a call."
    return {"identifier": call["identifier"],
            "title": call["title"],
            "href": flask.url_for("call.display", cid=call["identifier"], _external=True),
            "opens": call["opens"],
            "closes": call["closes"],
            "description": call["description"],
            "labels": call.get("labels", [])}
