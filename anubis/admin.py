"Admin pages endpoints."

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
