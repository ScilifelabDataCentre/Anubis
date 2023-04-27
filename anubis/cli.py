"Command-line interface for administrator operations."

import json
import os.path
import time

import click
import couchdb2
import flask

import anubis.config
import anubis.database
import anubis.call
import anubis.proposal
import anubis.grant
import anubis.user

from anubis import constants
from anubis import utils


def set_db(app):
    "Set the database object in the current context."
    try:
        flask.g.db = anubis.database.get_db(app=app)
    except couchdb2.NotFoundError as error:
        raise click.ClickException(error)


def to_json(data):
    "Convert data structure to indented JSON."
    return json.dumps(data, ensure_ascii=False, indent=2)


def join_dirpath(dirpath, filename):
    if dirpath:
        return os.path.normpath(
            os.path.join(os.path.expandvars(os.path.expanduser(dirpath)), filename)
        )
    else:
        return filename


@click.group
def cli():
    "Command line interface for operations on the Anubis database."
    pass


@cli.command
def config():
    "Output the current config as a JSON document."
    app = anubis.config.create_app()
    with app.app_context():
        config = anubis.config.get_config(hidden=False)
    # Remove entries that are not relevant for a config file.
    for name in ["ROOT", "SETTINGS_DOTENV", "SETTINGS_ENVVAR", "SETTINGS_FILEPATH"]:
        config.pop(name, None)
    click.echo(to_json(config))


@cli.command
def versions():
    "Versions of various software in the Anubis system."
    app = anubis.config.create_app()
    with app.app_context():
        for name, version, url in anubis.utils.get_software():
            click.echo(f"{name:>20} {version:>10}   {url}")


@cli.command
def counts():
    "Output counts of entities in the system."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        click.echo(f"{anubis.database.get_count('calls', 'owner'):>5} calls")
        click.echo(f"{anubis.database.get_count('proposals', 'user'):>5} proposals")
        click.echo(f"{anubis.database.get_count('reviews', 'call'):>5} reviews")
        click.echo(
            f"{anubis.database.get_count('reviews', 'proposal_archived'):>5} archived reviews"
        )
        click.echo(f"{anubis.database.get_count('grants', 'call'):>5} grants")
        click.echo(f"{anubis.database.get_count('users', 'username'):>5} users")


@cli.command
@click.option("--force", is_flag=True, help="Do not ask for confirmation.")
def database_destroy(force):
    "Irrevocable delete of the entire database, including the instance within CouchDB."
    app = anubis.config.create_app()
    with app.app_context():
        server = anubis.database.get_server(app)
        try:
            db = server[app.config["COUCHDB_DBNAME"]]
        except couchdb2.NotFoundError as error:
            raise click.ClickException(error)
        if not force:
            click.confirm(
                "The entire database will be irrevocably deleted: Continue?", abort=True
            )
        db.destroy()
        click.echo(f"""Destroyed database '{app.config["COUCHDB_DBNAME"]}'.""")


@cli.command
def database_create():
    "Create the database within CouchDB and load the design documents."
    app = anubis.config.create_app(config_with_db=False)
    with app.app_context():
        server = anubis.database.get_server(app)
        if app.config["COUCHDB_DBNAME"] in server:
            raise click.ClickException(
                f"""Database '{app.config["COUCHDB_DBNAME"]}' already exists."""
            )
        server.create(app.config["COUCHDB_DBNAME"])
        # Do not update the database more than this!
        # A dump file may contain configuration documents to be loaded.
        anubis.database.update_design_documents(app)
        click.echo(f"""Created database '{app.config["COUCHDB_DBNAME"]}'.""")


@cli.command
@click.option("--username", help="Username for the new admin account.", prompt=True)
@click.option("--email", help="Email address for the new admin account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new admin account.",
    prompt=True,
    hide_input=True,
)
def admin(username, email, password):
    "Create a new admin account."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.ADMIN)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(error)
        click.echo(f"Created admin user account '{username}'.")


@cli.command
@click.option("--username", help="Username for the new user account.", prompt=True)
@click.option("--email", help="Email address for the new user account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new user account.",
    prompt=True,
    hide_input=True,
)
def user(username, email, password):
    "Create a new user account."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.USER)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(error)
        click.echo(f"Created user account '{username}'.")


@cli.command
@click.option(
    "-d", "--dumpfile", type=str, help="The path of the Anubis database dump file."
)
@click.option(
    "-D",
    "--dumpdir",
    type=str,
    help="The directory to write the dump file in, using the default name.",
)
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def dump(dumpfile, dumpdir, progressbar):
    "Dump all data in the database to a '.tar.gz' dump file."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            dumpfile = join_dirpath(dumpdir, dumpfile)
        ndocs, nfiles = flask.g.db.dump(
            dumpfile, exclude_designs=True, progressbar=progressbar
        )
        click.echo(f"Dumped {ndocs} documents and {nfiles} files to '{dumpfile}'.")


