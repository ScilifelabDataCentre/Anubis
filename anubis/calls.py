"Lists of calls for submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('calls', __name__)

@blueprint.route('')
@utils.admin_required
def all():
    "All calls."
    raise NotImplementedError

@blueprint.route('/user')
@blueprint.route('/user/<name:username>')
@utils.login_required
def user(username=''):
    "Calls in which the user is involved (submitter or reviewer)."
    raise NotImplementedError
