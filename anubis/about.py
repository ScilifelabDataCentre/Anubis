"About info HTMl endpoints."

import sys

import couchdb2
import flask
import jsonschema

import anubis
from . import constants
from . import utils


blueprint = flask.Blueprint('about', __name__)

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
        ('jsonschema', jsonschema.__version__, 
         'https://pypi.org/project/jsonschema'),
        ('Bootstrap', constants.BOOTSTRAP_VERSION, 'https://getbootstrap.com/'),
        ('jQuery', constants.JQUERY_VERSION, 'https://jquery.com/'),
        ('DataTables', constants.DATATABLES_VERSION, 'https://datatables.net/'),
        ("Feather of Ma'at icon", 'freepik',
         'https://www.flaticon.com/authors/freepik'),
    ]

@blueprint.route('/settings')
@utils.admin_required
def settings():
    config = flask.current_app.config.copy()
    for key in ['SECRET_KEY', 'MAIL_PASSWORD']:
        if config.get(key):
            config[key] = '<hidden>'
    return flask.render_template('about/settings.html',
                                 items=sorted(config.items()))
