"Base document saver context classes."

import copy
import os.path

import flask

from anubis import constants
from anubis import utils


class Saver:
    "Document saver context."

    DOCTYPE = None
    HIDDEN_FIELDS = []

    def __init__(self, doc=None, id=None, db=None):
        if doc is None:
            self.original = {}
            self.doc = {"_id": id or utils.get_iuid(), "created": utils.get_time()}
            self.initialize()
        else:
            self.original = copy.deepcopy(doc)
            self.doc = doc
        self.db = db or flask.g.db
        self.prepare()
        # Special flag when a repeat field has changed value.
        # May be used to immediately redisplay the edit page
        # with changed number of input fields.
        self.repeat_changed = False

    def __enter__(self):
        return self

    def __exit__(self, etyp, einst, etb):
        if etyp is not None:
            return False
        self.finish()
        self.doc["doctype"] = self.DOCTYPE
        self.doc["modified"] = utils.get_time()
        self.db.put(self.doc)
        self.wrapup()
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
        self._delete_attachments = set()
        self._add_attachments = []

    def add_attachment(self, filename, content, mimetype):
        """If the filename is already in use, add a numerical suffix.
        Return the final filename.
        """
        current = set(self.doc.get("_attachments", {}).keys())
        current.update([a["filename"] for a in self._add_attachments])
        basename, ext = os.path.splitext(filename)
        count = 0
        while filename in current:
            count += 1
            filename = f"{basename}_{count}{ext}"
        self._add_attachments.append(
            {"filename": filename, "content": content, "mimetype": mimetype}
        )
        return filename

    def delete_attachment(self, filename):
        self._delete_attachments.add(filename)

    def finish(self):
        """Final changes and checks on the document before storing it.
        Remove any temporary data from the document.
        """
        self.doc.pop("tmp", None)

    def wrapup(self):
        """Delete any specified attachments.
        Store the input files as attachments.
        Must be done after document is stored subsequent to changes of other items.
        """
        for filename in self._delete_attachments:
            self.db.delete_attachment(self.doc, filename)
        for attachment in self._add_attachments:
            self.db.put_attachment(
                self.doc,
                attachment["content"],
                filename=attachment["filename"],
                content_type=attachment["mimetype"],
            )

    def add_log(self):
        """Add a log entry recording the the difference betweens the current and
        the original document, hiding values of specified keys.
        'added': list of keys for items added in the current.
        'updated': dictionary of items updated; original values.
        'removed': dictionary of items removed; original values.
        """
        added = list(set(self.doc).difference(self.original or {}))
        updated = dict(
            [
                (k, self.original[k])
                for k in set(self.doc).intersection(self.original or {})
                if self.doc[k] != self.original[k]
            ]
        )
        removed = dict(
            [
                (k, self.original[k])
                for k in set(self.original or {}).difference(self.doc)
            ]
        )
        for key in ["_id", "_rev", "modified"]:
            try:
                added.remove(key)
            except ValueError:
                pass
        updated.pop("_rev", None)
        updated.pop("modified", None)
        for key in self.HIDDEN_FIELDS:
            if key in updated:
                updated[key] = "***"
            if key in removed:
                removed[key] = "***"
        entry = {
            "_id": utils.get_iuid(),
            "doctype": constants.LOG,
            "docid": self.doc["_id"],
            "added": added,
            "updated": updated,
            "removed": removed,
            "timestamp": utils.get_time(),
        }
        if hasattr(flask.g, "current_user") and flask.g.current_user:
            entry["username"] = flask.g.current_user["username"]
        else:
            entry["username"] = None
        if flask.has_request_context():
            entry["remote_addr"] = str(flask.request.remote_addr)
            entry["user_agent"] = str(flask.request.user_agent)
        else:
            entry["remote_addr"] = None
            entry["user_agent"] = None
        self.db.put(entry)


