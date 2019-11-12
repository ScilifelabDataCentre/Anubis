"Evaluation of a submission."

import flask

from . import constants
from . import utils
from .saver import BaseSaver


blueprint = flask.Blueprint('evaluation', __name__)

@blueprint.route('/<sid>')
@utils.login_required
def create(sid):
    """Create a new evaluation for the submission.
    Redirect to existing is the user (reviewer) already has one.
    """
    raise NotImplementedError

@blueprint.route('/<sid>/<iuid:iuid>')
@utils.login_required
def display(sid, iuid):
    "Display the evaluation for the submission."
    raise NotImplementedError

@blueprint.route('/<sid>/<iuid:iuid>/edit')
@utils.login_required
def edit(sid, iuid):
    "Edit the evaluation for the submission."
    raise NotImplementedError
