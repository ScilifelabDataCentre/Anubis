"Admin pages endpoints."

import json

import flask

from anubis import constants
from anubis import utils

import anubis.config


blueprint = flask.Blueprint("admin", __name__)


@blueprint.route("/parameters")
@utils.admin_required
def parameters():
    "Display all parameters."
    return flask.render_template("admin/parameters.html", items=sorted(config.items()))


@blueprint.route("/database")
@utils.admin_required
def database():
    "Display CouchDB database information."
    server = utils.get_server()
    identifier = flask.request.args.get("identifier") or None
    return flask.render_template("admin/database.html",
                                 doc=utils.get_document(identifier),
                                 counts=json.dumps(utils.get_counts(), indent=2),
                                 db_info=json.dumps(flask.g.db.get_info(), indent=2),
                                 server_data=json.dumps(server(), indent=2),
                                 databases=", ".join([str(d) for d in server]),
                                 system_stats=json.dumps(server.get_node_system(), indent=2),
                                 node_stats=json.dumps(server.get_node_stats(), indent=2))


@blueprint.route("/document/<identifier>")
@utils.admin_required
def document(identifier):
    try:
        doc = flask.g.db[identifier]
    except couchdb2.NotFoundError:
        return utils.error("No such document.", flask.url_for(".database"))
    response = flask.make_response(doc)
    response.headers.set("Content-Type", constants.JSON_MIMETYPE)
    response.headers.set(
        "Content-Disposition", "attachment", filename=f"{identifier}.json"
    )
    return response


@blueprint.route("/settings")
@utils.admin_required
def settings():
    "Display all configuration settings."
    config = {"ROOT": constants.ROOT}
    for key in anubis.config.DEFAULT_SETTINGS:
        config[key] = flask.current_app.config[key]
    for key in ["SECRET_KEY", "COUCHDB_PASSWORD", "MAIL_PASSWORD"]:
        if config[key]:
            config[key] = "<hidden>"
    return flask.render_template("admin/settings.html", items=config.items())
