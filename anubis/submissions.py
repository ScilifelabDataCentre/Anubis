"Lists of submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('submissions', __name__)

@blueprint.route('/all')
@utils.admin_required
def all():
    "List of all submissions."
    raise NotImplementedError

