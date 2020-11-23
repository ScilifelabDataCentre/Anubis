"About info HTMl endpoints."

import os.path
import sys

import couchdb2
import flask
import openpyxl

import anubis
from . import constants
from . import utils


blueprint = flask.Blueprint('about', __name__)

@blueprint.route('/documentation/<page>')
def documentation(page):
    "Documentation page."
    try:
        with open(os.path.join(flask.current_app.config['DOC_DIRPATH'],
                               f"{page}.md")) as infile:
            text = infile.read()
    except (OSError, IOError):
        utils.flash_error('No such documentation page.')
        return flask.redirect(utils.referrer_or_home())
    title = page.replace('-', ' ')
    return flask.render_template('about/documentation.html',
                                 title=title, text=text)

@blueprint.route('/contact')
def contact():
    "Contact information page."
    try:
        filepath = os.path.normpath(
            os.path.join(flask.current_app.config['ROOT_DIRPATH'], 
                         '../site/contact.md'))
        with open(filepath) as infile:
            text = infile.read()
    except (OSError, IOError):
        utils.flash_error('No contact information available.')
        return flask.redirect(utils.referrer_or_home())
    return flask.render_template('about/contact.html', text=text)

@blueprint.route('/software')
def software():
    "Show software versions."
    return flask.render_template('about/software.html',
                                 software=get_software())

def get_software():
    v = sys.version_info
    return [
        (constants.SOURCE_NAME, anubis.__version__, constants.SOURCE_URL),
        ('Python', f"{v.major}.{v.minor}.{v.micro}", 'https://www.python.org/'),
        ('Flask', flask.__version__, 'http://flask.pocoo.org/'),
        ('CouchDB server', flask.g.db.server.version, 
         'https://couchdb.apache.org/'),
        ('CouchDB2 interface', couchdb2.__version__, 
         'https://pypi.org/project/couchdb2'),
        ('openpyxl', openpyxl.__version__,
         'https://openpyxl.readthedocs.io/en/stable/'),
        ('Bootstrap', constants.BOOTSTRAP_VERSION, 'https://getbootstrap.com/'),
        ('jQuery', constants.JQUERY_VERSION, 'https://jquery.com/'),
        ('DataTables', constants.DATATABLES_VERSION, 'https://datatables.net/'),
        ("Feather of Ma'at icon", 'freepik',
         'https://www.flaticon.com/authors/freepik'),
    ]

@blueprint.route('/settings')
@utils.login_required
def settings():
    "Display all configuration settings."
    if not (flask.g.am_admin or flask.g.am_staff):
        utils.flash_error('You are not allowed to view configuration settings.')
        return flask.redirect(flask.url_for('home'))
    config = flask.current_app.config.copy()
    for key in ['SECRET_KEY', 'COUCHDB_PASSWORD', 'MAIL_PASSWORD']:
        if config[key]:
            config[key] = '<hidden>'
    return flask.render_template('about/settings.html',
                                 items=sorted(config.items()))
