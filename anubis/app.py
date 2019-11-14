"Web app template."

import flask

import anubis.about
import anubis.call
import anubis.calls
import anubis.config
import anubis.evaluation
import anubis.submission
import anubis.submissions
import anubis.site
import anubis.user

import anubis.api.about
import anubis.api.root
import anubis.api.schema
import anubis.api.user

from anubis import constants
from anubis import utils


app = flask.Flask(__name__)

# Get the configuration and initialize.
app.url_map.converters['iuid'] = utils.IuidConverter
anubis.config.init(app)
utils.mail.init_app(app)
app.add_template_filter(utils.thousands)
app.add_template_filter(utils.boolean_value)
app.add_template_filter(utils.integer_value)
app.add_template_filter(utils.float_value)
app.add_template_filter(utils.do_markdown, name='markdown')

@app.context_processor
def setup_template_context():
    "Add useful stuff to the global context of Jinja2 templates."
    return dict(constants=constants,
                utils=utils,
                csrf_token=utils.csrf_token,
                enumerate=enumerate,
                sorted=sorted)

@app.before_first_request
def init_database():
    "Get the database connection, and update the design document."
    flask.g.db = db = utils.get_db()
    logger = utils.get_logger()
    if db.put_design('logs', utils.LOGS_DESIGN_DOC):
        logger.info('Updated logs design document.')
    if db.put_design('users', anubis.user.USERS_DESIGN_DOC):
        logger.info('Updated users design document.')
    if db.put_design('calls', anubis.call.CALLS_DESIGN_DOC):
        logger.info('Updated calls design document.')
    if db.put_design('submissions', anubis.call.SUBMISSIONS_DESIGN_DOC):
        logger.info('Updated submissions design document.')
    if db.put_design('evaluations', anubis.call.EVALUATIONS_DESIGN_DOC):
        logger.info('Updated evaluations design document.')

@app.before_request
def prepare():
    "Open the database connection; get the current user."
    flask.g.dbserver = utils.get_dbserver()
    flask.g.db = utils.get_db(dbserver=flask.g.dbserver)
    flask.g.current_user = anubis.user.get_current_user()
    flask.g.is_admin = flask.g.current_user and \
                       flask.g.current_user['role'] == constants.ADMIN

app.after_request(utils.log_access)

@app.route('/')
def home():
    "Home page. Redirect to API root if JSON is accepted."
    if utils.accept_json():
        return flask.redirect(flask.url_for('api_root'))
    # The list is already properly sorted.
    return flask.render_template('home.html', 
                                 calls=anubis.calls.get_open_calls())

# Set up the URL map.
app.register_blueprint(anubis.user.blueprint, url_prefix='/user')
app.register_blueprint(anubis.call.blueprint, url_prefix='/call')
app.register_blueprint(anubis.calls.blueprint, url_prefix='/calls')
app.register_blueprint(anubis.submission.blueprint, url_prefix='/submission')
app.register_blueprint(anubis.submissions.blueprint, url_prefix='/submissions')
app.register_blueprint(anubis.evaluation.blueprint, url_prefix='/evaluation')
app.register_blueprint(anubis.about.blueprint, url_prefix='/about')
app.register_blueprint(anubis.site.blueprint, url_prefix='/site')

app.register_blueprint(anubis.api.root.blueprint, url_prefix='/api')
app.register_blueprint(anubis.api.about.blueprint, url_prefix='/api/about')
app.register_blueprint(anubis.api.schema.blueprint, url_prefix='/api/schema')
app.register_blueprint(anubis.api.user.blueprint, url_prefix='/api/user')


# This code is used only during development.
if __name__ == '__main__':
    app.run()
