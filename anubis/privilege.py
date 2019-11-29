"Privilege functions."

import flask

from . import constants

def is_admin(user=None):
    "Is the user admin? Default: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['role'] == constants.ADMIN
