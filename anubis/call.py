"Call for submissions."

import copy

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('call', __name__)

@blueprint.route('/', methods=['GET', 'POST'])
@utils.admin_required
def create():
    "Create a new call from scratch."
    if utils.http_GET():
        return flask.render_template('call/create.html')

    elif utils.http_POST():
        try:
            with CallSaver() as saver:
                saver.set_identifier(flask.request.form.get('identifier'))
                saver.set_title(flask.request.form.get('title'))
            call = saver.doc
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(flask.url_for('.create'))
        return flask.redirect(flask.url_for('.edit', cid=call['identifier']))

@blueprint.route('/<cid>')
def display(cid):
    "Display the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('call/display.html', call=call)

@blueprint.route('/<cid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.admin_required
def edit(cid):
    "Edit the call, or delete it."
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/edit.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.set_title(flask.request.form.get('title'))
                saver['description'] = flask.request.form.get('description')
                saver['opens'] = utils.normalize_datetime(
                    flask.request.form.get('opens'))
                saver['closes'] = utils.normalize_datetime(
                    flask.request.form.get('closes'))
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

    elif utils.http_DELETE():
        if not is_editable(call):
            utils.flash_error('call cannot be deleted')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        utils.delete(call)
        utils.flash_message(f"deleted call {call['identifier']}:{call['title']}")
        return flask.redirect(flask.url_for('calls.all'))


@blueprint.route('/<cid>/field', methods=['POST'])
@utils.admin_required
def add_field(cid):
    "Add an input field to the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_field(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.add_field', cid=call['identifier']))
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<cid>/field/<fid>', methods=['POST', 'DELETE'])
@utils.admin_required
def edit_field(cid, fid):
    "Edit the input field of the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_field(fid, form=flask.request.form)
        except (KeyError, ValueError) as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

    elif utils.http_DELETE():
        with CallSaver(call) as saver:
            saver.delete_field(fid)
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<cid>/clone', methods=['GET', 'POST'])
@utils.admin_required
def clone(cid):
    "Clone the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/clone.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver() as saver:
                saver.set_identifier(flask.request.form.get('identifier'))
                saver.set_title(flask.request.form.get('title'))
                saver.doc['fields'] = copy.deepcopy(call['fields'])
            new = saver.doc
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(flask.url_for('.clone', cid=cid))
        return flask.redirect(flask.url_for('.edit', cid=new['identifier']))

@blueprint.route('/<cid>/logs')
@utils.admin_required
def logs(cid):
    "Display the log records of the call."
    call = get_call(cid)
    if call is None:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Call {call['identifier']}",
        cancel_url=flask.url_for('.display', cid=call['identifier']),
        logs=utils.get_logs(call['_id']))

@blueprint.route('/<cid>/submission', methods=['POST'])
@utils.login_required
def submission(cid):
    "Create a new submission within the call."
    import anubis.submission 
    call = get_call(cid)
    if call is None:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))

    if not call['tmp']['is_open']:
        utils.flash_error(f"Call {call['title']} is not open.")

    if utils.http_POST():
        with anubis.submission.SubmissionSaver() as saver:
            saver.set_call(call)
        doc = saver
        return flask.redirect(
            flask.url_for('submission.edit', sid=doc['identifier']))


