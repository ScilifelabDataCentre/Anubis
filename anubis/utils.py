"Various utility functions and classes."

import datetime
import functools
import http.client
import os.path
import smtplib
import uuid

import couchdb2
import dateutil.parser
import flask
import flask_mail
import jinja2.utils
import marko
import pytz
import werkzeug.routing

from anubis import constants
from anubis.saver import BaseSaver


# Global instance of mail interface.
MAIL = flask_mail.Mail()


def init(app):
    "Initialize: Logging, setup email, add template filters."
    app.logger.info(f"Anubis version {constants.VERSION}")
    app.logger.info(f"settings file: {app.config.get('SETTINGS_FILE')}")
    MAIL.init_app(app)
    app.add_template_filter(display_markdown)
    app.add_template_filter(display_field_value)
    app.add_template_filter(display_value)
    app.add_template_filter(display_datetime_timezone)
    app.add_template_filter(display_boolean)
    app.add_template_filter(user_link)
    app.add_template_filter(call_link)
    app.add_template_filter(call_proposals_link)
    app.add_template_filter(call_reviews_link)
    app.add_template_filter(call_grants_link)
    app.add_template_filter(proposal_link)
    app.add_template_filter(review_link)
    app.add_template_filter(decision_link)
    app.add_template_filter(grant_link)


def load_design_documents(app):
    "Load all CouchDB design documents."
    import anubis.call
    import anubis.proposal
    import anubis.review
    import anubis.decision
    import anubis.grant
    import anubis.user
    import anubis.doc

    db = get_db(app=app)
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
    if app is None:
        app = flask.current_app
    return couchdb2.Server(
        href=app.config["COUCHDB_URL"],
        username=app.config["COUCHDB_USERNAME"],
        password=app.config["COUCHDB_PASSWORD"],
    )


def get_db(app=None):
    "Get a connection to the database."
    if app is None:
        app = flask.current_app
    return get_server(app=app)[app.config["COUCHDB_DBNAME"]]


def update_db(app=None):
    """Update the contents of the database for changes in new version(s).
    - Change all stored datetimes (call opens, closes, reviews_due) to UTC ISO format.
    - Add meta documents for data policy and contact pages.
    """
    db = get_db(app=app)
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
    if "data_policy" not in db:
        try:
            filepath = os.path.normpath(os.path.join(constants.ROOT, "../site", "gdpr.md"))
            with open(filepath) as infile:
                text = infile.read()
        except (OSError, IOError):
            text = None
        with MetaSaver(id="data_policy", db=db) as saver:
            saver["text"] = text
    if "contact" not in db:
        try:
            filepath = os.path.normpath(os.path.join(constants.ROOT, "../site", "contact.md"))
            with open(filepath) as infile:
                text = infile.read()
        except (OSError, IOError):
            text = None
        with MetaSaver(id="contact", db=db) as saver:
            saver["text"] = text
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


def set_db(app=None):
    "Set the database connection and create the document cache."
    flask.g.db = get_db(app=app)
    flask.g.cache = {}  # key: id, value: doc.


def update_config_from_db(app=None):
    "Set configuration values that are stored in the database."
    if app is None:
        app = flask.current_app
    user_configuration = flask.g.db["user_configuration"]
    for key, value in user_configuration.items():
        if key in constants.GENERIC_FIELDS: continue
        if key == "universities":  # Special case
            app.config["UNIVERSITIES"] = value
        else:
            app.config[f"USER_{key.upper()}"] = value
    # Special case: user cannot be enabled immediately if no email server defined.
    if not app.config["MAIL_SERVER"]:
        app.config["USER_ENABLE_EMAIL_WHITELIST"] = []


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


class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."

    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive


def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex


def to_bool(s):
    "Convert string or other value into boolean."
    if isinstance(s, str):
        return s.lower() in ("true", "t", "yes", "y")
    else:
        return bool(s)


