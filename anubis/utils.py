"Various utility functions and classes."

import datetime
import functools
import http.client
import logging
import time
import uuid

import couchdb2
import flask
import flask_mail
import jinja2.utils
import markdown as markdown_module
import werkzeug.routing

from . import constants

def init(app):
    """Initialize.
    - Add template filters.
    - Update CouchDB design documents.
    """
    app.add_template_filter(markdown)
    app.add_template_filter(typed_value)
    app.add_template_filter(datetimetz)
    app.add_template_filter(due)
    app.add_template_filter(boolean_value)

    db = get_db(app=app)
    if db.put_design('logs', DESIGN_DOC):
        app.logger.info('Updated logs design document.')

DESIGN_DOC = {
    'views': {
        'doc': {'map': "function (doc) {if (doc.doctype !== 'log') return; emit([doc.docid, doc.timestamp], null);}"}
    }
}

def get_db(app=None):
    "Get a connection to the database."
    if app is None:
        app = flask.current_app
    server = couchdb2.Server(href=app.config['COUCHDB_URL'],
                             username=app.config['COUCHDB_USERNAME'],
                             password=app.config['COUCHDB_PASSWORD'])
    return server[app.config['COUCHDB_DBNAME']]

def get_count(designname, viewname, key):
    "Get the count for the given view and key."
    result = flask.g.db.view(designname, viewname, key=key, reduce=True)
    if result:
        return result[0].value
    else:
        return 0

def get_call_proposals_count(cid):
    "Get the count for all proposals in the given call."
    return get_count('proposals', 'call', cid)

def get_call_reviews_count(cid):
    "Get the count of all reviews in the given call."
    return get_count('reviews', 'call', cid)

def get_proposal_reviews_count(pid):
    "Get the count of all reviews for the given proposal."
    return get_count('reviews', 'proposal', pid)

def get_call_reviewer_reviews_count(cid, username):
    "Get the count of all reviews for the reviewer in the given call."
    return get_count('reviews', 'call_reviewer', [cid, username])

# Global instance of mail interface.
mail = flask_mail.Mail()

def login_required(f):
    """Resource endpoint decorator for checking if logged in.
    Send to login page if not.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.current_user:
            url = flask.url_for('user.login', next=flask.request.base_url)
            return flask.redirect(url)
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    """Resource endpoint decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.am_admin:
            flask.abort(http.client.UNAUTHORIZED)
        return f(*args, **kwargs)
    return wrap

def referrer_or_home():
    "Return the URL for the referring page 'referer' or the home page."
    return flask.request.headers.get('referer') or flask.url_for('home')    

class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."
    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()    # Case-insensitive

def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex

def to_bool(s):
    "Convert string value into boolean."
    if not s: return False
    s = s.lower()
    return s in ('true', 't', 'yes', 'y')

def get_time(offset=None):
    """Current date and time (UTC) in ISO format, with millisecond precision.
    Add the specified offset in seconds, if given.
    """
    instant = datetime.datetime.utcnow()
    if offset:
        instant += datetime.timedelta(seconds=offset)
    instant = instant.isoformat()
    return instant[:17] + "{:06.3f}".format(float(instant[17:])) + "Z"

def normalized_local_now():
    "Return the current local date and time in normalized form."
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

def normalize_datetime(dt=None):
    "Normalize date and time to format 'YYYY-MM-DD HH:MM'."
    if dt:
        dt = dt.strip()
    if dt:
        try:
            dt = ' '.join(dt.split())
            dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                dt = datetime.datetime.strptime(dt, '%Y-%m-%d')
            except ValueError:
                raise ValueError('invalid date or datetime')
        return dt.strftime('%Y-%m-%d %H:%M')
    else:
        return None

def days_remaining(dt):
    "Return the number of days remaining for the given local datetime string."
    dt = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M')
    remaining = dt - datetime.datetime.now()
    return remaining.total_seconds() / (24* 3600.0)

def url_for(endpoint, **values):
    "Same as 'flask.url_for', but with '_external' set to True."
    return flask.url_for(endpoint, _external=True, **values)

def http_GET():
    "Is the HTTP method GET?"
    return flask.request.method == 'GET'

def http_POST(csrf=True):
    "Is the HTTP method POST? Check whether used for method tunneling."
    if flask.request.method != 'POST': return False
    if flask.request.form.get('_http_method') in (None, 'POST'):
        if csrf: check_csrf_token()
        return True
    else:
        return False

