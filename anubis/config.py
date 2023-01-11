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
    FLASK_DEBUG=False,
    REVERSE_PROXY=False,    # Use 'werkzeug.middleware.proxy_fix.ProxyFix'
    SECRET_KEY=None,        # Must be set for proper session handling!
    COUCHDB_URL="http://127.0.0.1:5984/",  # Likely, if CouchDB on local machine.
    COUCHDB_USERNAME=None,  # Must probably be set; depends on CouchDB setup.
    COUCHDB_PASSWORD=None,  # Must probably be set; depends on CouchDB setup.
    COUCHDB_DBNAME="anubis",# The database instance within CouchDB to use.
    MIN_PASSWORD_LENGTH=6,  # Must be at least 4.
    # Default timezone is that of the host machine.
    TIMEZONE=str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo),
    MAIL_SERVER=None,       # E.g. "localhost" or domain name. If None: email disabled.
    MAIL_PORT=25,           # Must be changed if TLS or SSL is used.
    MAIL_USE_TLS=False,     # Use TLS for email or not.
    MAIL_USE_SSL=False,     # Use SSL for email or not.
    MAIL_USERNAME=None,     # Email server account; most likely an email address.
    MAIL_PASSWORD=None,     # Email server account password.
    MAIL_DEFAULT_SENDER=None,  # Email address from which Anubis emails are sent.
    MAIL_REPLY_TO=None,        # If different from default sender.
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
            app.config.from_mapping(config)
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

    # Read and preprocess the documentation.
    with open("documentation.md") as infile:
        lines = infile.readlines()
    toc = []
    current_level = 0
    for line in lines:
        if line.startswith("#"):
            parts = line.split()
            level = len(parts[0])
            title = " ".join(parts[1:])
            # All headers in README are "clean", i.e. text only, no markup.
            id = title.strip().replace(" ", "-").lower()
            id = "".join(c for c in id if c in constants.ALLOWED_ID_CHARACTERS)
            # Add to table of contents.
            if level <= 2:
                if level > current_level:
                    for l in range(current_level, level):
                        toc.append('<ul class="list-unstyled ml-3">')
                    current_level = level
                elif level < current_level:
                    for l in range(level, current_level):
                        toc.append("</ul>")
                    current_level = level
                toc.append(f'<li><a href="#{id}">{title}</a></li>')
    for level in range(current_level):
        toc.append("</ul>")
    app.config["DOCUMENTATION_TOC"] = "\n".join(toc)
    app.config["DOCUMENTATION"] = utils.markdown2html("".join(lines))


def init_from_db():
    """Set configuration from values stored in the database.
    These are not settable by environment variables or the settings file.
    """
    db = anubis.database.get_db()
    app = flask.current_app

    # Site configuration values from database to Flask config.
    configuration = db["site_configuration"]
    for key, value in configuration.items():
        if key in constants.GENERIC_FIELDS:
            continue
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
            app.config[key] = {
                "content": infile.read(),
                "mimetype": filestub["content_type"],
                "etag": filestub["digest"],
                "modified": modified,
            }

    # User configuration values from database to Flask config.
    configuration = db["user_configuration"]
    for key, value in configuration.items():
        if key in constants.GENERIC_FIELDS:
            continue
        if key == "universities":  # Special case
            app.config["UNIVERSITIES"] = value
        else:
            app.config[f"USER_{key.upper()}"] = value
    # Special case: user cannot be enabled immediately if no email server defined.
    if not app.config["MAIL_SERVER"]:
        app.config["USER_ENABLE_EMAIL_WHITELIST"] = []

    # Call configuration values from database to Flask config.
    configuration = db["call_configuration"]
    for key, value in configuration.items():
        if key in constants.GENERIC_FIELDS:
            continue
        app.config[f"CALL_{key.upper()}"] = value


def get_config(hidden=True):
    """Return the current config. Only those items that are supposed to
    be set for a site, not those that are set by the software.
    """
    result = {"ROOT": constants.ROOT}
    for key in ["SETTINGS_DOTENV", "SETTINGS_ENVVAR", "SETTINGS_FILE"]:
        result[key] = flask.current_app.config.get(key)
    for key in anubis.config.DEFAULT_CONFIG:
        result[key] = flask.current_app.config[key]
    if hidden:
        for key in ["SECRET_KEY", "COUCHDB_PASSWORD", "MAIL_PASSWORD"]:
            if result[key]:
                result[key] = "<hidden>"
    return result
