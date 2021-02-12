"Review of a proposal. Created from the proposal fields in the call."

import os.path

import flask

import anubis.user
import anubis.call
import anubis.proposal
from anubis import constants
from anubis import utils
from anubis.saver import AttachmentSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('reviews', DESIGN_DOC):
        app.logger.info('Updated reviews design document.')

DESIGN_DOC = {
    'views': {
        # Reviews for all proposals in call.
        'call':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.call, null);}"},
        # Reviews for a proposal.
        'proposal':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.proposal, null);}"},
        # Reviews per reviewer, in any call
        'reviewer':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.reviewer, null);}"},
        # Reviews per call and reviewer.
        'call_reviewer':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit([doc.call, doc.reviewer], null);}"},
        'proposal_reviewer': {'map': "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit([doc.proposal, doc.reviewer], null);}"},
        # Unfinalized reviews by reviewer, in any call.
        'unfinalized':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || doc.finalized || doc.archived) return; emit(doc.reviewer, null);}"},
        # Archived reviews for a proposal.
        'proposal_archived':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || !doc.archived) return; emit(doc.proposal, null);}"},
        # Archived reviews for a proposal and reviewer.
        'proposal_reviewer_archived':
        {'reduce': '_count',
         'map': "function(doc) {if (doc.doctype !== 'review' || !doc.archived) return; emit([doc.proposal, doc.reviewer], null);}"},
    }
}

blueprint = flask.Blueprint('review', __name__)

@blueprint.route('/create/<pid>/<username>', methods=['POST'])
@utils.login_required
def create(pid, username):
    "Create a new review for the proposal for the given reviewer."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    call = anubis.call.get_call(proposal['call'])

    try:
        if not allow_create(proposal):
            raise ValueError('You may not create a review for the proposal.')
        user = anubis.user.get_user(username=username)
        if user is None:
            raise ValueError('No such user.')
        if user['username'] not in call['reviewers']:
            raise ValueError('User is not a reviewer in the call.')
        review = get_reviewer_review(proposal, user)
        if review is not None:
            utils.flash_message('The review already exists.')
            return flask.redirect(flask.url_for('.display', iuid=review['_id']))
        if proposal['user'] == user['username']:
            raise ValueError('Reviewer not allowed to review their own proposal.')
        with ReviewSaver(proposal=proposal, user=user) as saver:
            pass
    except ValueError as error:
        utils.flash_error(error)
    try:
        url = flask.request.form['_next']
    except KeyError:
        url = flask.url_for('reviews.proposal', pid=proposal['identifier'])
    return flask.redirect(url)

@blueprint.route('/<iuid:iuid>')
@utils.login_required
def display(iuid):
    "Display the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    call = anubis.call.get_call(review['call'])
    proposal = anubis.proposal.get_proposal(review['proposal'])
    if not allow_view(review):
        return utils.error('You are not allowed to view this review.',
                           flask.url_for('proposal.display',
                                         pid=review['proposal']))
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    return flask.render_template('review/display.html',
                                 review=review,
                                 call=call,
                                 proposal=proposal,
                                 allow_edit=allow_edit(review),
                                 allow_delete=allow_delete(review),
                                 allow_finalize=allow_finalize(review),
                                 allow_unfinalize=allow_unfinalize(review),
                                 allow_view_reviews=allow_view_reviews)

