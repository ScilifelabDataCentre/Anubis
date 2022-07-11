"Command-line interface for admin operations."

import json
import os.path
import time

import click
import flask

import anubis.app
import anubis.call
import anubis.proposal
import anubis.grant
import anubis.user

from anubis import constants
from anubis import utils


@click.group()
def cli():
    "Command line interface for operations on the Anubis database."
    pass


@cli.command()
def counts():
    "Output counts of entities in the system."
    with anubis.app.app.app_context():
        utils.set_db()
        click.echo(f"{utils.get_count('calls', 'owner'):>5} calls")
        click.echo(f"{utils.get_count('proposals', 'user'):>5} proposals")
        click.echo(f"{utils.get_count('reviews', 'call'):>5} reviews")
        click.echo(
            f"{utils.get_count('reviews', 'proposal_archived'):>5} archived reviews"
        )
        click.echo(f"{utils.get_count('grants', 'call'):>5} grants")
        click.echo(f"{utils.get_count('users', 'username'):>5} users")


@cli.command()
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
        utils.set_db()
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.ADMIN)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
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
        utils.set_db()
        try:
            with anubis.user.UserSaver() as saver:
                saver.set_username(username)
                saver.set_email(email)
                saver.set_password(password)
                saver.set_role(constants.USER)
                saver.set_status(constants.ENABLED)
        except ValueError as error:
            raise click.ClickException(str(error))


@cli.command()
@click.option("--username", help="Username for the user account.", prompt=True)
@click.option(
    "--password",
    help="New password for the user account.",
    prompt=True,
    hide_input=True,
)
def password(username, password):
    "Set the password for a user account."
    with anubis.app.app.app_context():
        utils.set_db()
        user = anubis.user.get_user(username)
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password(password)
        else:
            raise click.ClickException("No such user.")


@cli.command()
@click.argument("identifier")
def show(identifier):
    "Show the JSON for the item given by the identifier."
    with anubis.app.app.app_context():
        utils.set_db()
        for item in [
            anubis.call.get_call(identifier),
            anubis.proposal.get_proposal(identifier),
            anubis.grant.get_grant(identifier),
            anubis.user.get_user(username=identifier),
            anubis.user.get_user(email=identifier),
            flask.g.db.get(identifier),
        ]:
            if item:
                click.echo(json.dumps(item, indent=2))
                break
        else:
            raise click.ClickException("No such item.")


@cli.command()
@click.argument("username")
def user(username):
    "Show the JSON for the user given by username or email."
    with anubis.app.app.app_context():
        utils.set_db()
        for item in [
            anubis.user.get_user(username=username),
            anubis.user.get_user(email=username),
        ]:
            if item:
                click.echo(json.dumps(item, indent=2))
                break
        else:
            raise click.ClickException("No such user.")


@cli.command()
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
        utils.set_db()
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            if dumpdir:
                filepath = os.path.join(dumpdir, dumpfile)
        ndocs, nfiles = flask.g.db.dump(
            dumpfile, exclude_designs=True, progressbar=progressbar
        )
        click.echo(f"Dumped {ndocs} documents and {nfiles} files to {dumpfile}")


@cli.command()
@click.argument("dumpfile", type=click.Path(exists=True))
@click.option(
    "--progressbar/--no-progressbar", default=True, help="Display a progressbar."
)
def undump(dumpfile, progressbar):
    "Load an Anubis database dump file. The database must be empty."
    with anubis.app.app.app_context():
        utils.set_db()
        if utils.get_count("users", "username") != 0:
            raise click.ClickException(
                f"The database '{anubis.app.app.config['COUCHDB_DBNAME']}'"
                " is not empty."
            )
        ndocs, nfiles = flask.g.db.undump(dumpfile, progressbar=progressbar)
        click.echo(f"Loaded {ndocs} documents and {nfiles} files.")


if __name__ == "__main__":
    cli()
