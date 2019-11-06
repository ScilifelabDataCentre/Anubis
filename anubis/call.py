"Call for submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('call', __name__)

@blueprint.route('/all')
@utils.admin_required
def all():
    return flask.render_template('call/all.html')

@blueprint.route('/create', methods=['GET', 'POST'])
@utils.admin_required
def create():
    if utils.http_GET():
        return flask.render_template('call/create.html')
    elif utils.http_POST():
        raise NotImplementedError
