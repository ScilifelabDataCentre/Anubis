"CouchDB operations."

import couchdb2
import flask

from anubis import constants
from anubis.saver import Saver


LOG_DESIGN_DOC = {
    "views": {
        "doc": {
            "map": "function (doc) {if (doc.doctype !== 'log') return; emit([doc.docid, doc.timestamp], null);}"
        }
    }
}

META_DESIGN_DOC = {
    "views": {
        "doc": {
            "map": "function (doc) {if (doc.doctype !== 'meta') return; emit(doc.docid, null);}"
        }
    }
}


class MetaSaver(Saver):
    "Meta document saver context handler."

    DOCTYPE = constants.META

    def add_log(self):
        "No log entries for meta documents."
        pass


def get_server():
    "Get a connection to the CouchDB server."
    return couchdb2.Server(
        href=flask.current_app.config["COUCHDB_URL"],
        username=flask.current_app.config["COUCHDB_USERNAME"],
        password=flask.current_app.config["COUCHDB_PASSWORD"],
    )

def get_db():
    "Get a connection to the database."
    return get_server()[flask.current_app.config["COUCHDB_DBNAME"]]


def update_design_documents():
    "Ensure that all CouchDB design documents are up to date."
    import anubis.call
    import anubis.proposal
    import anubis.review
    import anubis.decision
    import anubis.grant
    import anubis.user

    db = get_db()
    app = flask.current_app

    if db.put_design("calls", anubis.call.DESIGN_DOC):
        app.logger.info("Updated calls design document.")
    if db.put_design("proposals", anubis.proposal.DESIGN_DOC):
        app.logger.info("Updated proposals design document.")
    if db.put_design("reviews", anubis.review.DESIGN_DOC):
        app.logger.info("Updated reviews design document.")
    if db.put_design("decisions", anubis.decision.DESIGN_DOC):
        app.logger.info("Updated decisions design document.")
    if db.put_design("grants", anubis.grant.DESIGN_DOC):
        app.logger.info("Updated grants design document.")
    if db.put_design("users", anubis.user.DESIGN_DOC):
        app.logger.info("Updated users design document.")
    if db.put_design("logs", LOG_DESIGN_DOC):
        app.logger.info("Updated logs design document.")
    if db.put_design("meta", META_DESIGN_DOC):
        app.logger.info("Updated meta design document.")


def get_count(designname, viewname, key=None):
    "Get the count for the given view and key."
    if key is None:
        result = flask.g.db.view(designname, viewname, reduce=True)
    else:
        result = flask.g.db.view(designname, viewname, key=key, reduce=True)
    if result:
        return result[0].value
    else:
        return 0


def update():
    "Update the contents of the database for changes in new version(s)."
    db = get_db()
    app = flask.current_app

    # Change all stored datetimes (call opens, closes, reviews_due) to UTC ISO format.
    calls = [row.doc for row in db.view("calls", "identifier", include_docs=True)]
    for call in calls:
        changed = False
        for key in ["opens", "closes", "reviews_due"]:
            try:
                value = call[key]
                if not value: raise KeyError
            except KeyError:
                pass
            else:
                if "Z" not in value: # Not in UTC; then it is in TIMEZONE.
                    changed = True
                    call[key] = utc_from_timezone_isoformat(value)
        if changed:
            app.logger.info(f"Updated call {call['identifier']} document.")
            db.put(call)

    # Add a meta document for 'data_policy' text.
    if "data_policy" not in db:
        try:
            filepath = os.path.normpath(os.path.join(constants.ROOT, "../site", "gdpr.md"))
            with open(filepath) as infile:
                text = infile.read()
        except OSError:
            text = None
        with MetaSaver(id="data_policy", db=db) as saver:
            saver["text"] = text

    # Add a meta document for 'contact' text.
    if "contact" not in db:
        try:
            filepath = os.path.normpath(os.path.join(constants.ROOT, "../site", "contact.md"))
            with open(filepath) as infile:
                text = infile.read()
        except OSError:
            text = None
        with MetaSaver(id="contact", db=db) as saver:
            saver["text"] = text

    # Add a meta document for site configuration.
    if "site_configuration" not in db:
        with MetaSaver(id="site_configuration", db=db) as saver:
            saver["name"] = app.config.get("SITE_NAME") or "Anubis"
            saver["description"] = app.config.get("SITE_DESCRIPTION") or "Submit proposals for grants in open calls."
            saver["host_name"] = app.config.get("HOST_NAME")
            saver["host_url"] = app.config.get("HOST_URL")
            if app.config.get("SITE_STATIC_DIR"):
                dirpath = app.config.get("SITE_STATIC_DIR")
            else:
                dirpath = os.path.normpath(os.path.join(constants.ROOT, "../site/static"))
            # Attach the site name logo file, if any.
            if app.config.get("SITE_LOGO"):
                path = os.path.join(dirpath, app.config["SITE_LOGO"])
                mimetype = mimetypes.guess_type(path)[0]
                try:
                    with open(path, "rb") as infile:
                        data = infile.read()
                    saver.add_attachment("name_logo", data, mimetype)
                except OSError:
                    pass
            # Attach the host logo file, if any.
            if app.config.get("HOST_LOGO"):
                path = os.path.join(dirpath, app.config["HOST_LOGO"])
                mimetype = mimetypes.guess_type(path)[0]
                try:
                    with open(path, "rb") as infile:
                        data = infile.read()
                    saver.add_attachment("host_logo", data, mimetype)
                except OSError:
                    pass

    # Add a meta document for user account configurations.
    if "user_configuration" not in db:
        with MetaSaver(id="user_configuration", db=db) as saver:
            saver["orcid"] = to_bool(app.config.get("USER_ORCID", True))
            saver["genders"] = app.config.get("USER_GENDERS") or ["Male", "Female", "Other"]
            saver["birthdate"] = to_bool(app.config.get("USER_BIRTHDATE", True))
            saver["degrees"] = app.config.get("USER_DEGREES") or ["Mr/Ms", "MSc", "MD", "PhD", "Assoc Prof", "Prof", "Other"]
            saver["affiliation"] = to_bool(app.config.get("USER_AFFILIATION", True))
            saver["universities"] = app.config.get("UNIVERSITIES") or []
            # Badly chosen key, but have to keep it...
            saver["postaladdress"] = to_bool(app.config.get("USER_POSTALADDRESS", False))
            saver["phone"] = to_bool(app.config.get("USER_PHONE", True))
            saver["enable_email_whitelist"] = app.config.get("USER_ENABLE_EMAIL_WHITELIST") or []
