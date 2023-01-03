"Various utility functions and classes."

import datetime
import functools
import http.client
import mimetypes
import os.path
import smtplib
import uuid

import couchdb2
import dateutil.parser
import flask
import marko
import markupsafe
import pytz

from anubis import constants
from anubis.saver import Saver


class MetaSaver(Saver):
    "Meta document saver context handler."

    DOCTYPE = constants.META

    def add_log(self):
        "No log entries for meta documents."
        pass


def load_design_documents():
    "Load all CouchDB design documents."
    import anubis.call
    import anubis.proposal
    import anubis.review
    import anubis.decision
    import anubis.grant
    import anubis.user
    import anubis.doc

    app = flask.current_app
    db = get_db()

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


def get_server(app=None):
    "Get a connection to the CouchDB server."
    if app is None:
        app = flask.current_app
    return couchdb2.Server(
        href=app.config["COUCHDB_URL"],
        username=app.config["COUCHDB_USERNAME"],
        password=app.config["COUCHDB_PASSWORD"],
    )

def get_db():
    "Get a connection to the database."
    return get_server()[flask.current_app.config["COUCHDB_DBNAME"]]


def set_db():
    "Set the database connection and create the document cache."
    flask.g.db = get_db()
    flask.g.cache = {}  # key: id, value: doc.


def update_db(db):
    "Update the contents of the database for changes in new version(s)."
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


def get_counts():
    "Get counts of some entities in the database."
    result = {}
    for key, design, view in [("n_calls", "calls", "owner"),
                              ("n_users", "users", "username"),
                              ("n_proposals", "proposals", "call"),
                              ("n_reviews", "reviews", "call"),
                              ("n_grants", "grants", "call")]:
        try:
            result[key] = list(flask.g.db.view(design, view, reduce=True))[0].value
        except IndexError:
            result[key] = 0
    return result

def get_call_proposals_count(cid):
    "Get the count for all proposals in the given call."
    return get_count("proposals", "call", cid)


def get_call_reviewer_reviews_count(cid, username, archived=False):
    "Get the count of all reviews for the reviewer in the given call."
    if archived:
        return get_count("reviews", "call_reviewer_archived", [cid, username])
    else:
        return get_count("reviews", "call_reviewer", [cid, username])


def get_proposal_reviews_count(pid, archived=False):
    """Get the count of all reviews for the given proposal.
    Optionally for archived reviews.
    """
    if archived:
        return get_count("reviews", "proposal_archived", pid)
    else:
        return get_count("reviews", "proposal", pid)


def get_user_grants_count(username):
    """Return the number of grants for the user,
    including those she has access to.
    """
    return get_count("grants", "user", username) + get_count(
        "grants", "access", username
    )


def get_docs_view(designname, viewname, key):
    "Get the documents from the view. Add them to the cache."
    result = [
        r.doc for r in flask.g.db.view(designname, viewname, key=key, include_docs=True)
    ]
    for doc in result:
        if doc.get("doctype") == constants.CALL:
            flask.g.cache[f"call {doc['identifier']}"] = doc
        elif doc.get("doctype") == constants.PROPOSAL:
            flask.g.cache[f"proposal {doc['identifier']}"] = doc
        elif doc.get("doctype") == constants.REVIEW:
            flask.g.cache[f"review {doc['_id']}"] = doc
        elif doc.get("doctype") == constants.DECISION:
            flask.g.cache[f"decision {doc['_id']}"] = doc
        elif doc.get("doctype") == constants.GRANT:
            flask.g.cache[f"grant {doc['identifier']}"] = doc
        elif doc.get("doctype") == constants.USER:
            flask.g.cache[f"username {doc['username']}"] = doc
            if doc["email"]:
                flask.g.cache[f"email {doc['email']}"] = doc
    return result


