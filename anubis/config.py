"""Configuration of this Anubis instance: default configuration,
modified by an optional settings file or environment variables.
"""

import datetime
import json
import os
import os.path

import pytz

from anubis import constants
from anubis import utils


# Default configurable values, loaded and/or modified in procedure 'init'.
DEFAULT_CONFIG = dict(
    DEBUG=False,
    SERVER_NAME=None, # Previously "localhost:5002" for development.
    REVERSE_PROXY=False,
    SITE_NAME="Anubis",
    SITE_DESCRIPTION="Submit proposals for grants in open calls.",
    HOST_NAME=None,
    HOST_URL=None,
    SECRET_KEY=None,  # Must be set!
    COUCHDB_URL="http://127.0.0.1:5984/",
    COUCHDB_USERNAME=None, # Must probably be set.
    COUCHDB_PASSWORD=None, # Must probably bet set.
    COUCHDB_DBNAME="anubis",
    MIN_PASSWORD_LENGTH=6, # Must be at least 4.
    PERMANENT_SESSION_LIFETIME=7 * 24 * 60 * 60,  # In seconds; 1 week.
    # Default timezone to that of the host machine.
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
    Set the defaults, and then modify the values based on:
    1) The settings file path environment variable ANUBIS_SETTINGS_FILEPATH.
    2) The file 'settings.json' in this directory.
    3) The file '../site/settings.json' relative to this directory.
    4) Check for environment variables and use value if defined.
    Raise IOError if settings file could not be read.
    Raise KeyError if a settings variable is missing.
    Raise ValueError if a settings variable value is invalid.
    """
    app.config.from_mapping(DEFAULT_CONFIG)

    # Hard-wired Flask configurations.
    app.config["JSON_AS_ASCII"] = False
    app.config["JSON_SORT_KEYS"] = False

    # Modify the configuration from a JSON settings file.
    filepaths = []
    try:
        filepaths.append(os.environ["ANUBIS_SETTINGS_FILEPATH"])
    except KeyError:
        pass
    for filepath in ["settings.json", "../site/settings.json"]:
        filepaths.append(os.path.normpath(os.path.join(constants.ROOT, filepath)))
    for filepath in filepaths:
        try:
            with open(filepath) as infile:
                config = json.load(infile)
        except FileNotFoundError:
            pass
        else:
            for key in config.keys():
                if key not in DEFAULT_CONFIG:
                    app.logger.warning(f"Obsolete item '{key}' in settings file.")
            app.config.update(**config)
            app.config["SETTINGS_FILE"] = filepath
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

    # Sanity checks. Exception means bad setup.
    if not app.config["SECRET_KEY"]:
        raise ValueError("SECRET_KEY not set")
    if app.config["MIN_PASSWORD_LENGTH"] <= 4:
        raise ValueError("MIN_PASSWORD_LENGTH is too short")
    pytz.timezone(app.config["TIMEZONE"])
