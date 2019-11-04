"About API endpoints."

import http.client

import flask

import anubis.about
from .. import utils


blueprint = flask.Blueprint('api_about', __name__)

@blueprint.route('/software')
def software():
    result = [{'name': s[0], 'version': s[1], 'href': s[2]}
              for s in anubis.about.get_software()]
    return utils.jsonify(utils.get_json(software=result),
                         schema='/about/software')