def get_time():
    "Current UTC datetime in ISO format (including Z) with millisecond precision."
    now = datetime.datetime.utcnow().isoformat()
    return now[:17] + "{:06.3f}".format(float(now[17:])) + "Z"


def utc_from_timezone_isoformat(dts):
    """Convert the given datetime ISO string in the site timezone to UTC, and 
    output in the same ISO format as in 'get_time' with dummy millisecond precision.
    """
    dt = dateutil.parser.isoparse(dts)
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
    if "_csrf_token" not in flask.session:
        flask.session["_csrf_token"] = get_iuid()
    html = (
        '<input type="hidden" name="_csrf_token" value="%s">'
        % flask.session["_csrf_token"]
    )
    return jinja2.utils.Markup(html)


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


def display_markdown(value):
    "Template filter: Process the value from Markdown to HTML."
    return jinja2.utils.Markup(markdown2html(value))


def display_field_value(field, entity, fid=None, max_length=None, show_user=False):
    """Template filter: Display field value according to its type.
    max_length: Truncate document name to given number of characters.
    show_user: Show user link if email address is an account, and admin or staff.
    """
    import anubis.user

    # Repeated field needs to pass its actual id explicitly.
    if not fid:
        fid = field["identifier"]
    value = entity.get("values", {}).get(fid)
    if field["type"] == constants.LINE:
        return value or "-"
    elif field["type"] == constants.EMAIL:
        if not value:
            return "-"
        if show_user and (flask.g.am_admin or flask.g.am_staff):
            user = anubis.user.get_user(email=value)
            if user:
                return value + " (" + user_link(user) + ")"
        return value
    elif field["type"] == constants.BOOLEAN:
        return display_boolean(value)
    elif field["type"] == constants.SELECT:
        if value is None:
            return "-"
        elif isinstance(value, list):
            return "; ".join(value)
        else:
            return value
    elif field["type"] in (constants.INTEGER, constants.SCORE, constants.RANK):
        if value is None:
            return "-"
        elif isinstance(value, int):
            return "{:,}".format(value)  # Thousands marker.
        else:
            return "?"
    elif field["type"] == constants.FLOAT:
        if value is None:
            return "-"
        elif isinstance(value, (int, float)):
            return "%.2f" % float(value)
        else:
            return "?"
    elif field["type"] == constants.TEXT:
        return display_markdown(value)
    elif field["type"] == constants.DOCUMENT:
        if value:
            if entity["doctype"] == constants.PROPOSAL:
                docurl = flask.url_for(
                    "proposal.document", pid=entity["identifier"], fid=fid
                )
            elif entity["doctype"] == constants.REVIEW:
                docurl = flask.url_for("review.document", iuid=entity["_id"], fid=fid)
            elif entity["doctype"] == constants.DECISION:
                docurl = flask.url_for("decision.document", iuid=entity["_id"], fid=fid)
            elif entity["doctype"] == constants.GRANT:
                docurl = flask.url_for(
                    "grant.document", gid=entity["identifier"], fid=fid
                )
            if max_length:
                if len(value) > max_length:
                    value = value[:max_length] + "..."
            return jinja2.utils.Markup(
                f'<i title="File" class="align-top">{value}</i> <a href="{docurl}"'
                ' role="button" title="Download file"'
                ' class="btn btn-dark btn-sm ml-4">Download</a>'
            )
        else:
            return "-"
    elif field["type"] == constants.REPEAT:
        if value is None:
            return "-"
        else:
            return value
    else:
        raise ValueError(f"unknown field type: {field['type']}")


def display_value(value, default="-"):
    "Template filter: Display the value if not None, else the default."
    if value is None:
        return default
    else:
        return value