def get_document(identifier):
    """Get the database document by identifier, else None.
    The identifier may be an account email, account API key, file name, info name,
    order identifier, or '_id' of the CouchDB document.
    """
    if not identifier:          # If empty string, database info is returned.
        return None
    for designname, viewname in [
            ("users", "username"),
            ("users", "email"),
            ("users", "orcid"),
            ("calls", "identifier"),
            ("proposals", "identifier"),
            ("grants", "identifier"),
    ]:
        try:
            view = flask.g.db.view(
                designname, viewname, key=identifier, reduce=False, include_docs=True
            )
            result = list(view)
            if len(result) == 1:
                return result[0].doc
        except KeyError:
            pass
    try:
        return flask.g.db[identifier]
    except couchdb2.NotFoundError:
        return None

def login_required(f):
    """Resource endpoint decorator for checking if logged in.
    Forward to login page if not, recording the origin URL.
    """

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.current_user:
            flask.session["login_target_url"] = flask.request.base_url
            return flask.redirect(flask.url_for("user.login"))
        return f(*args, **kwargs)

    return wrap


def admin_required(f):
    """Resource endpoint decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.am_admin:
            return error("Role 'admin' is required.")
        return f(*args, **kwargs)

    return wrap


def admin_or_staff_required(f):
    """Resource endpoint decorator for checking if logged in and 'admin'
    or 'staff' role.
    """

    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not (flask.g.am_admin or flask.g.am_staff):
            return error("Either of roles 'admin' or 'staff' is required.")
        return f(*args, **kwargs)

    return wrap


def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex


def to_bool(s):
    "Convert string or other value into boolean."
    if isinstance(s, str):
        return s.lower() in ("true", "t", "yes", "y")
    else:
        return bool(s)

def to_list(value):
    "Convert string value to list: one item per line, excluding empty lines."
    values = [s.strip() for s in value.split("\n")]
    return [s for s in values if s]

def get_time():
    "Current UTC datetime in ISO format (including Z) with millisecond precision."
    now = datetime.datetime.utcnow().isoformat()
    return now[:17] + "{:06.3f}".format(float(now[17:])) + "Z"


def timezone_from_utc_isoformat(dts, tz=True):
    "Convert the given datetime ISO string in UTC to the local timezone."
    try:
        dt = dateutil.parser.isoparse(dts)
    except ValueError as error:
        return str(error)
    dt = dt.astimezone(pytz.timezone(flask.current_app.config["TIMEZONE"]))
    if tz:
        return dt.strftime(f"%Y-%m-%d %H:%M %Z")
    else:
        return dt.strftime(f"%Y-%m-%d %H:%M")


def utc_from_timezone_isoformat(dts):
    """Convert the given datetime ISO string in the site timezone to UTC, and 
    output in the same ISO format as in 'get_time' with dummy millisecond precision.
    """
    try:
        dt = dateutil.parser.isoparse(dts)
    except ValueError as error:
        return str(error)
    dt = pytz.timezone(flask.current_app.config["TIMEZONE"]).localize(dt)
    dt = dt.astimezone(pytz.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def days_remaining(dts):
    "Return the number of days remaining for the given UTC datetime ISO format string."
    dt = dateutil.parser.isoparse(dts)
    remaining = dt - datetime.datetime.now(datetime.timezone.utc)
    return remaining.total_seconds() / (24 * 3600.0)


def http_GET():
    "Is the HTTP method GET?"
    return flask.request.method == "GET"


def http_POST(csrf=True):
    "Is the HTTP method POST? Check whether used for method tunneling."
    if flask.request.method != "POST":
        return False
    if flask.request.form.get("_http_method") in (None, "POST"):
        if csrf:
            check_csrf_token()
        return True
    else:
        return False


def http_PUT():
    "Is the HTTP method PUT? Is not tunneled."
    return flask.request.method == "PUT"


def http_DELETE(csrf=True):
    "Is the HTTP method DELETE? Check for method tunneling."
    if flask.request.method == "DELETE":
        return True
    if flask.request.method == "POST":
        if csrf:
            check_csrf_token()
        return flask.request.form.get("_http_method") == "DELETE"
    else:
        return False


def csrf_token():
    "Output HTML for cross-site request forgery (CSRF) protection."
    # Generate a token to last the session's lifetime.
    try:
        token = flask.session["_csrf_token"]
    except KeyError:
        flask.session["_csrf_token"] = token = get_iuid()
    html = f'<input type="hidden" name="_csrf_token" value="{token}">'
    return markupsafe.Markup(html)


def check_csrf_token():
    "Check the CSRF token for POST HTML."
    # Do not use up the token; keep it for the session's lifetime.
    token = flask.session.get("_csrf_token", None)
    if not token or token != flask.request.form.get("_csrf_token"):
        flask.abort(http.client.BAD_REQUEST)


def error(message, url=None, home=False):
    """Return redirect response to the given URL, or referrer, or home page.
    Flash the given message.
    """
    flash_error(message)
    if url:
        return flask.redirect(url)
    elif home:
        return flask.redirect(flask.url_for("home"))
    else:
        return flask.redirect(url or referrer_or_home())


def referrer_or_home():
    "Return the URL for the referring page 'referer' or the home page."
    return flask.request.headers.get("referer") or flask.url_for("home")


def flash_error(msg):
    "Flash error message."
    flask.flash(str(msg), "error")


def flash_warning(msg):
    "Flash warning message."
    flask.flash(str(msg), "warning")


def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), "message")


def get_banner_fields(fields):
    "Return fields flagged as banner fields. Avoid repeated fields."
    return [f for f in fields if f.get("banner") and not f.get("repeat")]


def markdown2html(value):
    "Process the value from Markdown to HTML."
    return marko.Markdown(renderer=HtmlRenderer).convert(value or "")


class HtmlRenderer(marko.html_renderer.HTMLRenderer):
    "Extension of Marko Markdown-to-HTML renderer."

    def render_link(self, element):
        """Allow setting <a> attribute '_target' to '_blank', when the title
        begins with an exclamation point '!'.
        """
        if element.title and element.title.startswith("!"):
            template = '<a target="_blank" href="{url}"{title}>{body}</a>'
            element.title = element.title[1:]
        else:
            template = '<a href="{url}"{title}>{body}</a>'
        title = (
            ' title="{}"'.format(self.escape_html(element.title))
            if element.title
            else ""
        )
        return template.format(url=self.escape_url(element.dest),
                               title=title,
                               body=self.render_children(element))

    def render_heading(self, element):
        "Add id to all headings."
        id = self.get_text_only(element).replace(" ", "-").lower()
        id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
        return '<h{level}><a id="{id}">{children}</a></h{level}>\n'.format(
            level=element.level, id=id, children=self.render_children(element)
        )

    def get_text_only(self, element):
        "Helper function to extract only the text from element and its children."
        if isinstance(element.children, str):
            return element.children
        else:
            return "".join([self.get_text_only(el) for el in element.children])


def get_logs(docid, cleanup=True):
    """Return the list of log entries for the given document identifier,
    sorted by reverse timestamp.
    """
    result = [
        r.doc
        for r in flask.g.db.view(
            "logs",
            "doc",
            startkey=[docid, "ZZZZZZ"],
            endkey=[docid],
            descending=True,
            include_docs=True,
        )
    ]
    # Remove irrelevant entries, if requested.
    if cleanup:
        for log in result:
            for key in ["_id", "_rev", "doctype", "docid"]:
                log.pop(key)
    return result


def delete(doc):
    """Delete the given document and all its log entries.
    NOTE: This was done by 'purge' before. This new implementation
    should be faster, but leaves the deleted documents in CouchDB.
    These are removed whenever a database compaction is done.
    """
    for log in get_logs(doc["_id"], cleanup=False):
        flask.g.db.delete(log)
    flask.g.db.delete(doc)


def send_email(recipients, title, text):
    """Send an email.
    Raise ValueError if the email server is not configured.
    Raise KeyError if email could not be sent; server misconfigured.
    """
    import anubis
    if not flask.current_app.config["MAIL_SERVER"]:
        raise ValueError
    if isinstance(recipients, str):
        recipients = [recipients]
    message = flask_mail.Message(
        title, recipients=recipients, reply_to=flask.current_app.config["MAIL_REPLY_TO"]
    )
    message.body = text
    try:
        anubis.mail.send(message)
    except (ConnectionRefusedError, smtplib.SMTPAuthenticationError) as error:
        app.logger.error(str(error))
        raise KeyError
