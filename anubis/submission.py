"Submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/<sid>')
@utils.login_required
def display(sid):
    "Display a submission."
    raise NotImplementedError
