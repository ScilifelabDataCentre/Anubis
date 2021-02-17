"Proposal review handling system."

import flask

import anubis.about
import anubis.call
import anubis.calls
import anubis.config
import anubis.review
import anubis.reviews
import anubis.proposal
import anubis.proposals
import anubis.decision
import anubis.grant
import anubis.grants
import anubis.site
import anubis.user

from anubis import constants
from anubis import utils

app = flask.Flask(__name__)

# Get the configuration and initialize modules.
anubis.config.init(app)
utils.init(app)
anubis.call.init(app)
anubis.proposal.init(app)
anubis.review.init(app)
anubis.decision.init(app)
anubis.grant.init(app)
anubis.user.init(app)

app.url_map.converters['iuid'] = utils.IuidConverter

@app.context_processor
def setup_template_context():
    "Add to the global context of Jinja2 templates."
    return dict(enumerate=enumerate,
                range=range,
                sorted=sorted,
                len=len,
                max=max,
                utils=utils,
                constants=constants,
                csrf_token=utils.csrf_token,
                get_user=anubis.user.get_user,
                get_call=anubis.call.get_call,
                get_proposal=anubis.proposal.get_proposal,
                get_review=anubis.review.get_review,
                get_decision=anubis.decision.get_decision,
                get_grant=anubis.grant.get_grant)

@app.before_request
def prepare():
    "Open the database connection, create the doc cache, get the current user."
    flask.g.db = utils.get_db()
    flask.g.cache = {}          # id or key -> document
    flask.g.current_user = anubis.user.get_current_user()
    flask.g.am_admin = anubis.user.am_admin()
    flask.g.am_staff = anubis.user.am_staff()
    if flask.g.current_user:
        username = flask.g.current_user['username']
        flask.g.my_calls_count = utils.get_count(
            'calls', 'owner', username)
        flask.g.my_proposals_count = utils.get_count(
            'proposals', 'user', username)
        flask.g.my_reviews_count = utils.get_count(
            'reviews', 'reviewer', username)
        flask.g.my_unsubmitted_proposals_count = utils.get_count(
            'proposals', 'unsubmitted', username)
        flask.g.my_unfinalized_reviews_count = utils.get_count(
            'reviews', 'unfinalized', username)
        flask.g.my_grants_count = utils.get_user_grants_count(username)
        flask.g.my_incomplete_grants_count = utils.get_count(
            'grants', 'incomplete', username)

@app.route('/')
def home():
    "Home page."
    # The list is already properly sorted.
    return flask.render_template('home.html', 
                                 calls=anubis.calls.get_open_calls(),
                                 allow_create_call=anubis.call.allow_create())

# Set up the URL map.
app.register_blueprint(anubis.user.blueprint, url_prefix='/user')
app.register_blueprint(anubis.call.blueprint, url_prefix='/call')
app.register_blueprint(anubis.calls.blueprint, url_prefix='/calls')
app.register_blueprint(anubis.proposal.blueprint, url_prefix='/proposal')
app.register_blueprint(anubis.proposals.blueprint, url_prefix='/proposals')
app.register_blueprint(anubis.review.blueprint, url_prefix='/review')
app.register_blueprint(anubis.reviews.blueprint, url_prefix='/reviews')
app.register_blueprint(anubis.decision.blueprint, url_prefix='/decision')
app.register_blueprint(anubis.grant.blueprint, url_prefix='/grant')
app.register_blueprint(anubis.grants.blueprint, url_prefix='/grants')
app.register_blueprint(anubis.about.blueprint, url_prefix='/about')
app.register_blueprint(anubis.site.blueprint, url_prefix='/site')


# This code is used only during development.
if __name__ == '__main__':
    app.run()