def display_datetime_timezone(value, due=False, tz=True, dash=True):
    """Template filter: Convert UTC datetime ISO string to the timezone of the site.
    Optionally output warning for approaching due date, and the timezone.
    """
    if value:
        try:
            dt = dateutil.parser.isoparse(value)
        except ValueError as error:
            return str(error)
        dt = dt.astimezone(pytz.timezone(flask.current_app.config["TIMEZONE"]))
        if tz:
            dts = dt.strftime(f"%Y-%m-%d %H:%M %Z")
        else:
            dts = dt.strftime(f"%Y-%m-%d %H:%M")
        if due:
            remaining = days_remaining(value)
            if remaining > 7:
                return dts
            elif remaining >= 2:
                return jinja2.utils.Markup(
                    f'{dts} <div class="badge badge-warning ml-2">'
                    f"{remaining:.1f} days until due.</div>"
                )
            elif remaining >= 0:
                return jinja2.utils.Markup(
                    f'{dts} <div class="badge badge-danger ml-2">'
                    f"{remaining:.1f} days until due.</div>"
                )
            else:
                return jinja2.utils.Markup(
                    f'{dts} <div class="badge badge-danger ml-2">Overdue!</div>'
                )
        else:
            return dts
    elif dash:
        return "-"
    return ""


def display_boolean(value):
    "Display field value boolean."
    if value is None:
        return "-"
    elif value:
        return "Yes"
    else:
        return "No"


def user_link(user, fullname=True, affiliation=False):
    """Template filter: user by name, with link if allowed to view.
    Optionally output affiliation.
    """
    import anubis.user

    if fullname:
        name = get_fullname(user)
    else:
        name = user["username"]
    if affiliation:
        name += f" [{user.get('affiliation') or '-'}]"
    if anubis.user.allow_view(user):
        url = flask.url_for("user.display", username=user["username"])
        return jinja2.utils.Markup(f'<a href="{url}">{name}</a>')
    else:
        return jinja2.utils.Markup(name)


def call_link(
    call, identifier=True, title=False, proposals_link=True, grants_link=False
):
    """Template filter: Link to call and optionally links to
    all its proposals and grants.
    """
    label = []
    if identifier:
        label.append(call["identifier"])
    if title and call["title"]:
        label.append(call["title"])
    label = " ".join(label) or call["identifier"]
    url = flask.url_for("call.display", cid=call["identifier"])
    html = f'<a href="{url}" class="font-weight-bold">{label}</a>'
    if proposals_link:
        count = get_call_proposals_count(call["identifier"])
        url = flask.url_for("proposals.call", cid=call["identifier"])
        html += (
            f' <a href="{url}" class="badge badge-primary mx-2">{count} proposals</a>'
        )
    if grants_link:
        count = get_count("grants", "call", call["identifier"])
        url = flask.url_for("grants.call", cid=call["identifier"])
        html += f' <a href="{url}" class="badge badge-success mx-2">{count} grants</a>'
    return jinja2.utils.Markup(html)


