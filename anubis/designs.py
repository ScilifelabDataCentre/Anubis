"CouchDB design documents definition and update."

import flask

from . import utils


DESIGNS = {
    'users': {
        'views': {
            'username': {'map': "function(doc) {if (doc.doctype !== 'user') return; emit(doc.username, null);}"},
            'email': {'map': "function(doc) {if (doc.doctype !== 'user') return;  emit(doc.email, null);}"},
            'apikey': {'map': "function(doc) {if (doc.doctype !== 'user') return;  emit(doc.apikey, null);}"},
            'role': {'map': "function(doc) {if (doc.doctype !== 'user') return;  emit(doc.role, null);}"},
        }
    },
    'logs': {
        'views': {
            'doc': {'map': "function (doc) {if (doc.doctype !== 'log') return; emit([doc.docid, doc.timestamp], null);}"}
        }
    },
    'calls': {
        'views': {
            'identifier': {'map': "function (doc) {if (doc.doctype !== 'call') return; emit(doc.identifier, null);}"},
            'closes': {'map': "function (doc) {if (doc.doctype !== 'call' || !doc.closes || !doc.opens) return; emit(doc.closes, null);}"},
            'open_ended': {'map': "function (doc) {if (doc.doctype !== 'call' || !doc.opens || doc.closes) return; emit(doc.opens, null);}"}
        }
    },
    'submissions': {
        'views': {
            'identifier': {'map': "function (doc) {if (doc.doctype !== 'submission') return; emit(doc.identifier, null);}"},
            # NOTE: excludeds submissions not marked 'submitted'
            'call': {'reduce': '_count',
                     'map': "function (doc) {if (doc.doctype !== 'submission' || !doc.submitted) return; emit(doc.call, null);}"},
            # NOTE: includes submissions not marked 'submitted'
            'user': {'reduce': '_count',
                     'map': "function (doc) {if (doc.doctype !== 'submission') return; emit(doc.user, null);}"},
            'user_call': {'reduce': '_count',
                          'map': "function (doc) {if (doc.doctype !== 'submission') return; emit([doc.user, doc.call], null);}"},
        }
    },
}

def update():
    "Update the CouchDB database design documents."
    logger = utils.get_logger()
    for name, doc in DESIGNS.items():
        if flask.g.db.put_design(name, doc):
            logger.info(f"Updated design document '{name}'.")
