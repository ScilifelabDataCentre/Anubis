"Various utility functions and classes."

import copy
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
import markdown
import werkzeug.routing

from . import constants


# Global logger instance.
_logger = None
def get_logger():
    global _logger
    if _logger is None:
        config = flask.current_app.config
        _logger = logging.getLogger(config['LOG_NAME'])
        if config['LOG_DEBUG']:
            _logger.setLevel(logging.DEBUG)
        else:
            _logger.setLevel(logging.WARNING)
        if config['LOG_FILEPATH']:
            if config['LOG_ROTATING']:
                loghandler = logging.TimedRotatingFileHandler(
                    config['LOG_FILEPATH'],
                    when='midnight',
                    backupCount=config['LOG_ROTATING'])
            else:
                loghandler = logging.FileHandler(config['LOG_FILEPATH'])
        else:
            loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter(config['LOG_FORMAT']))
        _logger.addHandler(loghandler)
    return _logger

def log_access(response):
    "Record access in the log."
    if not flask.current_app.config['LOG_ACCESS']:
        return response
    if flask.g.current_user:
        username = flask.g.current_user['username']
    else:
        username = None
    get_logger().info(f"{flask.request.remote_addr} {username}"
                      f" {flask.request.method} {flask.request.path}"
                      f" {response.status_code}")
    return response

# Global instance of mail interface.
mail = flask_mail.Mail()

# Decorators for endpoints
def login_required(f):
    "Decorator for checking if logged in. Send to login page if not."
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.current_user:
            url = flask.url_for('user.login', next=flask.request.base_url)
            return flask.redirect(url)
        return f(*args, **kwargs)
    return wrap

def admin_required(f):
    """Decorator for checking if logged in and 'admin' role.
    Otherwise return status 401 Unauthorized.
    """
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        if not flask.g.is_admin:
            flask.abort(http.client.UNAUTHORIZED)
        return f(*args, **kwargs)
    return wrap


class Timer:
    "CPU timer."
    def __init__(self):
        self.start = time.process_time()
    def __call__(self):
        "Return CPU time (in seconds) since start of this timer."
        return time.process_time() - self.start
    @property
    def milliseconds(self):
        "Return CPU time (in milliseconds) since start of this timer."
        return round(1000 * self())

def get_iuid():
    "Return a new IUID, which is a UUID4 pseudo-random string."
    return uuid.uuid4().hex

def to_bool(s):
    "Convert string value into boolean."
    if not s: return False
    s = s.lower()
    return s in ('true', 't', 'yes', 'y')

def is_none(value):
    "Is the value None? For use in templates."
    return value is None

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

def flash_message(msg):
    "Flash information message."
    flask.flash(str(msg), 'message')

def do_markdown(value):
    "Template filter: Use Markdown to process the value."
    value = value or ''
    return jinja2.utils.Markup(markdown.markdown(value, output_format='html5'))

def accept_json():
    "Return True if the header Accept contains the JSON content type."
    acc = flask.request.accept_mimetypes
    best = acc.best_match([constants.JSON_MIMETYPE, constants.HTML_MIMETYPE])
    return best == constants.JSON_MIMETYPE and \
        acc[best] > acc[constants.HTML_MIMETYPE]

def get_json(**data):
    "Return the JSON structure after fixing up for external representation."
    result = {'$id': flask.request.url,
              'timestamp': get_time()}
    try:
        result['iuid'] = data.pop('_id')
    except KeyError:
        pass
    data.pop('_rev', None)
    data.pop('doctype', None)
    result.update(data)
    return result

def jsonify(result, schema_url=None):
    """Return a Response object containing the JSON of 'result'.
    Optionally add a header Link to the schema."""
    response = flask.jsonify(result)
    if schema_url:
        response.headers.add('Link', schema_url, rel='schema')
    return response

def get_dbserver(app=None):
    "Get the connection to the CouchDB database server."
    if app is None:
        app = flask.current_app
    return couchdb2.Server(href=app.config['COUCHDB_URL'],
                           username=app.config['COUCHDB_USERNAME'],
                           password=app.config['COUCHDB_PASSWORD'])

def get_db(dbserver=None, app=None):
    if app is None:
        app = flask.current_app
    if dbserver is None:
        dbserver = get_dbserver(app=app)
    return dbserver[app.config['COUCHDB_DBNAME']]


class BaseSaver:
    "Base document saver context."

    DOCTYPE = None
    HIDDEN_FIELDS = []

    def __init__(self, doc=None):
        if doc is None:
            self.original = {}
            self.doc = {'_id': get_iuid(), 'created': get_time()}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None: return False
        self.finalize()
        self.doc['doctype'] = self.DOCTYPE
        self.doc['modified'] = get_time()
        self.original.pop('tmp', None)
        self.doc.pop('tmp', None)
        flask.g.db.put(self.doc)
        self.add_log()

    def __getitem__(self, key):
        return self.doc[key]

    def __setitem__(self, key, value):
        self.doc[key] = value

    def initialize(self):
        "Initialize the new document."
        pass

    def prepare(self):
        "Preparations before making any changes."
        pass

    def finalize(self):
        "Final operations and checks on the document."
        pass

    def add_log(self):
        """Add a log entry recording the the difference betweens the current and
        the original document, hiding values of specified keys.
        'added': list of keys for items added in the current.
        'updated': dictionary of items updated; original values.
        'removed': dictionary of items removed; original values.
        """
        added = list(set(self.doc).difference(self.original or {}))
        updated = dict([(k, self.original[k])
                        for k in set(self.doc).intersection(self.original or {})
                        if self.doc[k] != self.original[k]])
        removed = dict([(k, self.original[k])
                        for k in set(self.original or {}).difference(self.doc)])
        for key in ['_id', '_rev', 'modified']:
            try:
                added.remove(key)
            except ValueError:
                pass
        updated.pop('_rev', None)
        updated.pop('modified', None)
        for key in self.HIDDEN_FIELDS:
            if key in updated:
                updated[key] = '***'
            if key in removed:
                removed[key] = '***'
        entry = {'_id': get_iuid(),
                 'doctype': constants.DOCTYPE_LOG,
                 'docid': self.doc['_id'],
                 'added': added,
                 'updated': updated,
                 'removed': removed,
                 'timestamp': get_time()}
        if hasattr(flask.g, 'current_user') and flask.g.current_user:
            entry['username'] = flask.g.current_user['username']
        else:
            entry['username'] = None
        if flask.has_request_context():
            entry['remote_addr'] = str(flask.request.remote_addr)
            entry['user_agent'] = str(flask.request.user_agent)
        else:
            entry['remote_addr'] = None
            entry['user_agent'] = None
        flask.g.db.put(entry)

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


