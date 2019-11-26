"Review of a proposal. Created from the outline in the call."

import flask

import anubis.user
import anubis.proposal

from . import constants
from . import utils
from .saver import BaseSaver, FieldMixin


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    logger = utils.get_logger(app)
    if db.put_design('reviews', DESIGN_DOC):
        logger.info('Updated reviews design document.')

DESIGN_DOC = {
    'views': {
        'call': {'reduce': '_count',
                 'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.call, null);}"},
        'proposal': {'reduce': '_count',
                     'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.proposal, null);}"},
        'reviewer': {'reduce': '_count',
                     'map': "function(doc) {if (doc.doctype !== 'review') return; emit(doc.reviewer, null);}"},
        'call_reviewer': {'reduce': '_count',
                          'map': "function(doc) {if (doc.doctype !== 'review') return; emit([doc.call, doc.reviewer], null);}"},
        'proposal_reviewer': {'map': "function(doc) {if (doc.doctype !== 'review') return; emit([doc.proposal, doc.reviewer], null);}"},
    }
}

blueprint = flask.Blueprint('review', __name__)

@blueprint.route('/create/<pid>/<username>', methods=['POST'])
@utils.admin_required
def create(pid, username):
    "Create a new review for the proposal for the given reviewer."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
    elif user['username'] not in proposal['cache']['call']['reviewers']:
        utils.flash_error('User is not a reviewer in the call.')
    else:
        review = get_review(proposal, user)
        if review is not None:
            utils.flash_message('The review already exists.')
            return flask.redirect(
                flask.url_for('review.display', iuid=review['iuid']))
        with ReviewSaver(proposal=proposal) as saver:
            saver.set_reviewer(user)
        print('created review', saver.doc['_id'])
    return flask.redirect(
        flask.url_for('reviews.proposal', pid=proposal['identifier']))

@blueprint.route('/<iuid:iuid>')
@utils.login_required
def display(iuid):
    "Display the review for the proposal."
    try:
        review = set_review_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not review['cache']['is_readable']:
        utils.flash_error('You are not allowed to read this review.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template('review/display.html',
                                 review=review)

@blueprint.route('/<iuid:iuid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.login_required
def edit(iuid):
    "Edit the review for the proposal."
    try:
        review = set_review_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not review['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this review.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('review/edit.html',
                                     review=review)

    elif utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                for field in review['cache']['call']['review']:
                    saver.set_field_value(field, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.edit', iuid=review['_id']))
        return flask.redirect(
            flask.url_for('.display', iuid=review['_id']))

    elif utils.http_DELETE():
        utils.delete(review)
        utils.flash_message('Deleted review.')
        return flask.redirect(flask.url_for('home'))

@blueprint.route('/<iuid:iuid>/finalize', methods=['POST'])
@utils.login_required
def finalize(iuid):
    "Finalize the review for the proposal."
    try:
        review = set_review_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not review['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this review.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = utils.get_time()
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/unfinalize', methods=['POST'])
@utils.login_required
def unfinalize(iuid):
    "Unfinalize the review for the proposal."
    try:
        review = set_review_cache(flask.g.db.get(iuid))
    except KeyError:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not review['cache']['is_editable']:
        utils.flash_error('You are not allowed to edit this review.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with ReviewSaver(doc=review) as saver:
                saver['finalized'] = None
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.display', iuid=review['_id']))

@blueprint.route('/<iuid:iuid>/logs')
@utils.login_required
def logs(iuid):
    "Display the log records of the call."
    review = flask.g.db.get(iuid)
    if review is None:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))

    review = set_review_cache(review)
    return flask.render_template(
        'logs.html',
        title="Review of" \
              f" {review['cache']['proposal']['identifier']}" \
              f" by {review['reviewer']}",
        back_url=flask.url_for('.display', iuid=review['_id']),
        logs=utils.get_logs(review['_id']))

@blueprint.route('/<iuid:iuid>/document/<documentname>')
@utils.login_required
def document(iuid, documentname):
    "Download the given review document (attachment file)."
    review = get_review(iuid)
    if review is None:
        utils.flash_error('No such review.')
        return flask.redirect(flask.url_for('home'))
    if not review['cache']['is_readable']:
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
            self.doc['call'] = proposal['cache']['call']['identifier']
            self.doc['proposal'] = proposal['identifier']
        else:
            raise ValueError('doc or proposal must be specified')
        self.set_reviewer(flask.g.current_user)

    def initialize(self):
        self.doc['values'] = {}
        self.doc['errors'] = {}

    def set_reviewer(self, user):
        "Set the reviewer for the review; must be called at creation."
        self.doc['reviewer'] = user['username']


def get_review(proposal, reviewer):
    "Get the review of the proposal by the reviewer."
    result = flask.g.db.view('reviews', 'proposal_reviewer',
                             key=[proposal['identifier'], 
                                  reviewer['username']],
                             reduce=False,
                             include_docs=True)
    try:
        return set_review_cache(result[0].doc)
    except IndexError:
        return None

def get_reviews(call):
    "Get all reviews for proposals in a call."
    result = [set_review_cache(r.doc)
              for r in flask.g.db.view('reviews', 'call',
                                       key=call['identifier'],
                                       reduce=False,
                                       include_docs=True)]

def set_review_cache(review, call=None):
    """Set the'cache' field of the review.
    This is computed data that will not be stored with the document.
    Depends on login, access, status, etc.
    """
    from anubis.call import get_call
    from anubis.proposal import get_proposal
    review['cache'] = cache = dict(is_readable=False,
                                       is_editable=False)
    if call is None:
        cache['call'] = call = get_call(review['call'])
    else:
        cache['call'] = call
    cache['proposal'] = get_proposal(review['proposal'])
    if flask.g.is_admin:
        cache['is_readable'] = True
        cache['is_editable'] = True
    elif flask.g.current_user:
        cache['is_readable'] = flask.g.current_user['username'] == review['reviewer']
        cache['is_editable'] = flask.g.current_user['username'] == review['reviewer']
    return review
