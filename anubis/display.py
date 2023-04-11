"Jinja2 setup and template filters."

import flask
import markupsafe

from anubis import constants
from anubis import utils

import anubis.database
import anubis.call
import anubis.user


def init(app):
    app.jinja_env.add_extension("jinja2.ext.loopcontrols")
    app.jinja_env.add_extension("jinja2.ext.do")
    for func in [
        display_markdown,
        display_field_value,
        display_value,
        display_datetime_timezone,
        call_closes_badge,
        reviews_due_badge,
        user_link,
        users_links_list,
        call_link,
        call_proposals_link,
        call_reviews_link,
        call_grants_link,
        proposal_link,
        review_link,
        review_status,
        decision_link,
        grant_link,
    ]:
        app.jinja_env.filters[func.__name__] = func


def display_markdown(value):
    "Process the value from Markdown to HTML."
    return markupsafe.Markup(utils.markdown2html(value))


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
        if value is None:
            return "-"
        else:
            return value and "Yes" or "No"
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


def display_value(value, default="-"):
    "Display the value if not None, else the default."
    if value is None:
        return default
    else:
        return value


def display_datetime_timezone(value, plain=False):
    """Return the datetime in the local timezone for the given UTC datetime ISO string.
    'plain' is for output as the value of an HTML input field.
    By default, the name of the timezone is included.
    By default, an undefined values is show as a dash.
    """
    if value:
        result = utils.timezone_from_utc_isoformat(value, tz=not plain)
        if not plain:
            result = f'<span class="text-nowrap">{result}</span>'
    elif plain:
        result = ""
    else:
        result = "-"
    return markupsafe.Markup(result)


def call_closes_badge(call):
    "Return a badge highlighting the implication of the closes date of the call."
    if anubis.call.is_open(call):
        remaining = utils.days_remaining(call["closes"])
        if remaining > flask.current_app.config["CALL_REMAINING_WARNING"]:
            result = (
                f'<div class="badge badge-pill badge-success mx-2">'
                f"{remaining:.0f} days remaining.</div>"
            )
        elif remaining >= flask.current_app.config["CALL_REMAINING_DANGER"]:
            result = (
                f'<div class="badge badge-pill badge-warning mx-2">'
                f"{remaining:.0f} days remaining.</div>"
            )
        elif remaining > 3.0 / 24.0:
            result = (
                f'<div class="badge badge-pill badge-danger mx-2">'
                f"{24*remaining:.0f} hours remaining.</div>"
            )
        elif remaining >= 0:
            result = (
                f'<div class="badge badge-pill badge-danger mx-2">'
                f"{24*remaining:.1f} hours remaining.</div>"
            )
    elif anubis.call.is_closed(call):
        result = f'<div class="badge badge-pill badge-dark mx-2">Closed.</div>'
    else:
        result = ""
    return markupsafe.Markup(result)


def reviews_due_badge(call):
    "Return a badge highlighting the implication of the reviews due date of the call."
    if call.get("reviews_due"):
        remaining = utils.days_remaining(call["reviews_due"])
        if remaining > 7.0:
            result = f'<div class="badge badge-pill badge-success mx-2">{remaining:.0f} days remaining.</div>'
        elif remaining >= 1.0:
            result = f'<div class="badge badge-pill badge-warning mx-2">{remaining:.0f} days remaining.</div>'
        elif remaining >= 0:
            result = f'<div class="badge badge-pill badge-danger mx-2">{24*remaining:.1f} hours remaining.</div>'
        else:
            result = f'<div class="badge badge-pill badge-danger mx-2">Overdue!</div>'
    else:
        result = ""
    return markupsafe.Markup(result)


def user_link(user, fullname=True, affiliation=False, button=False):
    "User by name, with link if allowed to view. Optionally output affiliation."
    if fullname:
        name = anubis.user.get_fullname(user)
    else:
        name = user["username"]
    if affiliation:
        name += f" [{user.get('affiliation') or '-'}]"
    if anubis.user.allow_view(user):
        url = flask.url_for("user.display", username=user["username"])
        if button:
            return markupsafe.Markup(f'<a href="{url}" role="button" class="btn btn-outline-secondary my-2 my-sm-0">{name}</a>')
        else:
            return markupsafe.Markup(f'<a href="{url}">{name}</a>')
    else:
        return markupsafe.Markup(name)


def users_links_list(usernames):
    "List of links to users."
    users = []
    for username in sorted(usernames):
        user = anubis.user.get_user(username)
        if not user:
            continue
        name = anubis.user.get_fullname(user)
        if anubis.user.allow_view(user):
            url = flask.url_for("user.display", username=user["username"])
            users.append(f'<a href="{url}">{name}</a>')
        else:
            users.append(name)
    if users:
        return markupsafe.Markup(", ".join(users))
    else:
        return "-"


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
        html += f' <a href="{url}" role="button" class="badge badge-success mx-2">{count} grants</a>'
    return markupsafe.Markup(html)


def call_proposals_link(call, full=False):
    "Button with link to the page of all proposals in the call."
    if not anubis.call.allow_view_proposals(call):
        return ""
    count = anubis.database.get_count("proposals", "call", call["identifier"])
    url = flask.url_for("proposals.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-primary">{count} {full and "proposals" or "" }</a>'
    return markupsafe.Markup(html)


def call_reviews_link(call, full=False):
    "Button with link to the page of all reviews in the call."
    if not anubis.call.allow_view_reviews(call):
        return ""
    count = anubis.database.get_count("reviews", "call", call["identifier"])
    url = flask.url_for("reviews.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-info">{count} {full and "reviews" or ""}</a>'
    return markupsafe.Markup(html)


def call_grants_link(call, full=False):
    "Button with link to the page of all grants in the call."
    if not anubis.call.allow_view_grants(call):
        return ""
    count = anubis.database.get_count("grants", "call", call["identifier"])
    url = flask.url_for("grants.call", cid=call["identifier"])
    html = f' <a href="{url}" role="button" class="btn btn-sm btn-success">{count} {full and "grants" or ""}</a>'
    return markupsafe.Markup(html)


def proposal_link(proposal):
    "Link to proposal."
    if not proposal:
        return "-"
    url = flask.url_for("proposal.display", pid=proposal["identifier"])
    title = proposal.get("title") or "[No title]"
    html = f"""<a href="{url}" title="{title}">{proposal['identifier']} {title}</a>"""
    return markupsafe.Markup(html)


def review_link(review):
    "Link to review."
    if review:
        url = flask.url_for("review.display", iuid=review["_id"])
        return markupsafe.Markup(f"""<a href="{url}" class="text-info">Review</a>""")
    else:
        return "-"


def review_status(review):
    "Display the status of the review."
    if not review:
        result = "-"
    elif review.get("archived"):
        result = '<span class="badge badge-pill badge-secondary">Archived</span>'
    elif review.get("finalized"):
        if review["values"].get("conflict_of_interest"):
            result = '<span title="Conflict Of Interest declared." class="badge badge-pill badge-danger">Finalized; COI</span>'
        else:
            result = '<span class="badge badge-pill badge-success">Finalized</span>'
    else:
        result = '<span class="badge badge-pill badge-warning">Not finalized</span>'
    return markupsafe.Markup(result)


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
