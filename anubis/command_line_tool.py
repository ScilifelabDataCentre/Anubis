"Command-line tool."

import argparse
import getpass
import sys

import flask

import anubis.app
import anubis.call
import anubis.proposal
import anubis.review
import anubis.user

from anubis import constants
from anubis import utils


def get_parser():
    "Get the parser for the command line tool."
    p = argparse.ArgumentParser(prog='command_line_tool.py',
                                usage='python %(prog)s [options]',
                                description='anubis command line tool')
    p.add_argument('-d', '--debug', action='store_true',
                    help='Debug logging output.')
    x0 = p.add_mutually_exclusive_group()
    x0.add_argument('-u', '--update', action='store_true',
                    help='Update the design document in the CouchDB database.')
    x0.add_argument('-A', '--create_admin', action='store_true',
                    help='Create an admin user.')
    x0.add_argument('-U', '--create_user', action='store_true',
                    help='Create a user.')
    x0.add_argument('-P', '--password', action='store_true',
                    help='Set the password for a user.')
    return p

def execute(pargs):
    "Execute the command. Must be within a flask app context."
    if pargs.debug:
        flask.current_app.config['DEBUG'] = True
        flask.current_app.config['LOGFORMAT'] = '%(levelname)-10s %(message)s'
    if pargs.update:
        utils.init(flask.current_app)
        anubis.call.init(flask.current_app)
        anubis.proposal.init(flask.current_app)
        anubis.review.init(flask.current_app)
        anubis.user.init(flask.current_app)
    if pargs.create_admin:
        with anubis.user.UserSaver() as saver:
            saver.set_username(input('username > '))
            saver.set_email(input('email > '), require=True)
            saver.set_password(getpass.getpass('password > '))
            saver.set_role(constants.ADMIN)
            saver.set_status(constants.ENABLED)
    elif pargs.create_user:
        with anubis.user.UserSaver() as saver:
            saver.set_username(input('username > '))
            saver.set_email(input('email > '), require=False)
            saver.set_password(getpass.getpass('password > '))
            saver.set_role(constants.USER)
            saver.set_status(constants.ENABLED)
    elif pargs.password:
        user = anubis.user.get_user(input('username > '))
        if user:
            with anubis.user.UserSaver(user) as saver:
                saver.set_password(getpass.getpass('password > '))
        else:
            sys.exit("No such user.")

def main():
    "Entry point for command line tool."
    parser = get_parser()
    pargs = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_usage()
    with anubis.app.app.app_context():
        flask.g.db = utils.get_db()
        flask.g.cache = {}          # id or key -> document
        execute(pargs)

if __name__ == '__main__':
    main()
