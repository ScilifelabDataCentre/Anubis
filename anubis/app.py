"Flask app setup and creation; main entry point.."

import base64
import http.client
import io
import os.path

import flask
import flask_mail
import markupsafe
import pytz
import werkzeug.routing

import anubis.database
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

# The global Flask app.
app = flask.Flask(__name__)
app.logger.info(f"Anubis version {constants.VERSION}")

# Config Flask app from settings file and/or environment variables.
anubis.config.init(app)

# Hard-wired Flask config.
app.json.ensure_ascii = False
app.json.sort_keys = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = constants.SITE_FILE_MAX_AGE
app.jinja_env.add_extension("jinja2.ext.loopcontrols")
app.jinja_env.add_extension("jinja2.ext.do")

# Global instance of the mail interface.
mail = flask_mail.Mail()
mail.init_app(app)

# Add a custom converter to handle IUID URLs.
class IuidConverter(werkzeug.routing.BaseConverter):
    "URL route converter for a IUID."
    def to_python(self, value):
        if not constants.IUID_RX.match(value):
            raise werkzeug.routing.ValidationError
        return value.lower()  # Case-insensitive

app.url_map.converters["iuid"] = IuidConverter

with app.app_context():
    # Ensure the design documents in the database are current.
    anubis.database.update_design_documents()
    anubis.doc.init()  # XXX To be refactored away.
    # Update the database to this version.
    anubis.database.update()
    # Get config values that nowadays are stored in the database.
    anubis.config.init_from_db()


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
        utils=utils,
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
        flask.g.my_proposals_count = anubis.database.get_count("proposals", "user", username)
        flask.g.my_unsubmitted_proposals_count = anubis.database.get_count(
            "proposals", "unsubmitted", username
        )
        flask.g.my_reviews_count = anubis.database.get_count("reviews", "reviewer", username)
        flask.g.my_unfinalized_reviews_count = anubis.database.get_count(
            "reviews", "unfinalized", username
        )
        flask.g.my_grants_count = (
            anubis.database.get_count("grants", "user", username) +
            anubis.database.get_count("grants", "access", username)
        )
        flask.g.my_incomplete_grants_count = anubis.database.get_count(
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
    return dict(
        status="ok",
        n_calls = anubis.database.get_count("calls", "owner"),
        n_users = anubis.database.get_count("users", "username"),
        n_proposals = anubis.database.get_count("proposals", "call"),
        n_reviews = anubis.database.get_count("reviews", "call"),
        n_grants = anubis.database.get_count("grants", "call")
    )


@app.route("/site/<filename>")
def site(filename):
    if filename in constants.SITE_FILES:
        try:
            filedata = flask.current_app.config[f"SITE_{filename.upper()}"]
            return flask.send_file(io.BytesIO(filedata["content"]),
                                   mimetype=filedata["mimetype"],
                                   etag=filedata["etag"],
                                   last_modified=filedata["modified"],
                                   max_age=constants.SITE_FILE_MAX_AGE)
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
                url=flask.url_for("call.display", cid=call["identifier"], _external=True))
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


@app.template_filter()
def display_markdown(value):
    "Process the value from Markdown to HTML."
    return markupsafe.Markup(utils.markdown2html(value))