class FieldSaverMixin:
    "Mixin for setting a field value in the saver."

    def set_fields_values(self, fields, form=dict()):
        "Set the values of the fields according to field type."
        # Remember which fields actually are current.
        self.current_fields = set()

        # First set the non-repeat fields; the number of
        # repeats is determined by fields in that set.
        for field in fields:
            if field.get("repeat"):
                continue
            # The 'fields' argument is needed to clean away
            # superfluous values if repeat number is reduced.
            self.set_single_field_value(field["identifier"], field, form, fields)
        # Then set the values of the repeat fields.
        for field in fields:
            if not field.get("repeat"):
                continue
            n_repeat = self.doc["values"].get(field["repeat"])
            if not n_repeat:
                continue
            for n in range(1, n_repeat + 1):
                fid = f"{field['identifier']}-{n}"
                self.set_single_field_value(fid, field, form)

        # Remove all data for fields that no longer exist.
        removed = set()
        for fid in set(self.doc["values"]).difference(self.current_fields):
            removed.add(self.doc["values"].pop(fid))

        # Delete attachment if it is among the removed values.
        # This is slightly risky: if a filename happens to be the same
        # as a removed value originating from another field,
        # the deletion may be in error. But this should be rare...
        for filename in self.doc.get("_attachments", {}):
            if filename in removed:
                self.delete_attachment(filename)

        # Remove all errors for fields that no longer exist.
        for fid in set(self.doc["errors"]).difference(self.current_fields):
            self.doc["errors"].pop(fid)

    def set_single_field_value(self, fid, field, form, fields=None):
        "Set the single field value."
        # Remember which fields actually exist right now.
        self.current_fields.add(fid)

        # Not allowed to edit the value if not staff.
        # Skipping here implies that an error for the value
        # in the field cannot be erased by ordinary user.
        if (field.get("staff") or field.get("staffonly")) and not (
            flask.g.am_admin or flask.g.am_staff
        ):
            return

        # Remove any old error message for this field.
        self.doc["errors"].pop(fid, None)

        if field["type"] in (constants.LINE, constants.EMAIL, constants.TEXT):
            text = form.get(fid)
            if text:
                text = text.replace("\r\n", "\n")
            self.doc["values"][fid] = text or None

        elif field["type"] == constants.BOOLEAN:
            value = form.get(fid) or None
            if value:
                value = utils.to_bool(value)
            self.doc["values"][fid] = value

        elif field["type"] == constants.SELECT:
            if field.get("multiple"):
                if fid in form:
                    self.doc["values"][fid] = form.getlist(fid)
                else:
                    self.doc["values"][fid] = []
                if field["required"] and not self.doc["values"][fid]:
                    self.doc["errors"][fid] = "Missing value."
            else:
                self.doc["values"][fid] = form.get(fid) or None

        elif field["type"] in (
            constants.INTEGER,
            constants.FLOAT,
            constants.SCORE,
            constants.RANK,
        ):
            if field["type"] == constants.FLOAT:
                converter = float
            else:
                converter = int
            value = form.get(fid)
            if form.get(f"{fid}_novalue"):
                value = None
            try:
                value = converter(value)
            except (TypeError, ValueError):
                if field["required"] and value:
                    self.doc["errors"][fid] = "Invalid value."
                value = None
            if value is not None:
                if field.get("minimum") is not None:
                    if value < field["minimum"]:
                        self.doc["errors"][fid] = "Value is too low."
                if field.get("maximum") is not None:
                    if value > field["maximum"]:
                        self.doc["errors"][fid] = "Value is too high."
            self.doc["values"][fid] = value

        elif field["type"] == constants.DOCUMENT:
            if form.get(f"{fid}_remove"):
                if self.doc["values"].get(fid):
                    self.delete_attachment(self.doc["values"][fid])
                self.doc["values"][fid] = None
            else:
                infile = flask.request.files.get(fid)
                if infile:  # New document given.
                    if (
                        self.doc["values"].get(fid)
                        and self.doc["values"][fid] != infile.filename
                    ):
                        self.delete_attachment(self.doc["values"][fid])
                    filename = self.add_attachment(
                        infile.filename, infile.read(), infile.mimetype
                    )
                    self.doc["values"][fid] = filename
                else:
                    filename = self.doc["values"].get(fid)
                if filename and field.get("extensions"):
                    extension = os.path.splitext(filename)[1].lstrip(".").lower()
                    if extension not in field["extensions"]:
                        self.doc["errors"][fid] = "Invalid file type."
            if field["required"] and not self.doc["values"].get(fid):
                self.doc["errors"][fid] = "Missing document."

        elif field["type"] == constants.REPEAT:
            value = form.get(fid) or None
            try:
                value = int(value)
            except (TypeError, ValueError):
                if field["required"]:
                    self.doc["errors"][fid] = "Invalid or missing value."
                value = None
            if (
                value is not None
                and field.get("maximum") is not None
                and value > field["maximum"]
            ):
                self.doc["errors"][fid] = "Value is too high."
            if (
                value is not None
                and field.get("minimum") is not None
                and value < field["minimum"]
            ):
                self.doc["errors"][fid] = "Value is too low."
            self.repeat_changed = (
                self.repeat_changed or self.doc["values"].get(fid) != value
            )
            self.doc["values"][fid] = value

        if self.doc["errors"].get(fid):
            return  # Error message already set; skip
        if field["required"] and self.doc["values"].get(fid) is None:
            self.doc["errors"][fid] = "Missing value."


class AccessSaverMixin:
    "Mixin to change access privileges."

    def set_access(self, form=dict()):
        """Set the access of the object according to the form input.
        Raise ValueError if no such user.
        """
        import anubis.user

        username = form.get("username")
        user = anubis.user.get_user(username=username)
        if user is None:
            user = anubis.user.get_user(email=username)
        if user is None:
            raise ValueError("No such user.")
        if form.get("access") == "view":
            # Remove edit access if view access explicitly specified.
            try:
                self.doc["access_edit"].remove(user["username"])
            except (KeyError, ValueError):
                pass
            view = set(self.doc.setdefault("access_view", []))
            view.add(user["username"])
            self.doc["access_view"] = list(view)
        elif form.get("access") == "edit":
            view = set(self.doc.setdefault("access_view", []))
            view.add(user["username"])
            self.doc["access_view"] = list(view)
            edit = set(self.doc.setdefault("access_edit", []))
            edit.add(user["username"])
            self.doc["access_edit"] = list(edit)

    def remove_access(self, form=dict()):
        """Remove the access of the object according to the form input.
        Raise ValueError if no such user.
        """
        import anubis.user

        username = form.get("username")
        user = anubis.user.get_user(username=username)
        if user is None:
            user = anubis.user.get_user(email=username)
        if user is None:
            raise ValueError("No such user.")
        try:
            self.doc["access_view"].remove(user["username"])
        except (KeyError, ValueError):
            pass
        try:
            self.doc["access_edit"].remove(user["username"])
        except (KeyError, ValueError):
            pass
