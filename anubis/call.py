"Call for submissions."

import datetime

import flask

from . import constants
from . import utils


blueprint = flask.Blueprint('call', __name__)

@blueprint.route('/create', methods=['GET', 'POST'])
@utils.admin_required
def create():
    "Create a new call."
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
    "Display a call."
    print(cid)
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('call/display.html', call=call)

@blueprint.route('/<id:cid>/edit', methods=['GET', 'POST'])
def edit(cid):
    "Edit a call."
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

@blueprint.route('/<id:cid>/field', methods=['POST'])
@utils.admin_required
def add_field(cid):
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    if utils.http_POST():
        with CallSaver(call) as saver:
            saver.add_field(form=flask.request.form)
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<id:cid>/field/<id:fid>', methods=['POST', 'DELETE'])
@utils.admin_required
def edit_field(cid, fid):
    call = get_call(cid)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    if utils.http_POST():
        with CallSaver(call) as saver:
            saver.edit_field(fid, form=flask.request.form)
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))
    elif utils.http_DELETE():
        with CallSaver(call) as saver:
            saver.delete_field(fid)
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<id:cid>/logs')
@utils.admin_required
def logs(cid):
    "Display the log records of the given user."
    call = get_call(cid)
    if call is None:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'logs.html',
        title=f"Call {call['cid']}",
        cancel_url=flask.url_for('.display', cid=call['identifier']),
        logs=utils.get_logs(call['_id']))

@blueprint.route('/<id:cid>/submission', methods=['GET', 'POST'])
@utils.login_required
def submission(cid):
    "Create a new submission in the given call."
    raise NotImplementedError


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
        field = {'type': form.get('type'),
                 'identifier': form.get('identifier'),
                 'title': form.get('title') or None,
                 'description': form.get('description') or None,
                 'required': bool(form.get('required'))
                 }
        if not (field['identifier'] and
                constants.ID_RX.match(field['identifier'])):
            raise ValueError('invalid identifier')
        if field['type'] == 'text':
            pass
        else:
            raise ValueError('invalid field type')
        self.doc['fields'].append(field)

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
        call = result[0]
        update_calls([call])
        return call
    else:
        return None

def update_calls(calls):
    "Update current properties of calls: is_open, display data."
    for call in calls:
        call['current'] = {}
        now = utils.normalized_local_now()
        if call['opens']:
            if call['opens'] > now:
                call['current']['is_open'] = False
                call['current']['text'] = 'Not yet open.'
                call['current']['color'] = 'secondary'
            elif call['closes']:
                remaining = utils.days_remaining(call['closes'])
                if remaining > 7.0:
                    call['current']['is_open'] = True
                    call['current']['text'] = f"{remaining:.0f} days remaining."
                    call['current']['color'] = 'success'
                elif remaining > 2.0:
                    call['current']['is_open'] = True
                    call['current']['text'] = f"{remaining:.0f} days remaining."
                    call['current']['color'] = 'info'
                elif remaining >= 1.0:
                    call['current']['is_open'] = True
                    call['current']['text'] = "Less than two days remaining."
                    call['current']['color'] = 'warning'
                elif remaining >= 0.0:
                    call['current']['is_open'] = True
                    call['current']['text'] = "Less than one day remaining."
                    call['current']['color'] = 'warning'
                else:
                    call['current']['is_open'] = False
                    call['current']['text'] = 'Closed.'
                    call['current']['color'] = 'danger'
            else:
                call['current']['is_open'] = True
                call['current']['text'] = 'Open, no closing date.'
                call['current']['color'] = 'success'
        else:
            if call['closes']:
                call['current']['is_open'] = False
                call['current']['text'] = 'No opens date set.'
                call['current']['color'] = 'secondary'
            else:
                call['current']['is_open'] = False
                call['current']['text'] = 'No dates set.'
                call['current']['color'] = 'secondary'
            
