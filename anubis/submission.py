"Submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/all')
@utils.admin_required
def all():
    return flask.render_template('submission/all.html')

@blueprint.route('/<name:callname>/create', methods=['GET', 'POST'])
@utils.login_required
def create():
    if utils.http_GET():
        return flask.render_template('submission/create.html')
    elif utils.http_POST():
        raise NotImplementedError
