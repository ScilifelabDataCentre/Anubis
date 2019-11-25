"Reviews lists."

import flask

import anubis.user

from . import constants
from . import utils
from .review import get_review_cache


blueprint = flask.Blueprint('reviews', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all reviews for a call."
    from anubis.call import get_call
    call = get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not call['cache']['is_reviewer']:
        utils.flash_error('You are not a reviewer in the call.')
        return flask.redirect(flask.url_for('home'))

    scorefields = [f for f in call['review']
                   if f['type'] == constants.SCORE]
    reviews = [get_review_cache(r.doc)
                   for r in flask.g.db.view('reviews', 'call',
                                            key=cid,
                                            reduce=False,
                                            include_docs=True)]
    # XXX filter for reviews access
    return flask.render_template('reviews/call.html',
                                 call=call,
                                 scorefields=scorefields,
                                 reviews=reviews)

@blueprint.route('/proposal/<pid>')
@utils.login_required
def proposal(pid):
    "List all reviews for a proposal."
    from anubis.proposal import get_proposal
    proposal = get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    call = proposal['cache']['call']
    if not call['cache']['is_reviewer']:
        utils.flash_error("You are not a reviewer of the proposal's call.")
        return flask.redirect(flask.url_for('home'))

    reviews = [get_review_cache(r.doc)
                   for r in flask.g.db.view('reviews', 'call',
                                            key=call['identifier'],
                                            reduce=False,
                                            include_docs=True)]
    # XXX filter for reviews access
    return flask.render_template('reviews/proposal.html',
                                 proposal=proposal,
                                 reviews=reviews)

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all reviews for a user (reviewer)."
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
    result = flask.g.db.view('reviews', 'proposal_reviewer',
                             startkey=[proposal['identifier'], ''],
                             endkey=[proposal['identifier'], 'ZZZZZZ'],
                             reduce=True)
    if result:
        return result[0].value
    else:
        return 0
