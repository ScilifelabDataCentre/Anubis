"Configuration of the instance: default settings and reading of settings file."

import json
import os
import os.path

from anubis import constants
from anubis import utils


# Default configurable values; modified by reading a JSON file in 'init'.
DEFAULT_SETTINGS = dict(
    SERVER_NAME = '127.0.0.1:5002', # For URL generation; app.run() in devel.
    SITE_NAME = 'Anubis',
    SITE_STATIC_DIR = os.path.normpath(
        os.path.join(constants.ROOT, "../site/static")),
    SITE_ICON = None,           # Name of file in 'SITE_STATIC_DIR'.
    SITE_LOGO = None,           # Name of file in 'SITE_STATIC_DIR'.
    SITE_DESCRIPTION = "Proposal submission and review handling system.",
    HOST_LOGO = None,           # Name of file in 'SITE_STATIC_DIR'.
    HOST_NAME = None,
    HOST_URL = None,
    SECRET_KEY = None,          # Must be set in 'settings.json'.
    SALT_LENGTH = 12,
    COUCHDB_URL = 'http://127.0.0.1:5984/',
    COUCHDB_USERNAME = None,
    COUCHDB_PASSWORD = None,
    COUCHDB_DBNAME = 'anubis',
    JSON_AS_ASCII = False,
    JSON_SORT_KEYS = False,
    MIN_PASSWORD_LENGTH = 6,
    PERMANENT_SESSION_LIFETIME = 7 * 24 * 60 * 60, # In seconds; 1 week.
    DOC_DIR = os.path.join(constants.ROOT, 'documentation'),
    MAIL_SERVER = 'localhost',
    MAIL_PORT = 25,
    MAIL_USE_TLS = False,
    MAIL_USERNAME = None,
    MAIL_PASSWORD = None,
    MAIL_DEFAULT_SENDER = 'anubis@your.org', # Must be changed in settings!
    CALL_IDENTIFIER_MAXLENGTH = 16,
    CALL_REMAINING_DANGER = 1.0,
    CALL_REMAINING_WARNING = 7.0,
    CALLS_OPEN_ORDER_KEY = 'closes',
    USER_GENDERS = ['male', 'female', 'other'],
    USER_BIRTHDATE = True,
    USER_TITLE = True,
    USER_AFFILIATION = True,
    USER_POSTAL_ADDRESS = True,
    USER_PHONE = True,
    USER_ENABLE_IMMEDIATELY = False,
    USER_ENABLE_EMAIL_WHITELIST = [], # List of fnmatch patterns, not regexp's!
    MARKDOWN_URL = 'https://daringfireball.net/projects/markdown/syntax',
)


def init(app):
    """Perform the configuration of the Flask app.
    Set the defaults, and then modify the values based on:
    1) The settings file path environment variable ANUBIS_SETTINGS_FILEPATH.
    2) The file 'settings.json' in this directory.
    3) The file '../site/settings.json' relative to this directory.
    Check the environment for variables and use if defined.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    # Set the defaults specified above.
    app.config.from_mapping(DEFAULT_SETTINGS)

    # Modify the configuration from a JSON settings file.
    filepaths = []
    try:
        filepaths.append(os.environ['ANUBIS_SETTINGS_FILEPATH'])
    except KeyError:
        pass
    for filepath in ['settings.json', '../site/settings.json']:
        filepaths.append(
            os.path.normpath(os.path.join(constants.ROOT, filepath)))
    for filepath in filepaths:
        try:
            app.config.from_file(filepath, load=json.load)
        except FileNotFoundError:
            pass
        else:
            app.config['SETTINGS_FILE'] = filepath
            break

    # Modify the configuration from environment variables.
    for key, value in DEFAULT_SETTINGS.items():
        try:
            new = os.environ[key]
        except KeyError:
            pass
        else:                   # Do NOT catch any exception! Means bad setup.
            if isinstance(value, int):
                app.config[key] = int(new)
            elif isinstance(value, bool):
                app.config[key] = bool(new)
            else:
                app.config[key] = new

    # Sanity checks. Exception means bad setup.
    if not app.config['SECRET_KEY']:
        raise ValueError("SECRET_KEY not set")
    if app.config['SALT_LENGTH'] <= 6:
        raise ValueError("SALT_LENGTH is too short")
    if app.config['MIN_PASSWORD_LENGTH'] <= 4:
        raise ValueError("MIN_PASSWORD_LENGTH is too short")
