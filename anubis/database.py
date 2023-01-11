"CouchDB operations."

import couchdb2
import flask

from anubis import constants
from anubis import utils
from anubis.saver import Saver


class MetaSaver(Saver):
    "Meta document saver context handler."

    DOCTYPE = constants.META

    def add_log(self):
        "No log entries for meta documents."
        pass


def get_server():
    "Get a connection to the CouchDB server."
    return couchdb2.Server(
        href=flask.current_app.config["COUCHDB_URL"],
        username=flask.current_app.config["COUCHDB_USERNAME"],
        password=flask.current_app.config["COUCHDB_PASSWORD"],
    )


def get_db():
    "Get a connection to the database."
    return get_server()[flask.current_app.config["COUCHDB_DBNAME"]]


def update_design_documents():
    "Ensure that all CouchDB design documents are up to date."
    db = get_db()
    app = flask.current_app
    if db.put_design("calls", CALLS_DESIGN_DOC):
        app.logger.info("Updated calls design document.")
    if db.put_design("proposals", PROPOSALS_DESIGN_DOC):
        app.logger.info("Updated proposals design document.")
    if db.put_design("reviews", REVIEWS_DESIGN_DOC):
        app.logger.info("Updated reviews design document.")
    if db.put_design("decisions", DECISIONS_DESIGN_DOC):
        app.logger.info("Updated decisions design document.")
    if db.put_design("grants", GRANTS_DESIGN_DOC):
        app.logger.info("Updated grants design document.")
    if db.put_design("users", USERS_DESIGN_DOC):
        app.logger.info("Updated users design document.")
    if db.put_design("logs", LOGS_DESIGN_DOC):
        app.logger.info("Updated logs design document.")
    if db.put_design("meta", META_DESIGN_DOC):
        app.logger.info("Updated meta design document.")


def get_doc(identifier):
    """Get the database document by identifier, else None.
    The identifier may be an account email, account API key, file name, info name,
    order identifier, or '_id' of the CouchDB document.
    """
    if not identifier:  # If empty string, database info is returned.
        return None
    for designname, viewname in [
        ("users", "username"),
        ("users", "email"),
        ("users", "orcid"),
        ("calls", "identifier"),
        ("proposals", "identifier"),
        ("grants", "identifier"),
    ]:
        try:
            view = flask.g.db.view(
                designname, viewname, key=identifier, reduce=False, include_docs=True
            )
            result = list(view)
            if len(result) == 1:
                return result[0].doc
        except KeyError:
            pass
    try:
        return flask.g.db[identifier]
    except couchdb2.NotFoundError:
        return None


def get_docs(designname, viewname, key):
    "Get the documents from the view. Add them to the cache."
    result = [
        r.doc for r in flask.g.db.view(designname, viewname, key=key, include_docs=True)
    ]
    for doc in result:
        if doc.get("doctype") == constants.CALL:
            utils.cache_put(f"call {doc['identifier']}", doc)
        elif doc.get("doctype") == constants.PROPOSAL:
            utils.cache_put(f"proposal {doc['identifier']}", doc)
        elif doc.get("doctype") == constants.REVIEW:
            utils.cache_put(f"review {doc['_id']}", doc)
        elif doc.get("doctype") == constants.DECISION:
            utils.cache_put(f"decision {doc['_id']}", doc)
        elif doc.get("doctype") == constants.GRANT:
            utils.cache_put(f"grant {doc['identifier']}", doc)
        elif doc.get("doctype") == constants.USER:
            utils.cache_put(f"username {doc['username']}", doc)
            if doc["email"]:
                utils.cache_put(f"email {doc['email']}", doc)
            if doc.get("orcid"):
                utils.cache_put(f"orcid {doc['orcid']}", doc)
    return result


def get_count(designname, viewname, key=None):
    "Get the count for the given view and key."
    if key is None:
        result = flask.g.db.view(designname, viewname, reduce=True)
    else:
        result = flask.g.db.view(designname, viewname, key=key, reduce=True)
    if result:
        return result[0].value
    else:
        return 0


def get_counts():
    "Get the total number of some entities."
    return dict(
        n_calls=get_count("calls", "owner"),
        n_users=get_count("users", "username"),
        n_proposals=get_count("proposals", "call"),
        n_reviews=get_count("reviews", "call"),
        n_grants=get_count("grants", "call"),
    )


def get_logs(docid, cleanup=True):
    """Return the list of log entries for the given document identifier,
    sorted by reverse timestamp.
    """
    result = [
        r.doc
        for r in flask.g.db.view(
            "logs",
            "doc",
            startkey=[docid, "ZZZZZZ"],
            endkey=[docid],
            descending=True,
            include_docs=True,
        )
    ]
    # Remove irrelevant entries, if requested.
    if cleanup:
        for log in result:
            for key in ["_id", "_rev", "doctype", "docid"]:
                log.pop(key)
    return result


def delete(doc):
    """Delete the given document and all its log entries.
    NOTE: This implementation should be fast, but leaves the deleted documents
    in CouchDB. These are removed whenever a database compaction is done.
    """
    for log in get_logs(doc["_id"], cleanup=False):
        flask.g.db.delete(log)
    flask.g.db.delete(doc)


