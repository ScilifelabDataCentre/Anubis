"Lists of calls for submissions."

import flask

import anubis.call

from . import constants
from . import utils


blueprint = flask.Blueprint('calls', __name__)

@blueprint.route('')
@utils.admin_required
def all():
    "All calls."
    calls = [r.doc for r in 
             flask.g.db.view('calls', 'identifier', include_docs=True)]
    anubis.call.update_calls(calls)
    return flask.render_template('calls/all.html', calls=calls)

@blueprint.route('/user')
@blueprint.route('/user/<username>')
@utils.login_required
def user(username=''):
    "Calls in which the user is involved (submitter or reviewer)."
    raise NotImplementedError
