## Installation

These notes are for [the SciLifeLab instance](https://anubis.scilifelab.se/).
You will have to adapt the information according to your site.

Some example files are located in the `install` directory of the distro. These
need to be adapted to your site.

### Software

The source code is available the
[Anubis GitHub repo](https://github.com/pekrau/Anubis).

Anubis requires Python >= 3.6 and [CouchDB >= 2.3.1](https://couchdb.apache.org/);
installation of those systems is not documented here.

### Source code and packages

Get the source code:

```
$ cd
$ git clone https://github.com/pekrau/Anubis.git
```

It is recommended to set up a virtual environment for Anubis. On my
development machine, I am using the `virtualenv` system:

```bash
$ mkvirtualenv -p /usr/bin/python3 Anubis
$ cd Anubis
$ add2virtualenv        # To add the top Anubis dir to Python path
$ setvirtualenvproject  # To make this dir the default when doing 'workon'
```

The installation of a virtual environment system and creation of a virtenv
for Anubis is not documented here.

Download and install the required Python packages from PyPi:

```bash
$ workon Anubis  # Activate the virtual environment
$ pip install -r requirements.txt
```

### Configuration

The Anubis `flask` server runs as a `uwsgi` web server. It
needs to be configured. This is done in a JSON file called
`settings.json` located in the `site` directory. An example file can
be found in the `install` directory.

```bash
$ cd Anubis
$ mkdir site
$ cp install/settings.json site/settings.json
$ cd site
$ chmod go-rw settings.json  # Since it contains secrets
$ emacs settings.json  # Ok, ok, vim also works...
```

In particular, the following settings should be looked at:

- `"DEBUG": "true"` Web server debug mode: should be "false" in production.
- `"SECRET_KEY": "long-string-of-random-chars"` Needed for proper session handling.
- `"COUCHDB_URL"` The URL to the CouchDB instance.
- `"COUCHDB_DATABASE"` The name of the CouchDB database for Anubis.
- `"COUCHDB_USERNAME"` The name of the user account with read/write access to the CouchDB database.
- `"COUCHDB_PASSWORD"` The password for the user account.
- `"SITE_STATIC_DIRPATH"`: The full path to the directory containing site-specific files, such as logo image files.
- `"HOST_LOGO"`: The file name of the site-specific logo image file. It must be locaded in the `SITE_STATIC_DIRPATH`.
- `"HOST_NAME"`: The name of host of the site; e.g. the institution.
- `"HOST_URL"`: The URL to the home page of the host.
- `"MAIL_SERVER"`: The name of the mail server. There are more
  settings to define if the mail server cannot be set as
  `localhost`. See the `Anubis/anubis/config.py` file.

#### CouchDB

A database for Anubis needs to be created within the CouchDB
instance. See the CouchDB documentation on how to do this.

If a username and password is required for read/write access to the
CouchDB database for Anubis, then add those with the name of the database
to the `settings.json` file; see above.

#### Web server

The SciLifeLab instance uses `nginx` as a reverse proxy for the
`flask` web server that implements Anubis. The file
`Anubis/install/uwsgi.conf` contains the setup for `nginx`.
It should be located in the directory `/etc/nginx/conf.d`.

To run Anubis as a `systemd` service under Linux, the file
`Anubis/install/anubis.system` contains the setup. It should be
located in the directory `/etc/systemd/system`.

Useful `systemctl` commands are:

```bash
$ sudo systemctl status anubis
$ sudo systemctl start anubis
$ sudo systemctl restart anubis
$ sudo systemctl stop anubis
```

There is also a updating script `Anubis/install/deploy_anubis.bash` to
be located in a site-dependent directory and run like so:

```bash
$ sudo /etc/scripts/deploy_anubis.bash
```

This script contains the somewhat mysterious commands needed to make
things work under the restrictive security policies of SELinux.