@app.template_filter()
def display_field_value(field, entity, fid=None, max_length=None, show_user=False):
    """Display field value according to its type.
    max_length: Truncate document name to given number of characters.
    show_user: Show user link if email address is an account, and admin or staff.
    """
    # Repeated field needs to pass its actual id explicitly.
    if not fid:
        fid = field["identifier"]
    value = entity.get("values", {}).get(fid)
    if field["type"] == constants.LINE:
        return value or "-"
    elif field["type"] == constants.EMAIL:
        if not value:
            return "-"
        if show_user and (flask.g.am_admin or flask.g.am_staff):
            user = anubis.user.get_user(email=value)
            if user:
                return value + " (" + user_link(user) + ")"
        return value
    elif field["type"] == constants.BOOLEAN:
        return display_boolean(value)
    elif field["type"] == constants.SELECT:
        if value is None:
            return "-"
        elif isinstance(value, list):
            return "; ".join(value)
        else:
            return value
    elif field["type"] in (constants.INTEGER, constants.SCORE, constants.RANK):
        if value is None:
            return "-"
        elif isinstance(value, int):
            return "{:,}".format(value)  # Thousands marker.
        else:
            return "?"
    elif field["type"] == constants.FLOAT:
        if value is None:
            return "-"
        elif isinstance(value, (int, float)):
            return "%.2f" % float(value)
        else:
            return "?"
    elif field["type"] == constants.TEXT:
        return display_markdown(value)
    elif field["type"] == constants.DOCUMENT:
        if value:
            if entity["doctype"] == constants.PROPOSAL:
                docurl = flask.url_for(
                    "proposal.document", pid=entity["identifier"], fid=fid
                )
            elif entity["doctype"] == constants.REVIEW:
                docurl = flask.url_for("review.document", iuid=entity["_id"], fid=fid)
            elif entity["doctype"] == constants.DECISION:
                docurl = flask.url_for("decision.document", iuid=entity["_id"], fid=fid)
            elif entity["doctype"] == constants.GRANT:
                docurl = flask.url_for(
                    "grant.document", gid=entity["identifier"], fid=fid
                )
            if max_length:
                if len(value) > max_length:
                    value = value[:max_length] + "..."
            return markupsafe.Markup(
                f'<i title="File" class="align-top">{value}</i> <a href="{docurl}"'
                ' role="button" title="Download file"'
                ' class="btn btn-dark btn-sm ml-4">Download</a>'
            )
        else:
            return "-"
    elif field["type"] == constants.REPEAT:
        return display_value(value)
    else:
        raise ValueError(f"unknown field type: {field['type']}")


@app.template_filter()
def display_value(value, default="-"):
    "Display the value if not None, else the default."
    if value is None:
        return default
    else:
        return value


@app.template_filter()
def display_datetime_timezone(value, due=False, tz=True, dash=True):
    """Convert UTC datetime ISO string to the timezone of the site.
    Optionally output warning for approaching due date, and the timezone.
    """
    if value:
        dts = utils.timezone_from_utc_isoformat(value, tz=tz)
        if due:
            remaining = utils.days_remaining(value)
            if remaining > flask.current_app.config["CALL_REMAINING_WARNING"]:
                return dts
            elif remaining >= flask.current_app.config["CALL_REMAINING_DANGER"]:
                return markupsafe.Markup(
                    f'{dts} <div class="badge badge-warning ml-2">'
                    f"{remaining:.1f} days until due.</div>"
                )
            elif remaining >= 0:
                return markupsafe.Markup(
                    f'{dts} <div class="badge badge-danger ml-2">'
                    f"{remaining:.1f} days until due.</div>"
                )
            else:
                return markupsafe.Markup(
                    f'{dts} <div class="badge badge-danger ml-2">Overdue!</div>'
                )
        else:
            return dts
    elif dash:
        return "-"
    return ""


@app.template_filter()
def display_boolean(value):
    "Display field value boolean."
    if value is None:
        return "-"
    elif value:
        return "Yes"
    else:
        return "No"


@app.template_filter()
def user_link(user, fullname=True, affiliation=False):
    "User by name, with link if allowed to view. Optionally output affiliation."
    if fullname:
        name = anubis.user.get_fullname(user)
    else:
        name = user["username"]
    if affiliation:
        name += f" [{user.get('affiliation') or '-'}]"
    if anubis.user.allow_view(user):
        url = flask.url_for("user.display", username=user["username"])
        return markupsafe.Markup(f'<a href="{url}">{name}</a>')
    else:
        return markupsafe.Markup(name)


@app.template_filter()
def call_link(
    call, identifier=True, title=False, proposals_link=True, grants_link=False
):
    "Link to call and optionally links to all its proposals and grants."
    label = []
    if identifier:
        label.append(call["identifier"])
    if title and call["title"]:
        label.append(call["title"])
    label = " ".join(label) or call["identifier"]
    url = flask.url_for("call.display", cid=call["identifier"])
    html = f'<a href="{url}" class="font-weight-bold">{label}</a>'
    if proposals_link:
        count = anubis.database.get_count("proposals", "call", call["identifier"])
        url = flask.url_for("proposals.call", cid=call["identifier"])
        html += (
            f' <a href="{url}" class="badge badge-primary mx-2">{count} proposals</a>'
        )
    if grants_link:
        count = anubis.database.get_count("grants", "call", call["identifier"])
        url = flask.url_for("grants.call", cid=call["identifier"])
        html += f' <a href="{url}" class="badge badge-success mx-2">{count} grants</a>'
    return markupsafe.Markup(html)