def http_PUT():
    "Is the HTTP method PUT? Is not tunneled."
    return flask.request.method == 'PUT'

def http_DELETE(csrf=True):
    "Is the HTTP method DELETE? Check for method tunneling."
    if flask.request.method == 'DELETE': return True
    if flask.request.method == 'POST':
        if csrf: check_csrf_token()
        return flask.request.form.get('_http_method') == 'DELETE'
    else:
        return False

def csrf_token():
    "Output HTML for cross-site request forgery (CSRF) protection."
    # Generate a token to last the session's lifetime.
    if '_csrf_token' not in flask.session:
        flask.session['_csrf_token'] = get_iuid()
    html = '<input type="hidden" name="_csrf_token" value="%s">' % \
           flask.session['_csrf_token']
    return jinja2.utils.Markup(html)

def check_csrf_token():
    "Check the CSRF token for POST HTML."
    # Do not use up the token; keep it for the session's lifetime.
    token = flask.session.get('_csrf_token', None)
    if not token or token != flask.request.form.get('_csrf_token'):
        flask.abort(http.client.BAD_REQUEST)

def flash_error(msg):
    "Flash error message."
    flask.flash(str(msg), 'error')

def flash_warning(msg):
    "Flash warning message."
    flask.flash(str(msg), 'warning')

def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), 'message')

def typed_value(value, type, docurl=None):
    "Template filter: Output field value according to its type."
    if type == constants.LINE:
        return value or '-'
    if type == constants.BOOLEAN:
        return boolean_value(value)
    elif type == constants.SELECT:
        return select_value(value)
    elif type in (constants.INTEGER, constants.SCORE):
        return integer_value(value)
    elif type == constants.FLOAT:
        return float_value(value)
    elif type == constants.TEXT:
        return markdown(value)
    elif type == constants.DOCUMENT:
        if value:
            return jinja2.utils.Markup(
                f"""File <i>{value}</i> <a href="{docurl}" role="button" class="btn btn-outline-secondary btn-sm ml-4">Download</a>""")
        else:
            return '-'
    else:
        return value

def datetimetz(value):
    "Template filter: datetime with server local timezone."
    if value:
        return f"{value} {time.tzname[0]}"
    else:
        return '-'

def due(value):
    "Template filter: output 'due' text depending on server time."
    if not value: return ''
    remaining = days_remaining(value)
    if remaining > 7:
        return ''
    elif remaining >= 2:
        return jinja2.utils.Markup('<span class="bg-warning px-2">'
                                   f'{remaining:.1f} days until due.</span>')
    elif remaining >= 0:
        return jinja2.utils.Markup('<span class="bg-danger text-white px-2">'
                                   f'{remaining:.1f} days until due.</span>')
    else:
        return jinja2.utils.Markup('<span class="font-weight-bold bg-danger'
                                   ' text-white px-2">Overdue!</span>')

def boolean_value(value):
    "Output field value boolean."
    if value is None:
        return '-'
    elif value:
        return 'Yes'
    else:
        return 'No'

def select_value(value):
    "Output field value(s) for select."
    if value is None:
        return '-'
    elif isinstance(value, list):
        return '; '.join(value)
    else:
        return value

def integer_value(value):
    "Output field value integer."
    if value is None:
        return '-'
    elif isinstance(value, int):
        return '{:,}'.format(value)
    else:
        return '?'

def float_value(value):
    "Output field value float."
    if value is None:
        return '-'
    elif isinstance(value, (int, float)):
        return '%.2f' % float(value)
    else:
        return '?'

def markdown(value):
    "Process the value using Markdown."
    value = value or ''
    return jinja2.utils.Markup(markdown_module.markdown(value,
                                                        output_format='html5'))

def get_logs(docid, cleanup=True):
    """Return the list of log entries for the given document identifier,
    sorted by reverse timestamp.
    """
    result = [r.doc for r in flask.g.db.view('logs', 'doc',
                                             startkey=[docid, 'ZZZZZZ'],
                                             endkey=[docid],
                                             descending=True,
                                             include_docs=True)]
    # Remove irrelevant entries, if requested.
    if cleanup:
        for log in result:
            for key in ['_id', '_rev', 'doctype', 'docid']:
                log.pop(key)
    return result

def delete(doc):
    "Delete the given document and all its log entries."
    logs = get_logs(doc['_id'], cleanup=False)
    if logs:
        flask.g.db.purge(logs)
    flask.g.db.purge([doc])
