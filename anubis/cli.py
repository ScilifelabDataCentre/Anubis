"Command-line interface for admin operations."

import json
import os.path
import time

import click
import couchdb2
import flask

import anubis.app
import anubis.database
import anubis.call
import anubis.proposal
import anubis.grant
import anubis.user

from anubis import constants
from anubis import utils


@click.group
def cli():
    "Command line interface for operations on the Anubis database."
    pass


@cli.command
def destroy_database():
    "Hard delete of the entire database, including the instance within CouchDB."
    with anubis.app.app.app_context():
        server = anubis.database.get_server()
        try:
            db = server[anubis.app.app.config["COUCHDB_DBNAME"]]
        except couchdb2.NotFoundError as error:
            raise click.ClickException(str(error))
        db.destroy()
        click.echo(f"""Destroyed database '{anubis.app.app.config["COUCHDB_DBNAME"]}'.""")


@cli.command
def create_database():
    "Create the database within CouchDB and load the design documents."
    with anubis.app.app.app_context():
        server = anubis.database.get_server()
        if anubis.app.app.config["COUCHDB_DBNAME"] in server:
            raise click.ClickException(
                f"""Database '{anubis.app.app.config["COUCHDB_DBNAME"]}' already exists."""
            )
        server.create(anubis.app.app.config["COUCHDB_DBNAME"])
        anubis.database.update_design_documents()
        click.echo(f"""Created database '{anubis.app.app.config["COUCHDB_DBNAME"]}'.""")


@cli.command
def counts():
    "Output counts of entities in the system."
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
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
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.ADMIN)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


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
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.USER)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


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
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")


@cli.command
@click.option("--username", help="Username for the user account.", prompt=True)
def reset_password(username):
    "Reset the password for a user account."
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
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
    "Dump all data in the database to a .tar.gz dump file."
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            if dumpdir:
                dumpfile = os.path.join(dumpdir, dumpfile)
        ndocs, nfiles = flask.g.db.dump(
            dumpfile, exclude_designs=True, progressbar=progressbar
        )
        click.echo(f"Dumped {ndocs} documents and {nfiles} files to {dumpfile}")


@cli.command
@click.argument("dumpfile", type=click.Path(exists=True))
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def undump(dumpfile, progressbar):
    "Load an Anubis database dump file. The database must be empty."
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        if anubis.database.get_count("users", "username") != 0:
            raise click.ClickException(
                f"The database '{anubis.app.app.config['COUCHDB_DBNAME']}'"
                " is not empty."
            )
        
        ndocs, nfiles = flask.g.db.undump(dumpfile, progressbar=progressbar)
        click.echo(f"Loaded {ndocs} documents and {nfiles} files.")


@cli.command
@click.argument("identifier")
def output(identifier):
    """Output the JSON for the single document in the database.
    The identifier may be a user account name, email or ORCID, or a call identifier,
    proposal identifier, grant identifier, or '_id' if the CouchDB document.
    """
    with anubis.app.app.app_context():
        flask.g.db = anubis.database.get_db()
        doc = anubis.database.get_doc(identifier)
        if doc is None:
            raise click.ClickException("No such item in the database.")
        click.echo(to_json(doc))


@cli.command
def config():
    "Output the current config."
    with anubis.app.app.app_context():
        config = anubis.config.get_config(hidden=False)
    click.echo(to_json(config))


@cli.command
def versions():
    "Version of various software in the Anubis system."
    with anubis.app.app.app_context():
        click.echo(to_json(anubis.utils.get_software()))


def to_json(data):
    "Convert data structure to indented JSON."
    return json.dumps(data, ensure_ascii=False, indent=2)    


if __name__ == "__main__":
    cli()