@cli.command
@click.argument("dumpfile", type=click.Path(exists=True))
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def undump(dumpfile, progressbar):
    "Load an Anubis database dump file. The database must be empty."
    # Do not update the database before loading the data!
    # The dump file may contain configuration documents to be loaded.
    app = anubis.config.create_app(update_db=False)
    with app.app_context():
        set_db(app)
        if anubis.database.get_count("users", "username") != 0:
            raise click.ClickException(
                f"The database '{app.config['COUCHDB_DBNAME']}' is not empty."
            )

        ndocs, nfiles = flask.g.db.undump(dumpfile, progressbar=progressbar)
        click.echo(f"Loaded {ndocs} documents and {nfiles} files.")


@cli.command
@click.option("--username", help="Username for the user account.", prompt=True)
@click.option(
    "--password",
    help="New password for the user account.",
    prompt=True,
    hide_input=True,
)
def password_set(username, password):
    "Set the password for a user account."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")
        click.echo(f"Set password for user account '{username}'.")


@cli.command
@click.option("--username", help="Username for the user account.", prompt=True)
def password_reset(username):
    "Reset the password for a user account."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password()
            code = saver["password"][5:]
            click.echo(f"One-time password setting code: {code}")
        else:
            raise click.ClickException("No such user.")


@cli.command
@click.option("-f", "--filepath", type=str, help="The path of the downloaded file.")
@click.argument("identifier")
def document_download(filepath, identifier):
    """Download the JSON for the single document in the database.

    Write to the filepath if given, else to stdout.

    The identifier may be a user account name, email or ORCID, or a call identifier,
    proposal identifier, grant identifier, or '_id' if the CouchDB document.
    """
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        doc = anubis.database.get_doc(identifier)
        if doc is None:
            raise click.ClickException("No such document in the database.")
        if filepath:
            with open(filepath, "w") as outfile:
                outfile.write(to_json(doc))
            click.echo(f"Wrote JSON document to '{filepath}'.")
        else:
            click.echo(to_json(doc))


@cli.command
@click.argument("filepath", type=click.Path(exists=True))
def document_upload(filepath):
    """Upload a JSON document from a file into the database.

    If the document does not contain an '_id' entry, it will be set.

    If the document with the given '_id' entry exists in the database,
    the '_rev' entry must be present and correct.
    """
    try:
        with open(filepath) as infile:
            doc = json.load(infile)
    except json.JSONDecodeError as error:
        raise click.ClickException(error)
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        if "_id" in doc and doc["_id"] in flask.g.db:
            click.confirm(
                "A document with the '_id' already exists. Overwrite it?", abort=True
            )
        try:
            flask.g.db.put(doc)
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
    click.echo(f"""Uploaded JSON document '{doc["_id"]}' from '{filepath}'.""")


@cli.command
@click.option("--force", is_flag=True, help="Do not ask for confirmation.")
@click.argument("identifier")
def document_delete(force, identifier):
    "Delete the JSON document with the given identifier from the database."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            doc = flask.g.db[identifier]
            if not force:
                click.confirm("Really delete the document?", abort=True)
            flask.g.db.delete(doc)
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
    click.echo(f"Deleted JSON document '{identifier}'.")


@cli.command
@click.argument("identifier")
def attachments(identifier):
    "List the attachments for the document with the given identifier.."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            doc = flask.g.db[identifier]
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
        for filename, info in sorted(doc.get("_attachments", {}).items()):
            click.echo(
                f"{filename}\n  {info['content_type']}\n  {info['length']} bytes\n  {info['digest']}"
            )


@cli.command
@click.argument("identifier")
@click.option(
    "-D",
    "--dumpdir",
    type=str,
    help="The directory to write the attachments files to.",
)
def attachments_download(identifier, dumpdir):
    "Download all attachments for the document with the given identifier."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            doc = flask.g.db[identifier]
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
        for filename in sorted(doc.get("_attachments", {})):
            filepath = join_dirpath(dumpdir, filename)
            with open(filepath, "wb") as outfile:
                outfile.write(flask.g.db.get_attachment(doc, filename).read())
            click.echo(f"Downloaded {filepath}")


@cli.command
@click.argument("identifier")
@click.argument("filename", type=click.Path(exists=True))
def attachment_upload(identifier, filename):
    "Upload the given file and attach to the document with the given identifier."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            doc = flask.g.db[identifier]
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
        with open(filename, "rb") as infile:
            flask.g.db.put_attachment(doc, infile.read(), filename=filename)
        click.echo(f"Uploaded {filename} from document {identifier}.")


@cli.command
@click.argument("identifier")
@click.argument("filename")
def attachment_delete(identifier, filename):
    "Upload the given file and attach to the document with the given identifier."
    app = anubis.config.create_app()
    with app.app_context():
        set_db(app)
        try:
            doc = flask.g.db[identifier]
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
            raise click.ClickException(error)
        if filename not in doc.get("_attachments", {}):
            raise click.ClickException(
                "No such file {filename} in document {identifier}."
            )
        flask.g.db.delete_attachment(doc, filename)
        click.echo(f"Deleted {filename} from document {identifier}.")


if __name__ == "__main__":
    cli()