@blueprint.route('/<iuid:iuid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(iuid):
    "Edit the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    proposal = anubis.proposal.get_proposal(review['proposal'])
    call = anubis.call.get_call(review['call'])

    if utils.http_GET():
        if not allow_edit(review):
            return utils.error('You are not allowed to edit this review.',
                               flask.url_for('.display', iuid=review['_id']))
        return flask.render_template('review/edit.html',
                                     review=review,
                                     proposal=proposal,
                                     call=call)

    elif utils.http_POST():
        if not allow_edit(review):
            return utils.error('You are not allowed to edit this review.',
                               flask.url_for('.display', iuid=review['_id']))
        try:
            with ReviewSaver(doc=review) as saver:
                for field in call['review']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            return utils.error(error)
        # NOTE: Repeat field has not been implemented for review.
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

    elif utils.http_DELETE():
        if not allow_delete(review):
            return utils.error('You are not allowed to delete this review.',
                               flask.url_for('.display', iuid=review['_id']))
        utils.delete(review)
        utils.flash_message('Deleted review.')
        return flask.redirect(
            flask.url_for('proposal.display', pid=review['proposal']))

@blueprint.route('/<iuid:iuid>/finalize', methods=['POST'])
@utils.login_required
def finalize(iuid):
    "Finalize the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    if not allow_finalize(review):
        return utils.error('You are not allowed to finalize this review.',
                           flask.url_for('.display', iuid=review['_id']))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = utils.get_time()
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/unfinalize', methods=['POST'])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the review for the proposal."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    if not allow_unfinalize(review):
        return utils.error('You are not allowed to unfinalize this review.',
                           flask.url_for('.display', iuid=review['_id']))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = None
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/archive', methods=['POST'])
@utils.login_required
def archive(iuid):
    "Archive the review for the proposal. Requires 'delete' privilege."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    # In a sense similar to deleting, so requires same priviliege.
    if not allow_delete(review):
        return utils.error('You are not allowed to archive this review.',
                           flask.url_for('.display', iuid=review['_id']))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver.set_archived()
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/unarchive', methods=['POST'])
@utils.login_required
def unarchive(iuid):
    "Unarchive the review for the proposal. Requires 'delete' privilege."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such archived review.', flask.url_for('home'))
    if not allow_delete(review):
        return utils.error('You are not allowed to unarchive this review.',
                           flask.url_for('.display', iuid=review['_id']))
    if get_reviewer_review(anubis.proposal.get_proposal(review['proposal']),
                           anubis.user.get_user(review['reviewer'])):
        return utils.error('Unarchived review exists for proposal and reviewer.')

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver.set_unarchived()
        except ValueError as error:
            utils.flash_error(error)
        return flask.redirect(flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/logs')
@utils.login_required
def logs(iuid):
    "Display the log records of the review."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Review of {review['proposal']} by {review['reviewer']}",
        back_url=flask.url_for('.display', iuid=review['_id']),
        logs=utils.get_logs(review['_id']))

@blueprint.route('/<iuid:iuid>/document/<fid>')
@utils.login_required
def document(iuid, fid):
    "Download the review document (attachment file) for the given field id."
    try:
        review = get_review(iuid)
    except KeyError:
        return utils.error('No such review.', flask.url_for('home'))
    if not allow_view(review):
        return utils.error('You are not allowed to read this review.',
                           flask.url_for('home'))

    try:
        documentname = review['values'][fid]
        stub = review['_attachments'][documentname]
    except KeyError:
        return utils.error('No such document in review.',
                           flask.url_for('.display', iuid=review['identifier']))
    # Colon ':' is a problematic character in filenames.
    # Replace it by dash '-'; used as general glue character here.
    pid = review['proposal'].replace(':', '-')
    ext = os.path.splitext(documentname)[1]
    # Include reviewer id in filename to indicate review document.
    filename = f"{pid}-{review['reviewer']}-{fid}{ext}"
    outfile = flask.g.db.get_attachment(review, documentname)
    response = flask.make_response(outfile.read())
    response.headers.set('Content-Type', stub['content_type'])
    response.headers.set('Content-Disposition', 'attachment', filename=filename)
    return response


class ReviewSaver(FieldMixin, AttachmentSaver):
    "Review document saver context."

    DOCTYPE = constants.REVIEW

    def __init__(self, doc=None, proposal=None, user=None):
        if doc:
            super().__init__(doc=doc)
        elif proposal and user:
            super().__init__(doc=None)
            self.set_proposal(proposal)
            self.set_reviewer(user)
        else:
            raise ValueError('doc or proposal+user must be specified')

    def initialize(self):
        self['values'] = {}
        self['errors'] = {}

    def set_proposal(self, proposal):
        "Set the proposal for the review; must be called when creating."
        if self.doc.get('proposal'):
            raise ValueError('proposal has already been set')
        self['call'] = proposal['call']
        self['proposal'] = proposal['identifier']
        call = anubis.call.get_call(proposal['call'])
        self.set_fields_values(call['review'])

    def set_reviewer(self, user):
        "Set the reviewer for the review; must be called at creation."
        self['reviewer'] = user['username']

    def set_archived(self):
        "Archive this review; save the current field definitions."
        if self.doc.get('archived'): return
        call = anubis.call.get_call(self.doc['call'])
        self['fields'] = call['review']
        self['archived'] = True

    def set_unarchived(self):
        "Archive this review; save the current field definitions."
        if not self.doc.get('archived'): return
        self.doc.pop('archived', None)
        self.doc.pop('fields', None)


def get_review(iuid):
    "Get the review by its iuid."
    if not iuid: return None
    try:
        return flask.g.cache[iuid]
    except KeyError:
        review = flask.g.db[iuid]
        if review['doctype'] != constants.REVIEW: raise ValueError
        flask.g.cache[iuid] = review
        return review

def get_reviewer_review(proposal, reviewer=None):
    "Get the review of the proposal by the reviewer."
    if reviewer is None:
        reviewer = flask.g.current_user
    if reviewer is None: return None
    result = flask.g.db.view('reviews', 'proposal_reviewer',
                             key=[proposal['identifier'], reviewer['username']],
                             reduce=False,
                             include_docs=True)
    try:
        return result[0].doc
    except IndexError:
        return None

def allow_create(proposal):
    """The admin, call owner and chair may create a review
    for a submitted proposal.
    """
    if not proposal.get('submitted'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(proposal['call'])
    if anubis.call.am_chair(call) or anubis.call.am_call_owner(call): 
        return True
    return False

def allow_view(review):
    """The admin, staff and call owner may view any review in the call.
    The chair may view any review.
    Reviewer may view her own reviews.
    Reviewer may view all reviews depending on access flag for the call.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.am_staff: return True
    if flask.g.current_user['username'] == review['reviewer']: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_chair(call): return True
    if anubis.call.am_call_owner(call): return True
    if anubis.call.allow_view_reviews(call) and review.get('finalized'):
        return True
    return False

def allow_edit(review):
    "The admin, call owner and reviewer may edit an unfinalized review."
    if review.get('finalized'): return False
    if review.get('archived'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user['username'] == review['reviewer']: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_call_owner(call): return True
    return False

def allow_delete(review):
    "The admin and call owner may delete a review."
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_call_owner(call): return True
    return False

def allow_finalize(review):
    "The admin, call owner and reviewer may finalize if it contains no errors."
    if review.get('finalized'): return False
    if review.get('archived'): return False
    if review['errors']: return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if flask.g.current_user['username'] == review['reviewer']: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_call_owner(call): return True
    return False

def allow_unfinalize(review):
    """The admin and call owner may always unfinalize.
    Reviewer may unfinalize the review before reviews due date.
    """
    if not review.get('finalized'): return False
    if review.get('archived'): return False
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    call = anubis.call.get_call(review['call'])
    if anubis.call.am_call_owner(call): return True
    if call.get('reviews_due') and utils.days_remaining(call['reviews_due'])<0:
        return False
    if flask.g.current_user['username'] == review['reviewer']: return True
    return False