class CallSaver(utils.BaseSaver):
    "Call document saver context."

    DOCTYPE = constants.DOCTYPE_CALL

    def initialize(self):
        self.doc['opens'] = None
        self.doc['closes'] = None
        self.doc['fields'] = []

    def set_identifier(self, identifier):
        "Call identifier."
        if self.doc.get('identifier'):
            raise ValueError('identifier has already been set')
        if not identifier:
            raise ValueError('identifier must be provided')
        if len(identifier) > flask.current_app.config['CALL_IDENTIFIER_MAXLENGTH']:
            raise ValueError('too long identifier')
        if not constants.ID_RX.match(identifier):
            raise ValueError('invalid identifier')
        if get_call(identifier):
            raise ValueError('identifier is already in use')
        self.doc['identifier'] = identifier

    def set_title(self, title):
        "Call title: non-blank required."
        if not title:
            raise ValueError('title must be provided')
        self.doc['title'] = title

    def add_field(self, form=dict()):
        id = form.get('identifier')
        if not (id and constants.ID_RX.match(id)):
            raise ValueError('invalid field identifier')
        type = form.get('type')
        if type not in constants.INPUT_FIELD_TYPES:
            raise ValueError('invalid field type')
        title = form.get('title') or id.replace('_', ' ')
        title = ' '.join([w.capitalize() for w in title.split()])
        field = {'type': type,
                 'identifier': id,
                 'title': title,
                 'description': form.get('description') or None,
                 'required': bool(form.get('required'))
                 }
        if type in (constants.TEXT, constants.LINE):
            try:
                maxlength = int(form.get('maxlength'))
                if maxlength <= 0: raise ValueERror
            except (TypeError, ValueError):
                maxlength = None
            field['maxlength'] = maxlength
        self.doc['fields'].append(field)

    def edit_field(self, fid, form=dict()):
        for field in self.doc['fields']:
            if field['identifier'] == fid: break
        else:
            raise KeyError('no such field')
        title = form.get('title')
        if not title:
            title = ' '.join([w.capitalize() 
                              for w in fid.replace('_', ' ').split()])
        field['title'] = title
        field['description'] = form.get('description') or None
        field['required'] = bool(form.get('required'))
        if field['type'] == 'text':
            try:
                maxlength = int(form.get('maxlength'))
                if maxlength <= 0: raise ValueERror
            except (TypeError, ValueError):
                maxlength = None
            field['maxlength'] = maxlength
        else:
            raise ValueError('invalid field type')

    def delete_field(self, fid):
        for pos, field in enumerate(self.doc['fields']):
            if field['identifier'] == fid:
                self.doc['fields'].pop(pos)
                break
        else:
            raise ValueError('no such field')


def get_call(cid):
    "Return the call with the given identifier."
    result = [r.doc for r in flask.g.db.view('calls', 'identifier',
                                             key=cid,
                                             include_docs=True)]
    if len(result) == 1:
        return add_call_tmp(result[0])
    else:
        return None

def add_call_tmp(call):
    """Set the 'tmp' property of the call.
    This is computed data that will not be stored with the document.
    Depends on login, privileges, etc.
    """
    from anubis.submissions import get_submissions_count
    call['tmp'] = tmp = {}
    # Submissions count
    if flask.g.is_admin:
        tmp['submissions_count'] = get_submissions_count(call=call)
    if flask.g.current_user:
        tmp['my_submissions_count'] = get_submissions_count(
            username=flask.g.current_user['username'], call=call)
    # Open/closed status
    now = utils.normalized_local_now()
    if call['opens']:
        if call['opens'] > now:
            tmp['is_open'] = False
            tmp['is_closed'] = False
            tmp['text'] = 'Not yet open.'
            tmp['color'] = 'secondary'
        elif call['closes']:
            remaining = utils.days_remaining(call['closes'])
            if remaining > 7.0:
                tmp['is_open'] = True
                tmp['is_closed'] = False
                tmp['text'] = f"{remaining:.0f} days remaining."
                tmp['color'] = 'success'
            elif remaining > 2.0:
                tmp['is_open'] = True
                tmp['is_closed'] = False
                tmp['text'] = f"{remaining:.0f} days remaining."
                tmp['color'] = 'info'
            elif remaining >= 1.0:
                tmp['is_open'] = True
                tmp['is_closed'] = False
                tmp['text'] = "Less than two days remaining."
                tmp['color'] = 'warning'
            elif remaining >= 0.0:
                tmp['is_open'] = True
                tmp['is_closed'] = False
                tmp['text'] = "Less than one day remaining."
                tmp['color'] = 'danger'
            else:
                tmp['is_open'] = False
                tmp['is_closed'] = True
                tmp['text'] = 'Closed.'
                tmp['color'] = 'dark'
        else:
            tmp['is_open'] = True
            tmp['is_closed'] = False
            tmp['text'] = 'Open with no closing date.'
            tmp['color'] = 'success'
    else:
        if call['closes']:
            tmp['is_open'] = False
            tmp['is_closed'] = False
            tmp['text'] = 'No open date set.'
            tmp['color'] = 'secondary'
        else:
            tmp['is_open'] = False
            tmp['is_closed'] = False
            tmp['text'] = 'No open or close dates set.'
            tmp['color'] = 'secondary'
    # Is editable? Check open/closed and privileges.
    # XXX allow admin anything during development
    tmp['is_editable'] = flask.g.is_admin
    # if tmp['submissions_count'] != 0:
    #     tmp['is_editable'] = False
    # elif tmp['is_open']:
    #     tmp['is_editable'] = False
    # elif tmp['is_closed']:
    #     tmp['is_editable'] = False
    # else:
    #     tmp['is_editable'] = flask.g.is_admin
    return call
