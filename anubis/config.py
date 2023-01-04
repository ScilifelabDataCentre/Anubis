"""Configuration of this Anubis instance: default configuration,
modified by an optional settings file or environment variables.
"""

import datetime
import json
import os
import os.path

import couchdb2
import dotenv
import flask
import pytz
from werkzeug.middleware.proxy_fix import ProxyFix

from anubis import constants
from anubis import utils

import anubis.database


# Default configurable values, loaded and/or modified in procedure 'init'.
DEFAULT_CONFIG = dict(
    SETTINGS_DOTENV=False,
    SETTINGS_FILE=None,
    SETTINGS_ENVVAR=False,
    FLASK_DEBUG=False,
    SERVER_NAME=None,
    REVERSE_PROXY=False,
    SECRET_KEY=None,  # Must be set!
    COUCHDB_URL="http://127.0.0.1:5984/", # Likely, if CouchDB on local machine.
    COUCHDB_USERNAME=None, # Must probably be set; depends on CouchDB setup.
    COUCHDB_PASSWORD=None, # Must probably be set; depends on CouchDB setup.
    COUCHDB_DBNAME="anubis",
    MIN_PASSWORD_LENGTH=6, # Must be at least 4.
    # Default timezone is that of the host machine.
    TIMEZONE=str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo),
    MAIL_SERVER=None,  # E.g. "localhost" or domain name. If None: emails disabled.
    MAIL_PORT=25,
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=None,
    MAIL_PASSWORD=None,
    MAIL_DEFAULT_SENDER=None,  # Should be set if email is enabled.
    MAIL_REPLY_TO=None,
    CALL_REMAINING_DANGER=1.0,
    CALL_REMAINING_WARNING=7.0,
    CALLS_OPEN_ORDER_KEY="closes",
)


def init(app):
    """Perform the configuration of the Flask app.
    1) Start with values in DEFAULT_SETTINGS.
    2) Set environment variables from file '.env' using 'dotenv.load_dotenv'.
    3) Collect the possible settings file paths in the following order:
       - The environment variable ANUBIS_SETTINGS_FILEPATH, if any.
       - The file 'settings.json' in this directory.
       - The file '../site/settings.json' relative to this directory.
    4) Use the first of these files that is found and can be read.
    5) Use any environment variables defined.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    app.config.from_mapping(DEFAULT_CONFIG)

    app.config["SETTINGS_DOTENV"] = dotenv.load_dotenv()
    if app.config["SETTINGS_DOTENV"]:
        app.logger.info(f"set environment variables from '.env' file")

    # Collect filepaths for possible settings files.
    filepaths = []
    try:
        filepaths.append(os.environ["ANUBIS_SETTINGS_FILEPATH"])
    except KeyError:
        pass
    for filepath in ["settings.json", "../site/settings.json"]:
        filepaths.append(os.path.normpath(os.path.join(constants.ROOT, filepath)))

    # Use the first settings file that can be found.
    for filepath in filepaths:
        try:
            with open(filepath) as infile:
                config = json.load(infile)
        except OSError:
            pass
        else:
            for key in config.keys():
                if key not in DEFAULT_CONFIG:
                    app.logger.warning(f"Obsolete item '{key}' in settings file.")
            app.config.update(**config)
            app.config["SETTINGS_FILE"] = filepath
            app.logger.info(f"settings file: {app.config['SETTINGS_FILE']}")
            break
            
    # Modify the configuration from environment variables; convert to correct type.
    for key, value in DEFAULT_CONFIG.items():
        try:
            new = os.environ[key]
        except KeyError:
            pass
        else:  # Do NOT catch any exception! Means bad setup.
            if isinstance(value, int):
                app.config[key] = int(new)
            elif isinstance(value, bool):
                app.config[key] = utils.to_bool(new)
            else:
                app.config[key] = new
            app.logger.info(f"setting '{key}' from environment variable.")
            app.config["SETTINGS_ENVVAR"] = True

    # Must be done after all possible settings sources have been processed.
    if app.config["REVERSE_PROXY"]:
        app.wsgi_app = ProxyFix(app.wsgi_app)

    # Sanity checks. Any Exception raised here means bad configuration.
    if not app.config["SECRET_KEY"]:
        raise ValueError("SECRET_KEY not set")
    if app.config["MIN_PASSWORD_LENGTH"] <= 4:
        raise ValueError("MIN_PASSWORD_LENGTH is too short")
    pytz.timezone(app.config["TIMEZONE"])


def init_from_db():
    """Set configuration from values stored in the database.
    These are not settable by environment variables or the settings file.
    """
    db = anubis.database.get_db()
    app = flask.current_app

    configuration = db["site_configuration"]
    for key, value in configuration.items():
        if key in constants.GENERIC_FIELDS: continue
        app.config[f"SITE_{key.upper()}"] = value
    modified = datetime.datetime.fromisoformat(configuration["modified"].strip("Z"))
    for filename in constants.SITE_FILES:
        key = f"SITE_{filename.upper()}"
        try:
            filestub = configuration["_attachments"][filename]
            infile = db.get_attachment(configuration, filename)
        except (KeyError, couchdb2.NotFoundError):
            app.config.pop(key, None)
        else:
            app.config[key] = {"content": infile.read(),
                               "mimetype": filestub["content_type"],
                               "etag": filestub["digest"],
                               "modified": modified}

    configuration = db["user_configuration"]
    for key, value in configuration.items():
        if key in constants.GENERIC_FIELDS: continue
        if key == "universities":  # Special case
            app.config["UNIVERSITIES"] = value
        else:
            app.config[f"USER_{key.upper()}"] = value
    # Special case: user cannot be enabled immediately if no email server defined.
    if not app.config["MAIL_SERVER"]:
        app.config["USER_ENABLE_EMAIL_WHITELIST"] = []


def get_config(hidden=True):
    "Return the current config."
    result = {"ROOT": constants.ROOT}
    for key in anubis.config.DEFAULT_CONFIG:
        result[key] = flask.current_app.config[key]
    if hidden:
        for key in ["SECRET_KEY", "COUCHDB_PASSWORD", "MAIL_PASSWORD"]:
            if result[key]:
                result[key] = "<hidden>"
    return result
