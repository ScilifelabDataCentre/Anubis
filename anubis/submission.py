"Submissions."

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('submission', __name__)

@blueprint.route('/<name:submid>')
@utils.login_required
def display():
    "Display a submission."
    raise NotImplementedError