@app.template_filter()
def call_proposals_link(call, full=False):
    "Button with link to the page of all proposals in the call."
    if not anubis.call.allow_view_proposals(call):
        return ""
    count = anubis.database.get_count("proposals", "call", call["identifier"])
    url = flask.url_for("proposals.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-primary">{count} {full and "proposals" or "" }</a>'
    return markupsafe.Markup(html)


@app.template_filter()
def call_reviews_link(call, full=False):
    "Button with link to the page of all reviews in the call."
    if not anubis.call.allow_view_reviews(call):
        return ""
    count = anubis.database.get_count("reviews", "call", call["identifier"])
    url = flask.url_for("reviews.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-info">{count} {full and "reviews" or ""}</a>'
    return markupsafe.Markup(html)


@app.template_filter()
def call_grants_link(call, full=False):
    "Button with link to the page of all grants in the call."
    if not anubis.call.allow_view_grants(call):
        return ""
    count = anubis.database.get_count("grants", "call", call["identifier"])
    url = flask.url_for("grants.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-success">{count} {full and "grants" or ""}</a>'
    return markupsafe.Markup(html)


@app.template_filter()
def proposal_link(proposal):
    "Link to proposal."
    if not proposal:
        return "-"
    url = flask.url_for("proposal.display", pid=proposal["identifier"])
    title = proposal.get("title") or "[No title]"
    html = f'''<a href="{url}" title="{title}">{proposal['identifier']} {title}</a>'''
    return markupsafe.Markup(html)


@app.template_filter()
def review_link(review):
    "Link to review."
    if not review:
        return "-"
    url = flask.url_for("review.display", iuid=review["_id"])
    html = f"""<a href="{url}" class="text-info">Review """
    if review.get("archived"):
        html += '<span class="badge badge-pill badge-secondary">Archived</span>'
    elif review.get("finalized"):
        html += '<span class="badge badge-pill badge-success">Finalized</span>'
    else:
        html += '<span class="badge badge-pill badge-warning">Not finalized</span>'
    html += "</a>"
    return markupsafe.Markup(html)


@app.template_filter()
def decision_link(decision, small=False):
    "Link to decision."
    if not decision:
        return "-"
    url = flask.url_for("decision.display", iuid=decision["_id"])
    if decision.get("finalized"):
        if decision.get("verdict"):
            color = "btn-success font-weight-bold"
            label = "Accepted"
        else:
            color = "btn-secondary font-weight-bold"
            label = "Declined"
    else:
        if decision.get("verdict"):
            color = "btn-outline-success font-weight-bold"
            label = "Accepted"
        elif decision.get("verdict") == False:
            color = "btn-outline-secondary font-weight-bold"
            label = "Declined"
        else:
            color = "btn-warning"
            label = "Undecided"
    if small:
        color += " btn-sm"
    else:
        color += " my-1"
    return markupsafe.Markup(
        f"""<a href="{url}" role="button" class="btn {color}">""" f"{label}</a>"
    )


@app.template_filter()
def grant_link(grant, small=False, status=False):
    "Link to grant, optionally with status marker."
    if not grant:
        return "-"
    url = flask.url_for("grant.display", gid=grant["identifier"])
    color = "btn-success font-weight-bold"
    if small:
        color += " btn-sm"
    label = f"Grant {grant['identifier']}"
    if status:
        if grant["errors"]:
            label += ' <span class="badge badge-danger ml-2">Incomplete</span>'
    return markupsafe.Markup(
        f'<a href="{url}" role="button"' f' class="btn {color} my-1">{label}</a>'
    )



# This code is used only during development.
if __name__ == "__main__":
    app.run()
