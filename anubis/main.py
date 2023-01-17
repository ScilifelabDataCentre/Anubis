"Flask app setup and creation; main entry point.."

import http.client
import io

import flask
import markupsafe
import werkzeug.routing

import anubis.database
import anubis.display
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
import anubis.user

from anubis import constants
from anubis import utils

# The global Flask app.
app = flask.Flask(__name__)

# Hard-wired Flask configuration.
app.json.ensure_ascii = False
app.json.sort_keys = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = constants.SITE_FILE_MAX_AGE

# Configure Flask app from settings file and/or environment variables.
anubis.config.init(app)
anubis.utils.init(app)
anubis.display.init(app)


@app.before_first_request
def update_initialize():
    """The CLI cannot create a database if this code is executed when the app is
    created in the code above. That is why this code is in this special procedure
    which Flask executes once before handling the first request after starting up.
    - Update design document.
    - Update contents of db for version changes.
    - Get configuration values that are nowadays stored in the database.
    """
    anubis.database.update_design_documents()
    anubis.database.update()
    anubis.config.init_from_db()


# Add a custom converter to handle IUID URLs.
class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."

    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive


app.url_map.converters["iuid"] = IuidConverter


@app.context_processor
def setup_template_context():
    "Add to the global context of Jinja2 templates."
    return dict(
        enumerate=enumerate,
        range=range,
        sorted=sorted,
        len=len,
        min=min,
        max=max,
        constants=constants,
        csrf_token=utils.csrf_token,
        get_user=anubis.user.get_user,
        get_call=anubis.call.get_call,
        get_banner_fields=anubis.call.get_banner_fields,
        get_proposal=anubis.proposal.get_proposal,
        get_review=anubis.review.get_review,
        get_decision=anubis.decision.get_decision,
        get_grant=anubis.grant.get_grant,
        get_grant_proposal=anubis.grant.get_grant_proposal,
    )


@app.before_request
def prepare():
    "Set the database connection, get the current user."
    flask.g.db = anubis.database.get_db()
    flask.g.current_user = anubis.user.get_current_user()
    flask.g.am_admin = anubis.user.am_admin()
    flask.g.am_staff = anubis.user.am_staff()
    if flask.g.current_user:
        username = flask.g.current_user["username"]
        flask.g.allow_create_call = anubis.call.allow_create()
        flask.g.my_proposals_count = anubis.database.get_count(
            "proposals", "user", username
        )
        flask.g.my_unsubmitted_proposals_count = anubis.database.get_count(
            "proposals", "unsubmitted", username
        )
        flask.g.my_reviews_count = anubis.database.get_count(
            "reviews", "reviewer", username
        )
        flask.g.my_unfinalized_reviews_count = anubis.database.get_count(
            "reviews", "unfinalized", username
        )
        flask.g.my_grants_count = anubis.database.get_count(
            "grants", "user", username
        ) + anubis.database.get_count("grants", "access", username)
        flask.g.my_incomplete_grants_count = anubis.database.get_count(
            "grants", "incomplete", username
        )
        flask.g.orcid_require = (
            flask.current_app.config.get("USER_REQUEST_ORCID")
            and not (flask.g.am_admin or flask.g.am_staff)
            and not flask.g.current_user.get("orcid")
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


@app.route("/documentation")
def documentation():
    "Documentation page; the README page of the GitHub repo."
    return flask.render_template("documentation.html")


@app.route("/status")
def status():
    "Return JSON for the current status and some counts for the database."
    result = dict(status="ok")
    result.update(anubis.database.get_counts())
    return result


@app.route("/site/<filename>")
def site(filename):
    if filename in constants.SITE_FILES:
        try:
            filedata = flask.current_app.config[f"SITE_{filename.upper()}"]
            return flask.send_file(
                io.BytesIO(filedata["content"]),
                mimetype=filedata["mimetype"],
                etag=filedata["etag"],
                last_modified=filedata["modified"],
                max_age=constants.SITE_FILE_MAX_AGE,
            )
        except KeyError:
            pass
    flask.abort(http.client.NOT_FOUND)


@app.route("/sitemap")
def sitemap():
    "Return an XML sitemap."
    pages = [
        dict(url=flask.url_for("home", _external=True)),
        dict(url=flask.url_for("about.contact", _external=True)),
        dict(url=flask.url_for("about.software", _external=True)),
        dict(url=flask.url_for("calls.open", _external=True)),
        dict(url=flask.url_for("calls.closed", _external=True)),
    ]
    for call in anubis.calls.get_open_calls():
        pages.append(
            dict(
                url=flask.url_for(
                    "call.display", cid=call["identifier"], _external=True
                )
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


# This code is used only during development.
if __name__ == "__main__":
    app.run()
