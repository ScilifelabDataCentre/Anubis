"Command-line interface."

import io
import json
import os
import tarfile
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

@cli.command()
def counts():
    "Output counts of database entities."
    with anubis.app.app.app_context():
        utils.set_db()
        click.echo(f"{utils.get_count('calls', 'owner'):>5} calls")
        click.echo(f"{utils.get_count('proposals', 'user'):>5} proposals")
        click.echo(f"{utils.get_count('reviews', 'call'):>5} reviews")
        click.echo(f"{utils.get_count('reviews', 'proposal_archived'):>5} archived reviews")
        click.echo(f"{utils.get_count('grants', 'call'):>5} grants")
        click.echo(f"{utils.get_count('users', 'username'):>5} users")

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
@click.option("--username", help="Username for the new user account.",
              prompt=True)
@click.option("--email", help="Email address for the new user account.",
              prompt=True)
@click.option("--password", help="Password for the new user account.",
              prompt=True, hide_input=True)
def user(username, email, password):
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
@click.option("--username", help="Username for the user account.",
              prompt=True)
@click.option("--password", help="New password for the user account.",
              prompt=True, hide_input=True)
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

@cli.command()
@click.option("-d", "--dumpfile", type=str,
                help="The path of the Publications database dump file.")
@click.option("-D", "--dumpdir", type=str,
                help="The directory to write the dump file in, using the standard name.")
def dump(dumpfile, dumpdir):
    "Dump all data in the database to a .tar.gz dump file."
    with anubis.app.app.app_context():
        utils.set_db()
        if not dumpfile:
            dumpfile = "dump_{0}.tar.gz".format(time.strftime("%Y-%m-%d"))
            if dumpdir:
                filepath = os.path.join(dumpdir, dumpfile)
        count_items = 0
        count_files = 0
        if dumpfile.endswith(".gz"):
            mode = "w:gz"
        else:
            mode = "w"
        with tarfile.open(dumpfile, mode=mode) as outfile:
            with click.progressbar(flask.g.db, label="Dumping...") as bar:
                for doc in bar:
                    # Only documents that explicitly belong to the application.
                    if doc.get('doctype') is None: continue
                    rev = doc.pop("_rev")
                    info = tarfile.TarInfo(doc["_id"])
                    data = json.dumps(doc).encode("utf-8")
                    info.size = len(data)
                    outfile.addfile(info, io.BytesIO(data))
                    count_items += 1
                    doc["_rev"] = rev       # Revision required to get attachments.
                    for attname in doc.get("_attachments", dict()):
                        info = tarfile.TarInfo("{0}_att/{1}".format(doc["_id"], attname))
                        attfile = flask.g.db.get_attachment(doc, attname)
                        if attfile is None: continue
                        data = attfile.read()
                        attfile.close()
                        info.size = len(data)
                        outfile.addfile(info, io.BytesIO(data))
                        count_files += 1
        click.echo(f"Dumped {count_items} items and {count_files} files to {dumpfile}")

@cli.command()
@click.argument("dumpfile", type=click.Path(exists=True))
def undump(dumpfile):
    "Load an Anubis database .tar.gz dump file. The database must be empty."
    with anubis.app.app.app_context():
        utils.set_db()
        if utils.get_count( 'users', 'username') != 0:
            raise click.ClickException(
                f"The database '{anubis.app.app.config['COUCHDB_DBNAME']}'"
                " is not empty.")
        count_items = 0
        count_files = 0
        attachments = dict()
        with tarfile.open(dumpfile, mode="r") as infile:
            length = sum(1 for member in infile if member.isreg())
        with tarfile.open(dumpfile, mode="r") as infile:
            with click.progressbar(infile, label="Loading...", length=length) as bar:
                for item in bar:
                    itemfile = infile.extractfile(item)
                    itemdata = itemfile.read()
                    itemfile.close()
                    if item.name in attachments:
                        # This relies on an attachment being after its item in the tarfile.
                        flask.g.db.put_attachment(doc, itemdata,
                                                  **attachments.pop(item.name))
                        count_files += 1
                    else:
                        doc = json.loads(itemdata)
                        atts = doc.pop("_attachments", dict())
                        flask.g.db.put(doc)
                        count_items += 1
                        for attname, attinfo in list(atts.items()):
                            key = "{0}_att/{1}".format(doc["_id"], attname)
                            attachments[key] = dict(filename=attname,
                                                    content_type=attinfo["content_type"])
        click.echo(f"Loaded {count_items} items and {count_files} files.")
    

if __name__ == '__main__':
    cli()
