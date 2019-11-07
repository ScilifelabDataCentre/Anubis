"Call for submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('call', __name__)

@blueprint.route('/create', methods=['GET', 'POST'])
@utils.admin_required
def create():
    "Create a new call."
    if utils.http_GET():
        return flask.render_template('call/create.html')
    elif utils.http_POST():
        raise NotImplementedError

@blueprint.route('/<name:callid>')
def display():
    "Display a call."
    raise NotImplementedError

@blueprint.route('/<name:callid>/submission', methods=['GET', 'POST'])
@utils.login_required
def submission():
    "Create a new submission in the given call."
    raise NotImplementedError

