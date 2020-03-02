"""Load a dump tar file into the CouchDB database.

The file to load must be given as a command line argument.

NOTE: The database must exist. Items are just added to the
database. Will overwrite data with the same identifier, and keep other
pre-existing data, so inconsistencies may result. Should only be used
with an empty database.
"""

import argparse
import json
import os
import tarfile
import time

import flask

import anubis.config
from anubis import constants
from anubis import utils


def undump(db, filepath):
    """Reverse of dump; load all items from a tar file.
    NOTE: The database must exist. Items are just added to the
    database. Will overwrite data with the same identifier, and keep
    other pre-existing data, so inconsistencies may result. Should
    only be used with an empty database.
    """
    count_items = 0
    count_files = 0
    attachments = dict()
    infile = tarfile.open(filepath, mode='r')
    for item in infile:
        itemfile = infile.extractfile(item)
        itemdata = itemfile.read()
        itemfile.close()
        if item.name in attachments:
            # This relies on an attachment being after its item in the tarfile.
            db.put_attachment(doc, itemdata, **attachments.pop(item.name))
            count_files += 1
        else:
            doc = json.loads(itemdata)
            atts = doc.pop('_attachments', dict())
            db.put(doc)
            count_items += 1
            for attname, attinfo in atts.items():
                key = "{0}_att/{1}".format(doc['_id'], attname)
                attachments[key] = dict(filename=attname,
                                        content_type=attinfo['content_type'])
        if count_items % 100 == 0:
            print(count_items, 'items loaded...')
    infile.close()
    # This will be executed on the command line, so output to console, not log.
    print('undumped', count_items, 'items and', 
          count_files, 'files from', filepath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load dump into database.')
    parser.add_argument('dumpfile', metavar='FILE', type=str,
                        help='The dump file to load into the database.')
    args =  parser.parse_args()
    app = flask.Flask(__name__)
    with app.app_context():
        anubis.config.init(app)
        undump(utils.get_db(), args.dumpfile)