def call_proposals_link(call, full=False):
    "Template filter: Button with link to the page of all proposals in the call."
    import anubis.call

    if not anubis.call.allow_view_proposals(call):
        return ""
    count = get_count("proposals", "call", call["identifier"])
    url = flask.url_for("proposals.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-primary">{count} {full and "proposals" or "" }</a>'
    return jinja2.utils.Markup(html)


def call_reviews_link(call, full=False):
    "Template filter: Button with link to the page of all reviews in the call."
    import anubis.call

    if not anubis.call.allow_view_reviews(call):
        return ""
    count = get_count("reviews", "call", call["identifier"])
    url = flask.url_for("reviews.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-info">{count} {full and "reviews" or ""}</a>'
    return jinja2.utils.Markup(html)


def call_grants_link(call, full=False):
    "Template filter: Button with link to the page of all grants in the call."
    import anubis.call

    if not anubis.call.allow_view_grants(call):
        return ""
    count = get_count("grants", "call", call["identifier"])
    url = flask.url_for("grants.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-success">{count} {full and "grants" or ""}</a>'
    return jinja2.utils.Markup(html)


def proposal_link(proposal, bold=True):
    "Template filter: link to proposal."
    if not proposal:
        return "-"
    url = flask.url_for("proposal.display", pid=proposal["identifier"])
    title = proposal.get("title") or "[No title]"
    html = f'''<a href="{url}" title="{title}"'''
    if bold:
        html += ' class="font-weight-bold"'
    html += f">{proposal['identifier']} {title}</a>"
    return jinja2.utils.Markup(html)


def review_link(review):
    "Template filter: link to review."
    if not review:
        return "-"
    url = flask.url_for("review.display", iuid=review["_id"])
    html = f"""<a href="{url}" class="font-weight-bold text-info">Review """
    if review.get("archived"):
        html += '<span class="badge badge-pill badge-secondary">Archived</span>'
    elif review.get("finalized"):
        html += '<span class="badge badge-pill badge-success">Finalized</span>'
    else:
        html += '<span class="badge badge-pill badge-warning">Not finalized</span>'
    html += "</a>"
    return jinja2.utils.Markup(html)


def decision_link(decision, small=False):
    "Template filter: link to decision."
    if not decision:
        return "-"
    url = flask.url_for("decision.display", iuid=decision["_id"])
    if decision.get("finalized"):
        if decision.get("verdict"):
            color = "btn-success font-weight-bold"
            label = "Accepted"
        else:
            color = "btn-secondary font-weight-bold"
            label = "Declined"
    else:
        if decision.get("verdict"):
            color = "btn-outline-success font-weight-bold"
            label = "Accepted"
        elif decision.get("verdict") == False:
            color = "btn-outline-secondary font-weight-bold"
            label = "Declined"
        else:
            color = "btn-warning"
            label = "Undecided"
    if small:
        color += " btn-sm"
    else:
        color += " my-1"
    return jinja2.utils.Markup(
        f"""<a href="{url}" role="button" class="btn {color}">""" f"{label}</a>"
    )


def grant_link(grant, small=False, status=False):
    "Template filter: link to grant, optionally with status marker."
    if not grant:
        return "-"
    url = flask.url_for("grant.display", gid=grant["identifier"])
    color = "btn-success font-weight-bold"
    if small:
        color += " btn-sm"
    label = f"Grant {grant['identifier']}"
    if status:
        if grant["errors"]:
            label += ' <span class="badge badge-danger ml-2">Incomplete</span>'
    return jinja2.utils.Markup(
        f'<a href="{url}" role="button"' f' class="btn {color} my-1">{label}</a>'
    )


def get_fullname(user):
    "Return full name of user, or family name, or user name."
    if user.get("familyname"):
        name = user["familyname"]
        if user.get("givenname"):
            return f"{user['givenname']} {name}"
        return name
    return user["username"]


class HtmlRenderer(marko.html_renderer.HTMLRenderer):
    """Extension of HTML renderer to allow setting <a> attribute '_target'
    to '_blank', when the title begins with an exclamation point '!'.
    """

    def render_link(self, element):
        if element.title and element.title.startswith("!"):
            template = '<a target="_blank" href="{}"{}>{}</a>'
            element.title = element.title[1:]
        else:
            template = '<a href="{}"{}>{}</a>'
        title = (
            ' title="{}"'.format(self.escape_html(element.title))
            if element.title
            else ""
        )
        url = self.escape_url(element.dest)
        body = self.render_children(element)
        return template.format(url, title, body)


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
    Raise ValueError if email server not configured.
    Raise KeyError if email could not be sent; server misconfigured.
    """
    if not flask.current_app.config["MAIL_SERVER"]:
        raise ValueError
    if isinstance(recipients, str):
        recipients = [recipients]
    message = flask_mail.Message(
        title, recipients=recipients, reply_to=flask.current_app.config["MAIL_REPLY_TO"]
    )
    message.body = text
    try:
        MAIL.send(message)
    except (ConnectionRefusedError, smtplib.SMTPAuthenticationError) as error:
        app.logger.error(str(error))
        raise KeyError


class MetaSaver(BaseSaver):
    "Meta document saver context handler."

    DOCTYPE = constants.META

    def add_log(self):
        "No log entries for meta documents."
        pass
