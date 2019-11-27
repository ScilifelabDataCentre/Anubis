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
import anubis.site
import anubis.user

from anubis import constants
from anubis import utils

app = flask.Flask(__name__)

# Get the configuration and initialize modules (database).
anubis.config.init(app)

app.url_map.converters['iuid'] = utils.IuidConverter

utils.init(app)
anubis.call.init(app)
anubis.proposal.init(app)
anubis.review.init(app)
anubis.user.init(app)
utils.mail.init_app(app)

app.add_template_filter(utils.thousands)
app.add_template_filter(utils.value_or_none)
app.add_template_filter(utils.boolean_value)
app.add_template_filter(utils.integer_value)
app.add_template_filter(utils.float_value)
app.add_template_filter(utils.do_markdown, name='markdown')

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                csrf_token=utils.csrf_token,
                enumerate=enumerate,
                sorted=sorted)

@app.before_request
def prepare():
    "Open the database connection; get the current user."
    flask.g.db = utils.get_db()
    flask.g.current_user = anubis.user.get_current_user()
    flask.g.is_admin = flask.g.current_user and \
                       flask.g.current_user['role'] == constants.ADMIN

app.after_request(utils.log_access)

@app.route('/')
def home():
    "Home page."
    # The list is already properly sorted.
    return flask.render_template('home.html', 
                                 calls=anubis.calls.get_open_calls())

# Set up the URL map.
app.register_blueprint(anubis.user.blueprint, url_prefix='/user')
app.register_blueprint(anubis.call.blueprint, url_prefix='/call')
app.register_blueprint(anubis.calls.blueprint, url_prefix='/calls')
app.register_blueprint(anubis.proposal.blueprint, url_prefix='/proposal')
app.register_blueprint(anubis.proposals.blueprint, url_prefix='/proposals')
app.register_blueprint(anubis.review.blueprint, url_prefix='/review')
app.register_blueprint(anubis.reviews.blueprint, url_prefix='/reviews')
app.register_blueprint(anubis.about.blueprint, url_prefix='/about')
app.register_blueprint(anubis.site.blueprint, url_prefix='/site')


# This code is used only during development.
if __name__ == '__main__':
    app.run()
