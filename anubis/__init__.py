"Anubis: System to handle calls, proposals, reviews, decisions, grants."

import os.path
import re
import string
import sys

__version__ = "2.8.4"


class Constants:
    def __setattr__(self, key, value):
        raise ValueError("cannot set constant")

    VERSION = __version__
    URL = "https://github.com/pekrau/Anubis"
    ROOT = os.path.dirname(os.path.abspath(__file__))

    PYTHON_VERSION = ".".join([str(i) for i in sys.version_info[0:3]])
    PYTHON_URL = "https://www.python.org/"

    FLASK_URL = "https://pypi.org/project/Flask/"
    JINJA2_URL = "https://pypi.org/project/Jinja2/"
    COUCHDB_URL = "https://couchdb.apache.org/"
    COUCHDB2_URL = "https://pypi.org/project/couchdb2"
    XLSXWRITER_URL = "https://pypi.org/project/XlsxWriter/"
    MARKO_URL = "https://pypi.org/project/marko/"

    BOOTSTRAP_VERSION = "4.6.1"
    BOOTSTRAP_URL = "https://getbootstrap.com/docs/4.6/getting-started/introduction/"
    BOOTSTRAP_CSS_URL = (
        "https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/css/bootstrap.min.css"
    )
    BOOTSTRAP_CSS_INTEGRITY = (
        "sha384-zCbKRCUGaJDkqS1kPbPd7TveP5iyJE0EjAuZQTgFLD2ylzuqKfdKlfG/eSrtxUkn"
    )
    BOOTSTRAP_JS_URL = (
        "https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/js/bootstrap.bundle.min.js"
    )
    BOOTSTRAP_JS_INTEGRITY = (
        "sha384-fQybjgWLrvvRgtW6bFlB7jaZrFsaBXjsOMm/tB9LTS58ONXgqbR9W8oWht/amnpF"
    )

    JQUERY_VERSION = "3.5.1"
    JQUERY_URL = "https://jquery.com/"
    JQUERY_JS_URL = "https://code.jquery.com/jquery-3.5.1.slim.min.js"
    JQUERY_JS_INTEGRITY = (
        "sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj"
    )

    JQUERY_LOCALTIME_URL = "https://plugins.jquery.com/jquery.localtime/"
    JQUERY_LOCALTIME_VERSION = "0.9.1"
    JQUERY_LOCALTIME_FILENAME = "jquery.localtime-0.9.1.min.js"

    DATATABLES_VERSION = "1.10.24"
    DATATABLES_URL = "https://datatables.net/"
    DATATABLES_CSS_URL = (
        "https://cdn.datatables.net/1.10.24/css/dataTables.bootstrap4.min.css"
    )
    DATATABLES_JQUERY_JS_URL = (
        "https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"
    )
    DATATABLES_BOOTSTRAP_JS_URL = (
        "https://cdn.datatables.net/1.10.24/js/dataTables.bootstrap4.min.js"
    )

    MARKDOWN_URL = "https://www.markdownguide.org/basic-syntax/"

    CLIPBOARD_URL = "https://clipboardjs.com/"
    CLIPBOARD_VERSION = "2.0.6"
    CLIPBOARD_FILENAME = "clipboard.min.js"

    MAAT_URL = "https://www.flaticon.com/authors/freepik"
    MAAT_VERSION = "-"

    LOGGING_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

    ID_RX = re.compile(r"^[a-z][a-z0-9_]*$", re.I)
    IUID_RX = re.compile(r"^[a-f0-9]{32,32}$", re.I)
    EMAIL_RX = re.compile(r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$")

    # CouchDB document types.
    USER = "user"
    CALL = "call"
    PROPOSAL = "proposal"
    REVIEW = "review"
    DECISION = "decision"
    GRANT = "grant"
    LOG = "log"
    META = "meta"

    # CouchDB upper value.
    CEILING = "ZZZZZZZZ"

    # Generic fields in CouchDB document.
    GENERIC_FIELDS = frozenset(
        ["_id", "_rev", "_attachments", "doctype", "created", "modified"]
    )

    # User roles.
    ADMIN = "admin"
    STAFF = "staff"
    # USER  = 'user' # Defined above
    USER_ROLES = (ADMIN, STAFF, USER)

    # User statuses.
    PENDING = "pending"
    ENABLED = "enabled"
    DISABLED = "disabled"
    USER_STATUSES = (PENDING, ENABLED, DISABLED)

    # Input field types.
    LINE = "line"
    EMAIL = "email"
    BOOLEAN = "boolean"
    SELECT = "select"
    INTEGER = "integer"
    FLOAT = "float"
    SCORE = "score"
    RANK = "rank"
    TEXT = "text"
    DOCUMENT = "document"
    REPEAT = "repeat"

    # Exclude RANK, SCORE (not meaningful) and REPEAT (not yet implemented).
    PROPOSAL_FIELD_TYPES = (
        LINE,
        EMAIL,
        BOOLEAN,
        SELECT,
        INTEGER,
        FLOAT,
        TEXT,
        DOCUMENT,
    )

    # Exclude REPEAT (not yet implemented).
    REVIEW_FIELD_TYPES = (
        LINE,
        EMAIL,
        BOOLEAN,
        SELECT,
        INTEGER,
        FLOAT,
        SCORE,
        RANK,
        TEXT,
        DOCUMENT,
    )

    # Exclude RANK, SCORE (not meaningful) and REPEAT (not yet implemented).
    DECISION_FIELD_TYPES = (
        LINE,
        EMAIL,
        BOOLEAN,
        SELECT,
        INTEGER,
        FLOAT,
        TEXT,
        DOCUMENT,
    )

    # Exclude RANK, SCORE (not meaningful).
    GRANT_FIELD_TYPES = (
        LINE,
        EMAIL,
        BOOLEAN,
        SELECT,
        INTEGER,
        FLOAT,
        TEXT,
        DOCUMENT,
        REPEAT,
    )

    # Privileges flags for each call.
    PRIVILEGES = (
        "allow_reviewer_view_all_reviews",
        "allow_submitter_view_decision",
        "allow_chair_create_reviews",
    )

    # Delimiters to remove when searching in proposal titles.
    PROPOSALS_SEARCH_DELIMS_LINT = (":", ",", ";", "'", '"', "(", ")")

    # Words to remove when searching in proposal titles.
    PROPOSALS_SEARCH_LINT = (
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "is",
        "in",
        "not",
        "of",
        "on",
        "the",
        "to",
        "was",
    )

    # Call order (sorting) key alternatives.
    CALL_ORDER_KEYS = frozenset(["closes", "title", "identifier"])

    # Site files, caching timeout.
    SITE_FILES = frozenset(["name_logo", "host_logo"])
    SITE_FILE_MAX_AGE = 24 * 3600

    # MIME types
    DOCX_MIMETYPE = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ZIP_MIMETYPE = "application/zip"
    XML_MIMETYPE = "text/xml"
    JSON_MIMETYPE = "application/json"

    ALLOWED_ID_CHARACTERS = frozenset(string.ascii_lowercase + string.digits + "-_")


constants = Constants()
