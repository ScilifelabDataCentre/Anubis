"Admin pages endpoints."

import json

import flask

from anubis import constants
from anubis import utils

import anubis.config


blueprint = flask.Blueprint("admin", __name__)


@blueprint.route("/site_configuration", methods=["GET", "POST"])
@utils.admin_required
def site_configuration():
    "Display and edit site configuration."
    configuration = flask.g.db["site_configuration"]
    if utils.http_GET():
        return flask.render_template("admin/site_configuration.html",
                                     configuration=configuration)
    elif utils.http_POST():
        try:
            form = flask.request.form
            with utils.MetaSaver(configuration) as saver:
                saver["name"] = form.get("name") or "Anubis"
                saver["description"] = form.get("description") or None
                saver["name_logo_favicon"] = utils.to_bool(form.get("name_logo_favicon"))
                saver["name_logo_menu"] = utils.to_bool(form.get("name_logo_menu"))
                saver["host_name"] = form.get("host_name") or None
                saver["host_url"] = form.get("host_url") or None
                if utils.to_bool(form.get("remove_name_logo")):
                    saver.delete_attachment("name_logo")
                    saver["name_logo_favicon"] = False
                    saver["name_logo_menu"] = False
                infile = flask.request.files.get("name_logo")
                if infile:
                    saver.add_attachment("name_logo", infile.read(), infile.mimetype)
                if utils.to_bool(form.get("remove_host_logo")):
                    saver.delete_attachment("host_logo")
                infile = flask.request.files.get("host_logo")
                if infile:
                    saver.add_attachment("host_logo", infile.read(), infile.mimetype)
        except ValueError as error:
            utils.flash_error(error)
        utils.update_config_from_db()
        return flask.redirect(flask.url_for(".site_configuration"))


@blueprint.route("/user_configuration", methods=["GET", "POST"])
@utils.admin_required
def user_configuration():
    "Display and edit user configuration."
    configuration = flask.g.db["user_configuration"]
    if utils.http_GET():
        return flask.render_template("admin/user_configuration.html",
                                     configuration=configuration)
    elif utils.http_POST():
        try:
            form = flask.request.form
            with utils.MetaSaver(configuration) as saver:
                saver["orcid"] = utils.to_bool(form.get("orcid"))
                saver["genders"] = utils.to_list(form.get("genders") or "")
                saver["birthdate"] = utils.to_bool(form.get("birthdate"))
                saver["degrees"] = utils.to_list(form.get("degrees") or "")
                saver["affiliation"] = utils.to_bool(form.get("affiliation"))
                saver["universities"] = utils.to_list(form.get("universities") or "")
                saver["postaladdress"] = utils.to_bool(form.get("postaladdress"))
                saver["phone"] = utils.to_bool(form.get("phone"))
                if flask.current_app.config.get("MAIL_SERVER"):
                    saver["enable_email_whitelist"] = utils.to_list(form.get("enable_email_whitelist") or "")
        except ValueError as error:
            utils.flash_error(error)
        utils.update_config_from_db()
        return flask.redirect(flask.url_for(".user_configuration"))

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
    for key in anubis.config.DEFAULT_CONFIG:
        config[key] = flask.current_app.config[key]
    for key in ["SECRET_KEY", "COUCHDB_PASSWORD", "MAIL_PASSWORD"]:
        if config[key]:
            config[key] = "<hidden>"
    return flask.render_template("admin/settings.html", items=config.items())
