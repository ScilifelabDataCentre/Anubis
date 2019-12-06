"Reviews lists."

import flask

import anubis.call
import anubis.user
import anubis.proposal
import anubis.review

from . import constants
from . import utils

blueprint = flask.Blueprint('reviews', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all reviews for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not call['cache']['allow_view_reviews']:
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call',
                                        key=call['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    reviews_lookup = {f"r['proposal'] r['reviewer']":r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/call.html',
                                 call=call,
                                 proposals=proposals,
                                 reviews_lookup=reviews_lookup,
                                 scorefields=scorefields)

@blueprint.route('/call/<cid>/reviewer/<username>')
@utils.login_required
def call_reviewer(cid, username):
    "List all reviews in the call by the reviewer (user)."
    call = anubis.call.get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if user['username'] not in call['reviewers']:
        utils.flash_error("The user is not a reviewer in the call.")
        return flask.redirect(flask.url_for('home'))
    if not (anubis.user.is_admin_or_self(user) or
            call['cache']['allow_view_reviews']):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call_reviewer',
                                        key=[call['identifier'],
                                             user['username']],
                                        reduce=False,
                                        include_docs=True)]
    reviews_lookup = {r['proposal']:r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/call_reviewer.html', 
                                 call=call,
                                 proposals=proposals,
                                 user=user,
                                 reviews_lookup=reviews_lookup,
                                 scorefields=scorefields)

@blueprint.route('/proposal/<pid>')
@utils.login_required
def proposal(pid):
    "List all reviewers and reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))

    call = proposal['cache']['call']
    if not call['cache']['allow_view_reviews']:
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'proposal',
                                        key=proposal['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    reviews_lookup = {r['reviewer']:r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/proposal.html',
                                 proposal=proposal,
                                 reviewers=call['reviewers'],
                                 reviews_lookup=reviews_lookup,
                                 scorefields=scorefields)

@blueprint.route('/reviewer/<username>')
@utils.login_required
def reviewer(username):
    "List all reviews by the given reviewer (user)."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    # Access to view all reviews of a specific call is not sufficient.
    if not anubis.user.is_admin_or_self(user):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'reviewer',
                                        key=user['username'],
                                        reduce=False,
                                        include_docs=True)]
    return flask.render_template('reviews/reviewer.html', 
                                 user=user,
                                 reviews=reviews)
