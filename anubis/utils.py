"Various utility functions and classes."

import datetime
import functools
import http.client
import smtplib
import uuid

import couchdb2
import dateutil.parser
import flask
import flask_mail
import jinja2
import marko
import markupsafe
import pytz
import xlsxwriter

from anubis import constants


# Global instance of the mail interface.
MAIL = flask_mail.Mail()


def init(app):
    "Initialize the mail interface."
    MAIL.init_app(app)


def send_email(recipients, title, text):
    """Send an email.
    Raise ValueError if the email server is not configured.
    Raise KeyError if email could not be sent; server misconfigured.
    """
    if not flask.current_app.config["MAIL_SERVER"]:
        raise ValueError("No mail server configured.")
    if isinstance(recipients, str):
        recipients = [recipients]
    message = flask_mail.Message(
        title, recipients=recipients, reply_to=flask.current_app.config["MAIL_REPLY_TO"]
    )
    message.body = text
    try:
        MAIL.send(message)
    except (ConnectionRefusedError, smtplib.SMTPAuthenticationError) as error:
        flask.current_app.logger.error(str(error))
        raise KeyError


def get_software():
    "Return a list of tuples with the versions of current software."
    import anubis.database

    return [
        ("Anubis", constants.VERSION, constants.URL),
        ("Python", constants.PYTHON_VERSION, constants.PYTHON_URL),
        ("Flask", flask.__version__, constants.FLASK_URL),
        ("Jinja2", jinja2.__version__, constants.JINJA2_URL),
        ("CouchDB server", anubis.database.get_server().version, constants.COUCHDB_URL),
        ("CouchDB2 interface", couchdb2.__version__, constants.COUCHDB2_URL),
        ("XslxWriter", xlsxwriter.__version__, constants.XLSXWRITER_URL),
        ("Marko", marko.__version__, constants.MARKO_URL),
        ("Bootstrap", constants.BOOTSTRAP_VERSION, constants.BOOTSTRAP_URL),
        ("jQuery", constants.JQUERY_VERSION, constants.JQUERY_URL),
        (
            "jQuery.localtime",
            constants.JQUERY_LOCALTIME_VERSION,
            constants.JQUERY_LOCALTIME_URL,
        ),
        ("DataTables", constants.DATATABLES_VERSION, constants.DATATABLES_URL),
        ("clipboard.js", constants.CLIPBOARD_VERSION, constants.CLIPBOARD_URL),
        ("Feather of Ma'at icon", constants.MAAT_VERSION, constants.MAAT_URL),
    ]


def cache_put(identifier, doc):
    "Store the doc by the given identifier in the cache. Return the doc."
    try:
        flask.g.cache[identifier] = doc
    except AttributeError:
        flask.g.cache = dict(identifier=doc)
    return doc


def cache_get(identifier):
    "Get the document by identifier from the cache. Raise KeyError if not available."
    try:
        return flask.g.cache[identifier]
    except AttributeError:  # No dict implies empty; therefore KeyError.
        flask.g.cache = dict()
        raise KeyError


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


def staff_required(f):
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


def create_xlsx_formats(wb):
    "Create and return the formats to use for the given XLSX workbook."
    return dict(
        head=wb.add_format(
            {
                "bold": True,
                "text_wrap": True,
                "font_size": 14,
                "bg_color": "#9ECA7F",
                "border": 1,
                "align": "center",
            }
        ),
        normal=wb.add_format({"font_size": 14, "align": "left"}),
        wrap=wb.add_format({"font_size": 14, "text_wrap": True, "align": "vjustify"}),
    )


def write_xlsx_field(ws, nrow, ncol, value, field_type, formats):
    """Write a value to the specified cell in the given XLSX worksheet.
    If the field_type is DOCUMENT, then the URL for it must be stored in 'value'.
    """
    if value is None:
        ws.write_string(nrow, ncol, "")
    elif field_type in (constants.LINE, constants.EMAIL):
        ws.write_string(nrow, ncol, value, formats["normal"])
    elif field_type == constants.BOOLEAN:
        ws.write(nrow, ncol, value and "Yes" or "No", formats["normal"])
    elif field_type == constants.SELECT:
        if isinstance(value, list):  # Multiselect
            ws.write(nrow, ncol, "\n".join(value), formats["wrap"])
        else:
            ws.write(nrow, ncol, value, formats["normal"])
    elif field_type == constants.TEXT:
        ws.write_string(nrow, ncol, value, formats["wrap"])
    elif field_type == constants.DOCUMENT:
        ws.write_url(nrow, ncol, value, string="Download file")
    else:
        ws.write(nrow, ncol, value)


def get_now():
    "Current UTC datetime in ISO format (including Z) with millisecond precision."
    now = datetime.datetime.utcnow().isoformat()
    return now[:17] + "{:06.3f}".format(float(now[17:])) + "Z"


def timezone_from_utc_isoformat(dts, tz=True):
    "Convert the given datetime ISO string in UTC to the configured timezone."
    if not dts:
        return ""
    try:
        dt = dateutil.parser.isoparse(dts)
    except ValueError as error:
        raise ValueError(f"Invalid datetime '{dts}': {error}")
    dt = dt.astimezone(pytz.timezone(flask.current_app.config["TIMEZONE"]))
    if tz:
        return dt.strftime(f"%Y-%m-%d %H:%M {flask.current_app.config['TIMEZONE']}")
    else:
        return dt.strftime("%Y-%m-%d %H:%M")


def utc_from_timezone_isoformat(dts):
    """Convert the given datetime ISO string in the the set timezone to UTC, and
    output in the same ISO format as in 'get_now' with dummy millisecond precision.
    """
    try:
        dt = dateutil.parser.isoparse(dts)
    except ValueError as error:
        raise ValueError(f"Invalid datetime '{dts}': {error}")
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


def error(message, url=None):
    """Flash the given error message, and return a redirect response
    to the home page, or the given URL.
    """
    flash_error(message)
    if url:
        return flask.redirect(url)
    return flask.redirect(flask.url_for("home"))


def flash_error(msg):
    "Flash error message."
    flask.flash(str(msg), "error")


def flash_warning(msg):
    "Flash warning message."
    flask.flash(str(msg), "warning")


def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), "message")


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
        return template.format(
            url=self.escape_url(element.dest),
            title=title,
            body=self.render_children(element),
        )

    def render_heading(self, element):
        "Add id to all headings."
        id = self.get_text_only(element).replace(" ", "-").lower()
        id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
        return '<h{level} id="{id}">{children}</h{level}>\n'.format(
            level=element.level, id=id, children=self.render_children(element)
        )

    def get_text_only(self, element):
        "Helper function to extract only the text from element and its children."
        if isinstance(element.children, str):
            return element.children
        else:
            return "".join([self.get_text_only(el) for el in element.children])