def update():
    "Update the contents of the database for changes in new version(s)."
    db = get_db()
    app = flask.current_app

    # Change all stored datetimes (call opens, closes, reviews_due) to UTC ISO format.
    calls = [row.doc for row in db.view("calls", "identifier", include_docs=True)]
    for call in calls:
        changed = False
        for key in ["opens", "closes", "reviews_due"]:
            try:
                value = call[key]
                if not value:
                    raise KeyError
            except KeyError:
                pass
            else:
                if "Z" not in value:  # Not in UTC; then it is in TIMEZONE.
                    changed = True
                    call[key] = utc_from_timezone_isoformat(value)
        if changed:
            app.logger.info(f"Updated call {call['identifier']} document.")
            db.put(call)

    # Add a meta document for 'data_policy' text.
    if "data_policy" not in db:
        try:
            filepath = os.path.normpath(
                os.path.join(constants.ROOT, "../site", "gdpr.md")
            )
            with open(filepath) as infile:
                text = infile.read()
        except OSError:
            text = None
        with MetaSaver(id="data_policy", db=db) as saver:
            saver["text"] = text

    # Add a meta document for 'contact' text.
    if "contact" not in db:
        try:
            filepath = os.path.normpath(
                os.path.join(constants.ROOT, "../site", "contact.md")
            )
            with open(filepath) as infile:
                text = infile.read()
        except OSError:
            text = None
        with MetaSaver(id="contact", db=db) as saver:
            saver["text"] = text

    # Add a meta document for site configuration.
    if "site_configuration" not in db:
        with MetaSaver(id="site_configuration", db=db) as saver:
            saver["name"] = app.config.get("SITE_NAME") or "Anubis"
            saver["description"] = (
                app.config.get("SITE_DESCRIPTION")
                or "Submit proposals for grants in open calls."
            )
            saver["host_name"] = app.config.get("HOST_NAME")
            saver["host_url"] = app.config.get("HOST_URL")
            if app.config.get("SITE_STATIC_DIR"):
                dirpath = app.config.get("SITE_STATIC_DIR")
            else:
                dirpath = os.path.normpath(
                    os.path.join(constants.ROOT, "../site/static")
                )
            # Attach the site name logo file, if any.
            if app.config.get("SITE_LOGO"):
                path = os.path.join(dirpath, app.config["SITE_LOGO"])
                mimetype = mimetypes.guess_type(path)[0]
                try:
                    with open(path, "rb") as infile:
                        data = infile.read()
                    saver.add_attachment("name_logo", data, mimetype)
                except OSError:
                    pass
            # Attach the host logo file, if any.
            if app.config.get("HOST_LOGO"):
                path = os.path.join(dirpath, app.config["HOST_LOGO"])
                mimetype = mimetypes.guess_type(path)[0]
                try:
                    with open(path, "rb") as infile:
                        data = infile.read()
                    saver.add_attachment("host_logo", data, mimetype)
                except OSError:
                    pass

    # Add a meta document for user account configurations.
    if "user_configuration" not in db:
        with MetaSaver(id="user_configuration", db=db) as saver:
            saver["orcid"] = to_bool(app.config.get("USER_ORCID", True))
            saver["genders"] = app.config.get("USER_GENDERS") or [
                "Male",
                "Female",
                "Other",
            ]
            saver["birthdate"] = to_bool(app.config.get("USER_BIRTHDATE", True))
            saver["degrees"] = app.config.get("USER_DEGREES") or [
                "Mr/Ms",
                "MSc",
                "MD",
                "PhD",
                "Assoc Prof",
                "Prof",
                "Other",
            ]
            saver["affiliation"] = to_bool(app.config.get("USER_AFFILIATION", True))
            saver["universities"] = app.config.get("UNIVERSITIES") or []
            # Badly chosen key, but have to keep it...
            saver["postaladdress"] = to_bool(
                app.config.get("USER_POSTALADDRESS", False)
            )
            saver["phone"] = to_bool(app.config.get("USER_PHONE", True))
            saver["enable_email_whitelist"] = (
                app.config.get("USER_ENABLE_EMAIL_WHITELIST") or []
            )

    # Add a meta document for call configurations.
    if "call_configuration" not in db:
        with MetaSaver(id="call_configuration", db=db) as saver:
            saver["remaining_danger"] = app.config.get("CALL_REMAINING_DANGER") or 1.0
            saver["remaining_warning"] = app.config.get("CALL_REMAINING_WARNING") or 7.0
            saver["open_order_key"] = app.config.get("CALLS_OPEN_ORDER_KEY") or "closes"


