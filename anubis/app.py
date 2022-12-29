"Flask app setup and creation; main entry point.."

import flask
from werkzeug.middleware.proxy_fix import ProxyFix

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
import anubis.about
import anubis.admin
import anubis.doc
import anubis.user

from anubis import constants
from anubis import utils

app = flask.Flask(__name__)

# Get the configuration.
anubis.config.init(app)
app.url_map.converters["iuid"] = utils.IuidConverter
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
app.jinja_env.add_extension("jinja2.ext.do")
if app.config["REVERSE_PROXY"]:
    app.wsgi_app = ProxyFix(app.wsgi_app)


@app.context_processor
def setup_template_context():
    "Add to the global context of Jinja2 templates."
    return dict(
        enumerate=enumerate,
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
        get_grant=anubis.grant.get_grant,
        get_grant_proposal=anubis.grant.get_grant_proposal,
    )


@app.before_first_request
def initialize():
    """Initialization before handling the first request.
    1) Load the design documents.
    2) Load the documentation files.
    3) Update the database.
    4) Set the database connection and cache.
    """
    app = flask.current_app
    utils.init(app)
    utils.load_design_documents(app)
    anubis.doc.init(app)
    utils.update_db(app)
    utils.set_db(app)


@app.before_request
def prepare():
    "Set the database connection, get the current user."
    utils.set_db()
    flask.g.current_user = anubis.user.get_current_user()
    flask.g.am_admin = anubis.user.am_admin()
    flask.g.am_staff = anubis.user.am_staff()
    if flask.g.current_user:
        username = flask.g.current_user["username"]
        flask.g.allow_create_call = anubis.call.allow_create()
        flask.g.my_proposals_count = utils.get_count("proposals", "user", username)
        flask.g.my_unsubmitted_proposals_count = utils.get_count(
            "proposals", "unsubmitted", username
        )
        flask.g.my_reviews_count = utils.get_count("reviews", "reviewer", username)
        flask.g.my_unfinalized_reviews_count = utils.get_count(
            "reviews", "unfinalized", username
        )
        flask.g.my_grants_count = utils.get_user_grants_count(username)
        flask.g.my_incomplete_grants_count = utils.get_count(
            "grants", "incomplete", username
        )


@app.route("/")
def home():
    "Home page."
    # The list is already properly sorted.
    return flask.render_template(
        "home.html",
        calls=anubis.calls.get_open_calls(),
        allow_create_call=anubis.call.allow_create(),
    )


@app.route("/status")
def status():
    "Return JSON for the current status and some counts for the database."
    return utils.get_counts()


@app.route("/sitemap")
def sitemap():
    "Return an XML sitemap."
    pages = [
        dict(
            url=flask.url_for("home", _external=True), changefreq="daily", priority=1.0
        ),
        dict(url=flask.url_for("about.contact", _external=True), changefreq="yearly"),
        dict(url=flask.url_for("about.software", _external=True), changefreq="yearly"),
        dict(
            url=flask.url_for("calls.open", _external=True),
            changefreq="daily",
            priority=1.0,
        ),
        dict(
            url=flask.url_for("calls.closed", _external=True),
            changefreq="daily",
            priority=0.1,
        ),
    ]
    for call in anubis.calls.get_open_calls():
        pages.append(
            dict(
                url=flask.url_for(
                    "call.display", cid=call["identifier"], _external=True
                ),
                changefreq="daily",
                priority=0.8,
            )
        )
    xml = flask.render_template("sitemap.xml", pages=pages)
    response = flask.current_app.make_response(xml)
    response.mimetype = constants.XML_MIMETYPE
    return response


# Set up the URL map.
app.register_blueprint(anubis.user.blueprint, url_prefix="/user")
app.register_blueprint(anubis.call.blueprint, url_prefix="/call")
app.register_blueprint(anubis.calls.blueprint, url_prefix="/calls")
app.register_blueprint(anubis.proposal.blueprint, url_prefix="/proposal")
app.register_blueprint(anubis.proposals.blueprint, url_prefix="/proposals")
app.register_blueprint(anubis.review.blueprint, url_prefix="/review")
app.register_blueprint(anubis.reviews.blueprint, url_prefix="/reviews")
app.register_blueprint(anubis.decision.blueprint, url_prefix="/decision")
app.register_blueprint(anubis.grant.blueprint, url_prefix="/grant")
app.register_blueprint(anubis.grants.blueprint, url_prefix="/grants")
app.register_blueprint(anubis.about.blueprint, url_prefix="/about")
app.register_blueprint(anubis.admin.blueprint, url_prefix="/admin")
app.register_blueprint(anubis.doc.blueprint, url_prefix="/documentation")


# This code is used only during development.
if __name__ == "__main__":
    app.run()
