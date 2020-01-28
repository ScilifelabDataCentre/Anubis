"Base document saver context classes."

import copy

import flask

from . import constants
from . import utils


class BaseSaver:
    "Base document saver context."

    DOCTYPE = None
    HIDDEN_FIELDS = []

    def __init__(self, doc=None):
        if doc is None:
            self.original = {}
            self.doc = {'_id': utils.get_iuid(),
                        'created': utils.get_time()}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.prepare()

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None: return False
        self.finalize()
        self.doc['doctype'] = self.DOCTYPE
        self.doc['modified'] = utils.get_time()
        self.original.pop('cache', None)
        self.doc.pop('cache', None)
        flask.g.db.put(self.doc)
        self.finish()
        self.add_log()

    def __getitem__(self, key):
        return self.doc[key]

    def __setitem__(self, key, value):
        self.doc[key] = value

    def initialize(self):
        "Initialize the new document."
        pass

    def prepare(self):
        "Preparations before making any changes."
        pass

    def finalize(self):
        "Final changes and checks on the document."
        pass

    def finish(self):
        """Finish the save operation by performing actions that
        must be done after the document has been stored.
        """
        pass

    def add_log(self):
        """Add a log entry recording the the difference betweens the current and
        the original document, hiding values of specified keys.
        'added': list of keys for items added in the current.
        'updated': dictionary of items updated; original values.
        'removed': dictionary of items removed; original values.
        """
        added = list(set(self.doc).difference(self.original or {}))
        updated = dict([(k, self.original[k])
                        for k in set(self.doc).intersection(self.original or {})
                        if self.doc[k] != self.original[k]])
        removed = dict([(k, self.original[k])
                        for k in set(self.original or {}).difference(self.doc)])
        for key in ['_id', '_rev', 'modified']:
            try:
                added.remove(key)
            except ValueError:
                pass
        updated.pop('_rev', None)
        updated.pop('modified', None)
        for key in self.HIDDEN_FIELDS:
            if key in updated:
                updated[key] = '***'
            if key in removed:
                removed[key] = '***'
        entry = {'_id': utils.get_iuid(),
                 'doctype': constants.LOG,
                 'docid': self.doc['_id'],
                 'added': added,
                 'updated': updated,
                 'removed': removed,
                 'timestamp': utils.get_time()}
        if hasattr(flask.g, 'current_user') and flask.g.current_user:
            entry['username'] = flask.g.current_user['username']
        else:
            entry['username'] = None
        if flask.has_request_context():
            entry['remote_addr'] = str(flask.request.remote_addr)
            entry['user_agent'] = str(flask.request.user_agent)
        else:
            entry['remote_addr'] = None
            entry['user_agent'] = None
        flask.g.db.put(entry)


class AttachmentSaver(BaseSaver):
    "Document saver context handling attachments."

    def prepare(self):
        self._delete_attachments = set()
        self._add_attachments = []

    def finish(self):
        """Delete any specified attachments.
        Store the input files as attachments.
        Must be done after document is saved.
        """
        for filename in self._delete_attachments:
            rev = flask.g.db.delete_attachment(self.doc, filename)
            self.doc['_rev'] = rev
        for attachment in self._add_attachments:
            flask.g.db.put_attachment(self.doc,
                                      attachment['content'],
                                      filename=attachment['filename'],
                                      content_type=attachment['mimetype'])

    def add_attachment(self, filename, content, mimetype):
        self._add_attachments.append({'filename': filename,
                                      'content': content,
                                      'mimetype': mimetype})

    def delete_attachment(self, filename):
        self._delete_attachments.add(filename)


class FieldMixin:
    "Mixin for setting a field value in the saver."

    def set_field_value(self, field, form=dict()):
        "Set the value according to field type."
        fid = field['identifier']
        self.doc['errors'].pop(fid, None)

        if field['type'] in (constants.TEXT, constants.LINE):
            self.doc['values'][fid] = form.get(fid) or None

        elif field['type'] == constants.BOOLEAN:
            value = form.get(fid) or None
            if value:
                value = utils.to_bool(value)
            self.doc['values'][fid] = value

        elif field['type'] == constants.SELECT:
            if field.get('multiple'):
                self.doc['values'][fid] = form.getlist(fid) or []
            else:
                self.doc['values'][fid] = form.get(fid) or None

        elif field['type'] in (constants.INTEGER, constants.FLOAT, constants.SCORE):
            if field['type'] == constants.FLOAT:
                converter = float
            else:
                converter = int
            value = form.get(fid)
            if form.get(f"{fid}_na"):
                value = None
            try:
                value = converter(value)
            except (TypeError, ValueError):
                if field['required'] and value:
                    self.doc['errors'][fid] = 'invalid value'
                value = None
            if value is not None:
                if field.get('minimum') is not None:
                    if value < field['minimum']:
                        self.doc['errors'][fid] = 'value is too low'
                if field.get('maximum') is not None:
                    if value > field['maximum']:
                        self.doc['errors'][fid] = 'value is too high'
            self.doc['values'][fid] = value

        elif field['type'] in constants.DOCUMENT:
            infile = flask.request.files.get(fid)
            if infile:
                if self.doc['values'].get(fid) and \
                   self.doc['values'][fid] != infile.name:
                    self.delete_attachment(self.doc['values'][fid])
                self.doc['values'][fid] = infile.filename
                self.add_attachment(infile.filename,
                                    infile.read(),
                                    infile.mimetype)

        # Error message already set; skip
        if self.doc['errors'].get(fid): return
        if field['required'] and self.doc['values'][fid] is None:
            self.doc['errors'][fid] = 'missing value'