CALLS_DESIGN_DOC = {
    "views": {
        "identifier": {
            "map": "function (doc) {if (doc.doctype !== 'call') return; emit(doc.identifier, doc.title);}"
        },
        "closes": {
            "map": "function (doc) {if (doc.doctype !== 'call' || !doc.closes || !doc.opens) return; emit(doc.closes, doc.identifier);}"
        },
        "opens": {
            "map": "function (doc) {if (doc.doctype !== 'call' || !doc.closes || !doc.opens) return; emit(doc.opens, doc.identifier);}"
        },
        "undefined": {
            "map": "function (doc) {if (doc.doctype !== 'call' || (doc.closes && doc.opens)) return; emit(doc.identifier, null);}"
        },
        "owner": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'call') return; emit(doc.owner, doc.identifier);}",
        },
        "reviewer": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'call') return; for (var i=0; i < doc.reviewers.length; i++) {emit(doc.reviewers[i], doc.identifier); }}",
        },
        "access": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'call') return; for (var i=0; i < doc.access_view.length; i++) {emit(doc.access_view[i], doc.identifier); }}",
        },
    }
}

PROPOSALS_DESIGN_DOC = {
    "views": {
        "identifier": {
            "map": "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.identifier, doc.title);}"
        },
        "call": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.call, doc.user);}",
        },
        "user": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'proposal') return; emit(doc.user, doc.identifier);}",
        },
        "call_user": {
            "map": "function (doc) {if (doc.doctype !== 'proposal') return; emit([doc.call, doc.user], doc.identifier);}"
        },
        "unsubmitted": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'proposal' || doc.submitted) return; emit(doc.user, doc.identifier);}",
        },
        "access": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'proposal') return; for (var i=0; i < doc.access_view.length; i++) {emit(doc.access_view[i], doc.identifier); }}",
        },
    }
}

REVIEWS_DESIGN_DOC = {
    "views": {
        "call": {  # Reviews for all proposals in call.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.call, null);}",
        },
        "proposal": {  # Reviews for a proposal.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.proposal, null);}",
        },
        "reviewer": {  # Reviews per reviewer, in any call
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit(doc.reviewer, null);}",
        },
        "call_reviewer": {  # Reviews per call and reviewer.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit([doc.call, doc.reviewer], null);}",
        },
        "proposal_reviewer": {
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.archived) return; emit([doc.proposal, doc.reviewer], null);}"
        },
        "unfinalized": {  # Unfinalized reviews by reviewer, in any call.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || doc.finalized || doc.archived) return; emit(doc.reviewer, null);}",
        },
        "proposal_archived": {  # Archived reviews for a proposal.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || !doc.archived) return; emit(doc.proposal, null);}",
        },
        "call_reviewer_archived": {  # Archived reviews for a call and reviewer.
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'review' || !doc.archived) return; emit([doc.call, doc.reviewer], doc.proposal);}",
        },
    }
}

DECISIONS_DESIGN_DOC = {
    "views": {
        # Decisions for all proposals in call.
        "call": {
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.call, doc.proposal);}",
        },
        # Decision for a proposal.
        "proposal": {
            "map": "function(doc) {if (doc.doctype !== 'decision') return; emit(doc.proposal, null);}"
        },
    }
}

GRANTS_DESIGN_DOC = {
    "views": {
        "identifier": {
            "map": "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.identifier, doc.proposal);}"
        },
        "call": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.call, doc.identifier);}",
        },
        "proposal": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.proposal, doc.identifier);}",
        },
        "user": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'grant') return; emit(doc.user, doc.identifier);}",
        },
        "incomplete": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'grant') return; if (Object.keys(doc.errors).length === 0) return; emit(doc.user, doc.identifier); for (var i=0; i < doc.access_edit.length; i++) {emit(doc.access_edit[i], doc.identifier); }}",
        },
        "access": {
            "reduce": "_count",
            "map": "function (doc) {if (doc.doctype !== 'grant') return; for (var i=0; i < doc.access_view.length; i++) {emit(doc.access_view[i], doc.identifier); }}",
        },
    }
}

USERS_DESIGN_DOC = {
    "views": {
        "username": {
            "reduce": "_count",
            "map": "function(doc) {if (doc.doctype !== 'user') return; emit(doc.username, null);}",
        },
        "email": {
            "map": "function(doc) {if (doc.doctype !== 'user' || !doc.email) return; emit(doc.email, null);}"
        },
        "orcid": {
            "map": "function(doc) {if (doc.doctype !== 'user' || !doc.orcid) return; emit(doc.orcid, doc.username);}"
        },
        "role": {
            "map": "function(doc) {if (doc.doctype !== 'user') return; emit(doc.role, doc.username);}"
        },
        "status": {
            "map": "function(doc) {if (doc.doctype !== 'user') return; emit(doc.status, doc.username);}"
        },
        "last_login": {
            "map": "function(doc) {if (doc.doctype !== 'user') return; if (!doc.last_login) return; emit(doc.last_login, doc.username);}"
        },
    }
}

LOGS_DESIGN_DOC = {
    "views": {
        "doc": {
            "map": "function (doc) {if (doc.doctype !== 'log') return; emit([doc.docid, doc.timestamp], null);}"
        }
    }
}

META_DESIGN_DOC = {
    "views": {
        "doc": {
            "map": "function (doc) {if (doc.doctype !== 'meta') return; emit(doc.docid, null);}"
        }
    }
}
