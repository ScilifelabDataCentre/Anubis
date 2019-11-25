"Reviews lists."

import flask

import anubis.user
import anubis.proposal

from . import constants
from . import utils
from .review import get_review_cache


blueprint = flask.Blueprint('reviews', __name__)

@blueprint.route('/call/<cid>')
@utils.admin_required
def call(cid):
    "List all reviews for a call."
    from anubis.call import get_call
    call = get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    scorefields = [f for f in call['review']
                   if f['type'] == constants.SCORE]
    reviews = [get_review_cache(r.doc)
                   for r in flask.g.db.view('reviews', 'call',
                                            key=cid,
                                            reduce=False,
                                            include_docs=True)]
    return flask.render_template('reviews/call.html',
                                 call=call,
                                 scorefields=scorefields,
                                 reviews=reviews)

@blueprint.route('/proposal/<pid>')
@utils.admin_required
def proposal(pid):
    "List all reviewers and reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))

    call = proposal['cache']['call']
    scorefields = [f for f in call['review']
                   if f['type'] == constants.SCORE]
    reviews = [get_review_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call',
                                        key=call['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    return flask.render_template('reviews/proposal.html',
                                 proposal=proposal,
                                 reviewers=call['reviewers'],
                                 reviews=reviews,
                                 scorefields=scorefields)

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all reviews by a user (reviewer)."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(flask.url_for('home'))
    reviews = [get_review_cache(r.doc)
                   for r in flask.g.db.view('reviews', 'reviewer',
                                            key=user['username'],
                                            reduce=False,
                                            include_docs=True)]
    return flask.render_template('reviews/user.html', 
                                 user=user,
                                 proposals=reviews)

def get_call_reviews_count(call):
    "Get the number of reviews for the call."
    result = flask.g.db.view('reviews', 'call',
                             key=call['identifier'],
                             reduce=True)
    if result:
        return result[0].value
    else:
        return 0

def get_proposal_reviews_count(proposal):
    "Get the number of reviews for the proposal."
    result = flask.g.db.view('reviews', 'proposal',
                             key=proposal['identifier'],
                             reduce=True)
    if result:
        return result[0].value
    else:
        return 0
