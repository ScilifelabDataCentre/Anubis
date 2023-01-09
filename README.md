# Anubis

Anubis is a web-based system to handle calls for proposals, proposal submission,
reviews, decisions and grant dossiers. It allows:

- The publication of calls, with handling of open/close dates.
- Proposals can be created, edited and submitted based on open calls.
- A person who wants to prepare and submit a proposal must create an
  account in the system.
- The administrator configures which accounts should be reviewers of
  the proposals in a call.
- The administrator records the decisions that the reviewers (or other group) have made.
- Grants can have information and documents related to them added by both grantees
  and the Anubis site staff.

# Installation

## Software

The source code is available the
[Anubis GitHub repo](https://github.com/pekrau/Anubis).

Anubis requires Python >= 3.9 and [CouchDB >= 2.3.1](https://couchdb.apache.org/);
installation of those systems is not documented here.

### Source code

Get the source code by downloading the
[latest release from GitHub](https://github.com/pekrau/Anubis/releases)
and unpacking it. For simplicity, rename the top directory to `Anubis`.

It is recommended to set up a virtual environment for Anubis. On my
development machine, I am using the `virtualenv` system:

```bash
$ mkvirtualenv Anubis
$ cd Anubis
$ add2virtualenv        # To add the top Anubis dir to Python path.
$ setvirtualenvproject  # To make this dir the default when doing 'workon'.
```

The installation of a virtual environment system is not documented here.

Within the virtual environment, download and install the required
Python packages from PyPi:

```bash
$ workon Anubis  # Activate the virtual environment
$ pip install -r requirements.txt
```

### Docker container

A Docker container of the
[latest release is available at GitHub](https://github.com/pekrau/Anubis/pkgs/container/anubis).

## CouchDB database

The Anubis system relies on the [CouchDB database system](https://couchdb.apache.org/).
This has to be installed and running. Refer to the CouchDB documentation.

A user account has to be created in the CouchDB system with sufficient privileges
to create a database within it. This is the account used by Anubis to create,
access and modify its data. Refer to the CouchDB documentation.

### Configuration

In production mode, the Anubis `flask` uwsgi-compliant app should be
run by another web server, such as Apache, NGINX, Gunicorn or
similar. The app to be executed is
`anubis.app.app`. This setup not documented here.

Some configuration needs to be done before the app can be executed.
The configuration values can be set in one of two ways:

1. Setting environment variables that specify the configuration values.
2. Using a file `settings.json` containing the configuration values. This file
   can be located in the source directory `Anubis/anubis` or in a directory
   `Anubis/site`, which you may create.

The following configuration settings need to be set:

- `COUCHDB_URL`: The URL to the CouchDB instance.
- `COUCHDB_DBNAME`: The name of the CouchDB database for Anubis.
- `COUCHDB_USERNAME`: The name of the CouchDB user account with privileges to
  create, read and write the Anubis database within CouchDB.
- `COUCHDB_PASSWORD`: The password for the CouchDB account.
- `SECRET_KEY`: A longish string of random characters required for proper
  session handling.
- `TIMEZONE`: The software attempts to fetch this value from the environment,
  but it may have to be set explicitly.
- `MAIL_SERVER`: The name of the mail server for outgoing email. Anubis
  can execute without mail, but several account handling features will be restricted
  or missing, such as set and reset of passwords.
- `MAIL_PORT`: Default 25; may need to be changed depending on the variables below.
- `MAIL_USE_TLS`: Default False; set to True (or 1) to enable TLS for email.
- `MAIL_USE_SSL`: Default False; set to True (or 1) to enable SSL for email.
- `MAIL_USERNAME`: The user name requried to login to the email server.
- `MAIL_PASSWORD`: The password required  to login to the email server.
- `MAIL_DEFAULT_SENDER`: The email address of the sender of emails from Anubis.
- `MAIL_REPLY_TO`: The email address to use for replies, if different from the
  default sender.
