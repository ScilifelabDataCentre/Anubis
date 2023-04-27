# Anubis

Anubis is a web-based system to handle calls for proposals, proposal submission,
reviews, decisions and grant dossiers. It allows:

- The creation of calls, which includes defining what information a
  proposals should contain.
- The publication of calls, with handling of open/close dates.
- Proposals can be created, edited and submitted by users based on
  open calls.
- To prepare and submit a proposal, a person must must create an
  account in the Anubis system.
- Accounts with the role admin (or 'admin', for short) have the
  privileges to use all features in the system, including inspecting
  and handling calls, proposals, reviews, decisions and grants.
- Specific accounts can be given the privilege of creating calls by
  the admin.  They will be owners of the calls they create.
- A call owner designates which accounts should be reviewers of the
  proposals in a call.
- The call owner or admin records the decisions that the reviewers have made.
- Grants can have information and documents added by grant receivers and/or
  the Anubis site staff.

# Installation

## Software

The source code is available the [Anubis GitHub repo](https://github.com/pekrau/Anubis).

Anubis requires Python >= 3.10.

### Source code

Get the source code by downloading the
[latest release from GitHub](https://github.com/pekrau/Anubis/releases)
and unpacking it. For simplicity, rename the top directory to `Anubis`.

It is recommended to set up a virtual environment for Anubis. On my
development machine, I am using the `virtualenv` system. Refer to its
documentation.

```bash
$ mkvirtualenv Anubis
$ cd Anubis

$ add2virtualenv $PWD    # To add the root Anubis dir to Python path.
$ setvirtualenvproject   # To make this dir the default when doing 'workon'.
```

Within the virtual environment, download and install the required
Python packages from PyPi:

```bash
$ workon Anubis   # Activate the virtual environment and move into root dir.
$ pip install -r requirements.txt
```

### Docker container

A Docker container of the
[latest release is available at GitHub](https://github.com/pekrau/Anubis/pkgs/container/anubis).

## CouchDB database

The Anubis system relies on the [CouchDB database system](https://couchdb.apache.org/),
version >= 2.3.1.
This has to be installed and running. Refer to the CouchDB documentation.

A user account has to be created in the CouchDB system with sufficient privileges
to create a database within it. This is the account used by Anubis to create,
access and modify its data. Refer to the CouchDB documentation.

## Configuration

There are two phases of configuration:

1. Server configuration. This should be done once when installing the
   system. This requires access to the server machine.

   Server configuration takes effect when the web server process is
   started.  This means that if it is changed, the web server process
   will have to be restarted.

2. Web interface configuration. This is done when the web server is up
   and running, and requires an administrator account (role 'admin')
   in the Anubis site. This should usually be done before launching
   the site for general use. The various configuration pages can be
   reached from the top menu item 'Admin', which is visible only to
   admins.

   These changes take effect immediately. The values are stored in the
   database, and are read from it when the server process is
   restarted.

### Server configuration

In production mode, the Anubis `flask` uwsgi-compliant app should be
run by another web server, such as Apache, NGINX, Gunicorn or
similar. The app to be executed is `anubis.main.app`.
This setup not documented here.

Some server configuration needs to be done before the app can be executed.
The configuration values can be set in one of two ways:

1. Environment variables that specify the configuration values.
2. Using a file `settings.json` containing the configuration values. The path
   of this file can be specified by the environment variable ANUBIS_SETTINGS_FILEPATH
   or it can be located in a directory `Anubis/site`, which you must create.

The following configuration settings need to be reviewed and set:

- `COUCHDB_URL`: The absolute URL for the CouchDB instance interface.
- `COUCHDB_DBNAME`: The name of the CouchDB database used for Anubis.
- `COUCHDB_USERNAME`: The name of the CouchDB user account with privileges to
  create, read and write the Anubis database within CouchDB.
- `COUCHDB_PASSWORD`: The password for the CouchDB account.
- `SECRET_KEY`: A longish string of random characters required for proper
  session handling.
- `REVERSE_PROXY`: Set to the string 'true' if the
  'werkzeug.middleware.proxy_fix.ProxyFix' is to be used.
- `TIMEZONE`: By default "Europe/Stockholm", so needs to be set explicitly.
- `MIN_PASSWORD_LENGTH`: The minimum length of a user account password.
- `MAIL_SERVER`: The name of the mail server for outgoing email. Anubis
  can execute without mail, but several account handling features will be restricted
  or missing, such as setting and resetting of passwords.
- `MAIL_PORT`: Default 25; may need to be changed depending on the variables below.
- `MAIL_USE_TLS`: Default False; set to True (or 1) to enable TLS for email.
- `MAIL_USE_SSL`: Default False; set to True (or 1) to enable SSL for email.
- `MAIL_USERNAME`: The user name requried to login to the email server.
- `MAIL_PASSWORD`: The password required  to login to the email server.
- `MAIL_DEFAULT_SENDER`: The email address of the sender of emails from Anubis.
- `MAIL_REPLY_TO`: The email address to use for replies, if different from the
  default sender.

Once the Anubis system has been properly installed and configured,
it will be possible to execute the command-line interface (CLI) script
in the same environment as the web server is executing.

```bash
$ workon Anubis   # Activate the virtual environment and move into root dir.
$ cd anubis
$ python cli.py --help
```

At least one administrator account ('admin') must be created using the CLI:

```bash
$ workon Anubis   # Activate the virtual environment and move into root dir.
$ cd anubis
$ python cli.py admin   # And provide input to the questions asked...
```

Once that administrator account exists, it can be used to create other accounts
via the web interface, including other administrator accounts.

### Web interface configuration

The pages reachable from the top menu item 'Admin' contain all settings that
can be configured from the web interface by an admin.

The settings fields in these pages are (supposed to be) self-explanatory.
Before launching the site for general use, the admin should go through
these pages and consider the appropriate settings.


# Software design

The implementation of Anubis is based on the following design decisions:

- The back-end is written in Python using [Flask](https://pypi.org/project/Flask/ "!").
  - The back-end generates HTML for display using [Jinja2](https://pypi.org/project/Jinja2/ "!").
  - The front-end uses [Bootstrap](https://getbootstrap.com/docs/4.6/getting-started/introduction/ "!").
- The back-end uses the No-SQL database  [CouchDB](https://couchdb.apache.org/ "!").
  - Each entity instance is stored in one document in the CouchDB database.
  - The entities are in most cases identified internally by a IUID
    (Instance-unique identifier) which is a UUID4 value.
  - The entities contain pointers to each other using the IUIDs.
  - The CouchDB indexes ("designs") are vital for the computational efficiency
    of the system.
- There is a command-line interface (CLI) tool for certain operations,
  such as creating and loading backup dumps.
