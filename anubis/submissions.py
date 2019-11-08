"Lists of submissions."

import flask

import anubis.call

from . import constants
from . import utils


blueprint = flask.Blueprint('submissions', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List submissions in a call according to user access privileges."
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    # XXX check access
    submissions = get_submissions(call)
    return flask.render_template('submissions/call.html', 
                                 call=call,
                                 submissions=submissions)

def get_submissions(call):
    "Get all submissions for the call."
    return [r.doc for r in flask.g.db.view('submissions', 'call',
                                           key=call['identifier'],
                                           reduce=False,
                                           include_docs=True)]
