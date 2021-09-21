"Command-line interface."

import json

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
    "Command line interface for admin operations on the Anubis database."
    pass

@cli.command()
@click.option("--username", help="Username for the new admin account.",
              prompt=True)
@click.option("--email", help="Email address for the new admin account.",
              prompt=True)
@click.option("--password", help="Password for the new admin account.",
              prompt=True, hide_input=True)
def admin(username, email, password):
    "Create a new admin account."
    with anubis.app.app.app_context():
        flask.g.db = utils.get_db()
        flask.g.cache = {}          # id or key -> document
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
@click.option("--username", help="Username for the new user account.",
              prompt=True)
@click.option("--email", help="Email address for the new user account.",
              prompt=True)
@click.option("--password", help="Password for the new user account.",
              prompt=True, hide_input=True)
def user(username, email, password):
    "Create a new user account."
    with anubis.app.app.app_context():
        flask.g.db = utils.get_db()
        flask.g.cache = {}          # id or key -> document
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
@click.option("--username", help="Username for the user account.",
              prompt=True)
@click.option("--password", help="New password for the user account.",
              prompt=True, hide_input=True)
def password(username, password):
    "Set the password for a user account."
    with anubis.app.app.app_context():
        flask.g.db = utils.get_db()
        flask.g.cache = {}          # id or key -> document
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
        flask.g.db = utils.get_db()
        flask.g.cache = {}          # id or key -> document
        for item in [anubis.user.get_user(username=identifier),
                     anubis.user.get_user(email=identifier),
                     anubis.call.get_call(identifier),
                     anubis.proposal.get_proposal(identifier),
                     anubis.grant.get_grant(identifier),
                     flask.g.db.get(identifier)]:
            if item:
                click.echo(json.dumps(item, indent=2))
                break
        else:
            raise click.ClickException("No such item.")


if __name__ == '__main__':
    cli()
