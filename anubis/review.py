"Review of a proposal. Created from the proposal fields in the call."

import flask

import anubis.user
import anubis.call
import anubis.proposal

from . import constants
from . import utils
from .saver import BaseSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('reviews', DESIGN_DOC):
        print(' > Updated reviews design document.')

DESIGN_DOC = {
    'views': {
        # Reviews for all proposals in call.
        'call': {'reduce': '_count',
                 'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.call, null);}"},
        # Reviews for a proposal.
        'proposal': {'reduce': '_count',
                     'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.proposal, null);}"},
        # Reviews per reviewer, in any call
        'reviewer': {'reduce': '_count',
                     'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.reviewer, null);}"},
        # Reviews per call and reviewer.
        'call_reviewer': {'reduce': '_count',
                          'map': "function(doc) {if (doc.doctype !== 'review') return; emit([doc.call, doc.reviewer], null);}"},
        'proposal_reviewer': {'map': "function(doc) {if (doc.doctype !== 'review') return; emit([doc.proposal, doc.reviewer], null);}"},
        # Unfinalized reviews by reviewer, in any call.
        'unfinalized': {'reduce': '_count',
                        'map': "function(doc) {if (doc.doctype !== 'review' || doc.finalized) return; emit(doc.reviewer, null);}"},
    }
}

blueprint = flask.Blueprint('review', __name__)

@blueprint.route('/create/<pid>/<username>', methods=['POST'])
@utils.login_required
def create(pid, username):
    "Create a new review for the proposal for the given reviewer."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])

    try:
        if not allow_create(proposal):
            utils.flash_error('You may not create a review for the proposal.')
            raise ValueError
        user = anubis.user.get_user(username=username)
        if user is None:
            utils.flash_error('No such user.')
            raise ValueError
        if user['username'] not in call['reviewers']:
            utils.flash_error('User is not a reviewer in the call.')
            raise ValueError
        review = get_reviewer_review(proposal, user)
        if review is not None:
            utils.flash_message('The review already exists.')
            return flask.redirect(flask.url_for('.display', iuid=review['_id']))
        with ReviewSaver(proposal=proposal) as saver:
            saver.set_reviewer(user)
        print(saver.doc)
    except ValueError:
        pass
    try:
        return flask.redirect(flask.request.form['_next'])
    except KeyError:
        return flask.redirect(
            flask.url_for('reviews.proposal', pid=proposal['identifier']))

@blueprint.route('/<iuid:iuid>')
@utils.login_required
def display(iuid):
    "Display the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    proposal = anubis.proposal.get_proposal(review['proposal'])
    call = anubis.call.get_call(review['call'])

    if not allow_view(review):
        utils.flash_error('You are not allowed to view this review.')
        return flask.redirect(
            flask.url_for('proposal.display', pid=review['proposal']))
    return flask.render_template('review/display.html',
                                 review=review,
                                 proposal=proposal,
                                 call=call,
                                 allow_edit=allow_edit(review),
                                 allow_delete=allow_delete(review),
                                 allow_finalize=allow_finalize(review),
                                 allow_unfinalize=allow_unfinalize(review))

@blueprint.route('/<iuid:iuid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(iuid):
    "Edit the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    proposal = anubis.proposal.get_proposal(review['proposal'])
    call = anubis.call.get_call(review['call'])

    if utils.http_GET():
        if not allow_edit(review):
            utils.flash_error('You are not allowed to edit this review.')
            return flask.redirect(flask.url_for('.display', iuid=review['_id']))
        return flask.render_template('review/edit.html',
                                     review=review,
                                     proposal=proposal,
                                     call=call)

    elif utils.http_POST():
        if not allow_edit(review):
            utils.flash_error('You are not allowed to edit this review.')
            return flask.redirect(flask.url_for('.display', iuid=review['_id']))
        try:
            with ReviewSaver(doc=review) as saver:
                for field in call['review']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(utils.referrer_or_home())
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

    elif utils.http_DELETE():
        if not allow_delete(review):
            utils.flash_error('You are not allowed to delete this review.')
            return flask.redirect(flask.url_for('.display', iuid=review['_id']))
        utils.delete(review)
        utils.flash_message('Deleted review.')
        return flask.redirect(flask.url_for('call.display', cid=review['call']))

@blueprint.route('/<iuid:iuid>/finalize', methods=['POST'])
@utils.login_required
def finalize(iuid):
    "Finalize the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not allow_finalize(review):
        utils.flash_error('You are not allowed to finalize this review.')
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = utils.get_time()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/unfinalize', methods=['POST'])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not allow_unfinalize(review):
        utils.flash_error('You are not allowed to unfinalize this review.')
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = None
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/logs')
@utils.login_required
def logs(iuid):
    "Display the log records of the review."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Review of {review['proposal']} by {review['reviewer']}",
        back_url=flask.url_for('.display', iuid=review['_id']),
        logs=utils.get_logs(review['_id']))

@blueprint.route('/<iuid:iuid>/document/<documentname>')
@utils.login_required
def document(iuid, documentname):
    "Download the given review document (attachment file)."
    try:
        review = get_review(iuid)
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not allow_view(review):
        utils.flash_error('You are not allowed to read this review.')
        return flask.redirect(flask.url_for('home'))

    try:
        stub = review['_attachments'][documentname]
    except KeyError:
        utils.flash_error('No such document in review.')
        return flask.redirect(
            flask.url_for('.display', iuid=review['identifier']))
    outfile = flask.g.db.get_attachment(review, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=documentname)
    return response


class ReviewSaver(FieldMixin, BaseSaver):
    "Review document saver context."

    DOCTYPE = constants.REVIEW

    def __init__(self, doc=None, proposal=None):
        if doc:
            super().__init__(doc=doc)
        elif proposal:
            super().__init__(doc=None)
            self.set_proposal(proposal)
            self.set_reviewer(flask.g.current_user)
        else:
            raise ValueError('doc or proposal must be specified')

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_proposal(self, proposal):
        "Set the proposal for the review; must be called when creating."
        if self.doc.get('proposal'):
            raise ValueError('proposal has already been set')
        self.doc['call'] = proposal['call']
        self.doc['proposal'] = proposal['identifier']
        call = anubis.call.get_call(proposal['call'])
        for field in call['review']:
            self.set_field_value(field)

    def set_reviewer(self, user):
        "Set the reviewer for the review; must be called at creation."
        self.doc['reviewer'] = user['username']


def get_review(iuid, refetch=False):
    "Get the review by its iuid."
    if not iuid: return None
    try:
        if refetch: raise KeyError
        return flask.g.cache[iuid]
    except KeyError:
        review = flask.g.db[iuid]
        if review['doctype'] != constants.REVIEW: raise ValueError
        flask.g.cache[iuid] = review
        return review

def get_reviewer_review(proposal, reviewer):
    "Get the review of the proposal by the reviewer."
    result = flask.g.db.view('reviews', 'proposal_reviewer',
                             key=[proposal['identifier'], reviewer['username']],
                             reduce=False,
                             include_docs=True)
    try:
        return result[0].doc
    except IndexError:
        return None

def allow_create(proposal):
    "Admin and chair may create a review for a submitted proposal."
    if not proposal.get('submitted'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    return anubis.call.am_chair(call)

def allow_view(review):
    """Admin may view all reviews.
    Chair may view all reviews in a call.
    Reviewer may view her own reviews.
    Reviewer may view all reviews depending on access flag for the call.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user['username'] == review['reviewer']: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_reviewer(call): return True
    return anubis.call.allow_view_reviews(call) and review.get('finalized')

def allow_edit(review):
    "Admin and reviewer may edit an unfinalized review."
    if review.get('finalized'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(review['call'])
    if call.get('reviews_due') and utils.days_remaining(call['reviews_due'])<0:
        return False
    return flask.g.current_user['username'] == review['reviewer']

def allow_delete(review):
    "Admin may delete a review."
    return flask.g.am_admin

def allow_finalize(review):
    "Admin and reviewer may finalize if the review contains no errors."
    if review.get('finalized'): return False
    if not flask.g.current_user: return False
    if review['errors']: return False
    if flask.g.am_admin: return True
    return flask.g.current_user['username'] == review['reviewer']

def allow_unfinalize(review):
    "Admin and reviewer may unfinalize the review if before reviews due date."
    if not review.get('finalized'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(review['call'])
    if call.get('reviews_due') and utils.days_remaining(call['reviews_due'])<0:
        return False
    return flask.g.current_user['username'] == review['reviewer']
