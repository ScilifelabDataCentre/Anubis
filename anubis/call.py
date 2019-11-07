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
                saver.set_title(flask.request.form.get('title'))
                saver.set_prefix(flask.request.form.get('prefix'))
            call = saver.doc
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(flask.url_for('.create'))
        return flask.redirect(flask.url_for('.edit', prefix=call['prefix']))

@blueprint.route('/<name:prefix>')
def display(prefix):
    "Display a call."
    call = get_call(prefix)
    if not call:
        utils.flash_error('no such call')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template('call/display.html', call=call)

@blueprint.route('/<name:prefix>/edit', methods=['GET', 'POST'])
def edit(prefix):
    "Edit a call."
    call = get_call(prefix)
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
        return flask.redirect(flask.url_for('.display', prefix=call['prefix']))

@blueprint.route('/<name:prefix>/logs')
@utils.admin_required
def logs(prefix):
    "Display the log records of the given user."
    call = get_call(prefix)
    if call is None:
        utils.flash_error('no such prefix')
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'logs.html',
        title=f"Call {call['prefix']}",
        cancel_url=flask.url_for('.display', prefix=call['prefix']),
        logs=utils.get_logs(call['_id']))

@blueprint.route('/<name:callid>/submission', methods=['GET', 'POST'])
@utils.login_required
def submission():
    "Create a new submission in the given call."
    raise NotImplementedError


class CallSaver(utils.BaseSaver):
    "Call document saver context."

    DOCTYPE = constants.DOCTYPE_CALL

    def initialize(self):
        self.doc['opened'] = None
        self.doc['closed'] = None

    def set_title(self, title):
        "Call title: non-blank required."
        if not title:
            raise ValueError('title must be provided')
        self.doc['title'] = title

    def set_prefix(self, prefix):
        "Call prefix: used for submission identifiers."
        if self.doc.get('prefix'):
            raise ValueError('prefix has already been set')
        if not prefix:
            raise ValueError('prefix must be provided')
        if len(prefix) > flask.current_app.config['PREFIX_MAXLENGTH']:
            raise ValueError('too long prefix')
        prefix = prefix.upper()
        if not constants.PREFIX_RX.match(prefix):
            raise ValueError('invalid prefix')
        if get_call(prefix):
            raise ValueError('prefix is already in use')
        self.doc['prefix'] = prefix


def get_call(prefix):
    "Return the call with the given prefix."
    result = [r.doc for r in flask.g.db.view('calls', 'prefix',
                                             key=prefix.upper(),
                                             include_docs=True)]
    if len(result) == 1:
        return result[0]
    else:
        return None
