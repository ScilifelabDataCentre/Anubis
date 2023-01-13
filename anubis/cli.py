"Command-line interface for admin operations."

import json
import os.path
import time

import click
import couchdb2
import flask

import anubis.main
import anubis.database
import anubis.call
import anubis.proposal
import anubis.grant
import anubis.user

from anubis import constants
from anubis import utils


def set_db():
    "Must be called from within a Flask app context."
    try:
        flask.g.db = anubis.database.get_db()
    except couchdb2.NotFoundError as error:
        raise click.ClickException(error)


def to_json(data):
    "Convert data structure to indented JSON."
    return json.dumps(data, ensure_ascii=False, indent=2)


@click.group
def cli():
    "Command line interface for operations on the Anubis database."
    pass


@cli.command
def destroy_database():
    "Irrevocable delete of the entire database, including the instance within CouchDB."
    with anubis.main.app.app_context():
        server = anubis.database.get_server()
        try:
            db = server[anubis.main.app.config["COUCHDB_DBNAME"]]
        except couchdb2.NotFoundError as error:
            raise click.ClickException(error)
        db.destroy()
        click.echo(
            f"""Destroyed database '{anubis.main.app.config["COUCHDB_DBNAME"]}'."""
        )


@cli.command
def create_database():
    "Create the database within CouchDB and load the design documents."
    with anubis.main.app.app_context():
        server = anubis.database.get_server()
        if anubis.main.app.config["COUCHDB_DBNAME"] in server:
            raise click.ClickException(
                f"""Database '{anubis.main.app.config["COUCHDB_DBNAME"]}' already exists."""
            )
        server.create(anubis.main.app.config["COUCHDB_DBNAME"])
        anubis.database.update_design_documents()
        click.echo(
            f"""Created database '{anubis.main.app.config["COUCHDB_DBNAME"]}'."""
        )


@cli.command
def update_database():
    "Update the contents of the database for changes in new version(s)."
    with anubis.main.app.app_context():
        server = anubis.database.get_server()
        if not anubis.main.app.config["COUCHDB_DBNAME"] in server:
            raise click.ClickException(
                f"""Database '{anubis.main.app.config["COUCHDB_DBNAME"]}' does not exist."""
            )
        anubis.database.update_design_documents()
        anubis.database.update()
        click.echo(
            f"""Updated database '{anubis.main.app.config["COUCHDB_DBNAME"]}'."""
        )


@cli.command
def counts():
    "Output counts of entities in the system."
    with anubis.main.app.app_context():
        set_db()
        click.echo(f"{anubis.database.get_count('calls', 'owner'):>5} calls")
        click.echo(f"{anubis.database.get_count('proposals', 'user'):>5} proposals")
        click.echo(f"{anubis.database.get_count('reviews', 'call'):>5} reviews")
        click.echo(
            f"{anubis.database.get_count('reviews', 'proposal_archived'):>5} archived reviews"
        )
        click.echo(f"{anubis.database.get_count('grants', 'call'):>5} grants")
        click.echo(f"{anubis.database.get_count('users', 'username'):>5} users")


@cli.command
@click.option("--username", help="Username for the new admin account.", prompt=True)
@click.option("--email", help="Email address for the new admin account.", prompt=True)
@click.option(
    "--password",
    help="Password for the new admin account.",
    prompt=True,
    hide_input=True,
)
def create_admin(username, email, password):
    "Create a new admin account."
    with anubis.main.app.app_context():
        set_db()
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
def create_user(username, email, password):
    "Create a new user account."
    with anubis.main.app.app_context():
        set_db()
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
@click.option("--username", help="Username for the user account.", prompt=True)
@click.option(
    "--password",
    help="New password for the user account.",
    prompt=True,
    hide_input=True,
)
def set_password(username, password):
    "Set the password for a user account."
    with anubis.main.app.app_context():
        set_db()
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")
        click.echo(f"Set password for user account '{username}'.")


@cli.command
@click.option("--username", help="Username for the user account.", prompt=True)
def reset_password(username):
    "Reset the password for a user account."
    with anubis.main.app.app_context():
        set_db()
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password()
            code = saver["password"][5:]
            click.echo(f"One-time password setting code: {code}")
        else:
            raise click.ClickException("No such user.")


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
    with anubis.main.app.app_context():
        set_db()
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            if dumpdir:
                dumpfile = os.path.join(dumpdir, dumpfile)
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
    with anubis.main.app.app_context():
        set_db()
        if anubis.database.get_count("users", "username") != 0:
            raise click.ClickException(
                f"The database '{anubis.main.app.config['COUCHDB_DBNAME']}'"
                " is not empty."
            )

        ndocs, nfiles = flask.g.db.undump(dumpfile, progressbar=progressbar)
        click.echo(f"Loaded {ndocs} documents and {nfiles} files.")


@cli.command
@click.option("-f", "--filepath", type=str, help="The path of the downloaded file.")
@click.argument("identifier")
def download_document(filepath, identifier):
    """Download the JSON for the single document in the database.

    Write to the filepath if given, else to stdout.

    The identifier may be a user account name, email or ORCID, or a call identifier,
    proposal identifier, grant identifier, or '_id' if the CouchDB document.
    """
    with anubis.main.app.app_context():
        set_db()
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
def upload_document(filepath):
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
    with anubis.main.app.app_context():
        set_db()
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
@click.argument("identifier")
def delete_document(identifier):
    "Delete the JSON document with the given identifier from the database."
    with anubis.main.app.app_context():
        set_db()
        try:
            doc = flask.g.db[identifier]
            click.confirm("Really delete the document?", abort=True)
            flask.g.db.delete(doc)
        except couchdb2.CouchDB2Exception as error:
            raise click.ClickException(error)
    click.echo(f"Deleted JSON document '{identifier}'.")


@cli.command
def config():
    "Output the current config as a JSON document."
    with anubis.main.app.app_context():
        config = anubis.config.get_config(hidden=False)
    # Remove entries that are not relevant for a config file.
    for name in ["ROOT", "SETTINGS_DOTENV", "SETTINGS_ENVVAR", "SETTINGS_FILE"]:
        config.pop(name, None)
    click.echo(to_json(config))


@cli.command
def versions():
    "Versions of various software in the Anubis system."
    with anubis.main.app.app_context():
        for name, version, url in anubis.utils.get_software():
            click.echo(f"{name:>20} {version:>10}   {url}")


if __name__ == "__main__":
    cli()
