"Privilege functions."

import flask

from . import constants

def is_admin(user=None):
    "Is the user admin? Default: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['role'] == constants.ADMIN

def may_create_proposal(call, user=None):
    "May the user create a proposal in the call? Default: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    if user['role'] == constants.ADMIN: return True
    return user['username'] not in call['reviewers']

def is_call_reviewer(call, user=None):
    "Is the user a reviewer in the call? Default: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['username'] in call['reviewers']

def is_call_editable(call, user=None):
    "Is the call editable by the user? Default: current_user."
    if user is None:
        user = flask.g.current_user
    if user is None: return False
    return user['role'] == constants.ADMIN
