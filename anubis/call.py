"Call for proposals."

import copy

import flask

from . import constants
from . import utils
from .saver import AttachmentsSaver


def init(app):
    "Initialize; update CouchDB design documents."
    db = utils.get_db(app=app)
    if db.put_design('calls', DESIGN_DOC):
        print(' > Updated calls design document.')

DESIGN_DOC = {
    'views': {
        'identifier': {'map': "function (doc) {if (doc.doctype !== 'call') return; emit(doc.identifier, null);}"},
        'closes': {'map': "function (doc) {if (doc.doctype !== 'call' || !doc.closes || !doc.opens) return; emit(doc.closes, null);}"},
        'open_ended': {'map': "function (doc) {if (doc.doctype !== 'call' || !doc.opens || doc.closes) return; emit(doc.opens, null);}"},
        'reviewer': {'map': "function (doc) {if (doc.doctype !== 'call') return; for (var i=0; i < doc.reviewers.length; i++) {emit(doc.reviewers[i], doc.identifier); }}"},
    }
}

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
    from .proposals import get_call_user_proposal
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not allow_view(call):
        utils.flash_error('You are not allowed to view the call.')
        return flask.redirect(flask.url_for('home'))
    if flask.g.current_user:
        my_proposal = get_call_user_proposal(cid, 
                                             flask.g.current_user['username'])
    else:
        my_proposal = None
    return flask.render_template('call/display.html',
                                 call=call,
                                 my_proposal=my_proposal,
                                 am_reviewer=am_reviewer(call),
                                 allow_edit=allow_edit(call),
                                 allow_delete=allow_delete(call),
                                 allow_proposal=allow_proposal(call),
                                 allow_view_reviews=allow_view_reviews(call))

@blueprint.route('/<cid>/edit', methods=['GET', 'POST', 'DELETE'])
@utils.admin_required
def edit(cid):
    "Edit the call, or delete it."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        if not allow_edit(call):
            utils.flash_error('You are not allowed to edit this call.')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        return flask.render_template('call/edit.html', call=call)

    elif utils.http_POST():
        if not allow_edit(call):
            utils.flash_error('You are not allowed to edit this call.')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        try:
            with CallSaver(call) as saver:
                saver.set_title(flask.request.form.get('title'))
                saver['description'] = flask.request.form.get('description')
                saver['opens'] = utils.normalize_datetime(
                    flask.request.form.get('opens'))
                saver['closes'] = utils.normalize_datetime(
                    flask.request.form.get('closes'))
                saver['reviews_due'] = utils.normalize_datetime(
                    flask.request.form.get('reviews_due'))
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

    elif utils.http_DELETE():
        if not allow_delete(call):
            utils.flash_error('You may not delete the call.')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        utils.delete(call)
        utils.flash_message(f"Deleted call {call['identifier']}:{call['title']}.")
        return flask.redirect(flask.url_for('calls.all'))

@blueprint.route('/<cid>/documents', methods=['GET', 'POST'])
@utils.admin_required
def documents(cid):
    "Display documents for delete, or add document (attachment file)."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/documents.html', call=call)

    elif utils.http_POST():
        infile = flask.request.files.get('document')
        if infile:
            description = flask.request.form.get('document_description')
            with CallSaver(call) as saver:
                saver.add_document(infile, description)
        else:
            utils.flash_error('No document selected.')
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<cid>/documents/<documentname>',
                 methods=['GET', 'POST', 'DELETE'])
def document(cid, documentname):
    "Download the given document (attachment file), or delete it."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        state = get_state(call)
        if not (flask.g.am_admin or state['is_published']):
            utils.flash_error(f"Call {call['title']} has not been published.")
            return flask.redirect(flask.url_for('home'))
        try:
            stub = call['_attachments'][documentname]
        except KeyError:
            utils.flash_error('No such document in call.')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        outfile = flask.g.db.get_attachment(call, documentname)
        response = flask.make_response(outfile.read())
        response.headers.set('Content-Type', stub['content_type'])
        response.headers.set('Content-Disposition', 'attachment', 
                             filename=documentname)
        return response

    elif utils.http_DELETE():
        if not flask.g.am_admin:
            utils.flash_error('You may not delete a document in the call.')
            return flask.redirect(
                flask.url_for('.display', cid=call['identifier']))
        with CallSaver(call) as saver:
            saver.delete_document(documentname)
        return flask.redirect(
            flask.url_for('.documents', cid=call['identifier']))

@blueprint.route('/<cid>/proposal', methods=['GET', 'POST'])
@utils.admin_required
def proposal(cid):
    "Display proposal fields for delete, and add field."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/proposal.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_proposal_field(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.proposal', cid=call['identifier']))

@blueprint.route('/<cid>/proposal/<fid>', methods=['POST', 'DELETE'])
@utils.admin_required
def proposal_field(cid, fid):
    "Edit or delete the proposal field."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_proposal_field(fid, form=flask.request.form)
        except (KeyError, ValueError) as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.proposal', cid=call['identifier']))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_proposal_field(fid)
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(
            flask.url_for('.proposal', cid=call['identifier']))

@blueprint.route('/<cid>/reviewers', methods=['GET', 'POST', 'DELETE'])
@utils.admin_required
def reviewers(cid):
    "Edit the list of reviewers."
    from .user import get_user
    from .proposals import get_call_user_proposal
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/reviewers.html', call=call)

    elif utils.http_POST():
        reviewer = flask.request.form.get('reviewer')
        if not reviewer:
            utils.flash_error('No reviewer specified.')
            return flask.redirect(
                flask.url_for('.reviewers', cid=call['identifier']))
        user = get_user(username=reviewer)
        if user is None:
            user = get_user(email=reviewer)
        if user is None:
            utils.flash_error('No such user.')
            return flask.redirect(
                flask.url_for('.reviewers', cid=call['identifier']))
        if get_call_user_proposal(cid, user['username']):
            utils.flash_error('User has a proposal in the call.')
            return flask.redirect(
                flask.url_for('.reviewers', cid=call['identifier']))

        if user['username'] not in call['reviewers']:
            with CallSaver(call) as saver:
                saver['reviewers'].append(user['username'])
                if utils.to_bool(flask.request.form.get('chair')):
                    saver['chairs'].append(user['username'])
        return flask.redirect(
            flask.url_for('.reviewers', cid=call['identifier']))

    elif utils.http_DELETE():
        reviewer = flask.request.form.get('reviewer')
        if reviewer:
            with CallSaver(call) as saver:
                try:
                    saver['reviewers'].remove(reviewer)
                except ValueError:
                    pass
                try:
                    saver['chairs'].remove(reviewer)
                except ValueError:
                    pass
        return flask.redirect(
            flask.url_for('.reviewers', cid=call['identifier']))

@blueprint.route('/<cid>/review', methods=['GET', 'POST'])
@utils.admin_required
def review(cid):
    "Display review fields for delete, and add field."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/review.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.add_review_field(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.review', cid=call['identifier']))

@blueprint.route('/<cid>/review/<fid>', methods=['POST', 'DELETE'])
@utils.admin_required
def review_field(cid, fid):
    "Edit or delete the review field."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_review_field(fid, form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.review', cid=call['identifier']))

    elif utils.http_DELETE():
        try:
            with CallSaver(call) as saver:
                saver.delete_review_field(fid)
        except ValueError as error:
            utils.flash_error(str(error))
        return flask.redirect(flask.url_for('.review', cid=call['identifier']))

@blueprint.route('/<cid>/access', methods=['GET', 'POST'])
@utils.admin_required
def access(cid):
    "Edit the access flags for the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/access.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver(call) as saver:
                saver.edit_access(form=flask.request.form)
        except ValueError as error:
            utils.flash_error(str(error))
            return flask.redirect(
                flask.url_for('.access', cid=call['identifier']))
        return flask.redirect(flask.url_for('.display', cid=call['identifier']))

@blueprint.route('/<cid>/clone', methods=['GET', 'POST'])
@utils.admin_required
def clone(cid):
    "Clone the call."
    call = get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    if utils.http_GET():
        return flask.render_template('call/clone.html', call=call)

    elif utils.http_POST():
        try:
            with CallSaver() as saver:
                saver.set_identifier(flask.request.form.get('identifier'))
                saver.set_title(flask.request.form.get('title'))
                saver.doc['proposal'] = copy.deepcopy(call['proposal'])
                # Do not copy documents.
                # Do not copy reviewers or chairs.
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
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))

    return flask.render_template(
        'logs.html',
        title=f"Call {call['identifier']}",
        back_url=flask.url_for('.display', cid=call['identifier']),
        logs=utils.get_logs(call['_id']))

@blueprint.route('/<cid>/create_proposal', methods=['POST'])
@utils.login_required
def create_proposal(cid):
    "Create a new proposal within the call. Redirect to an existing proposal."
    from .proposal import ProposalSaver
    from .proposals import get_call_user_proposal
    call = get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not call['cache']['is_open']:
        utils.flash_error("The call is not open.")
        return flask.redirect(flask.url_for('.display', cid=cid))
    if not allow_proposal(call):
        utils.flash_error('You may not create a proposal in this call.')
        return flask.redirect(flask.url_for('.display', cid=cid))

    if utils.http_POST():
        proposal = get_call_user_proposal(cid, flask.g.current_user['username'])
        if proposal:
            utils.flash_message('Proposal already exists for the call.')
            return flask.redirect(
                flask.url_for('proposal.display', pid=proposal['identifier']))
        else:
            with ProposalSaver(call=call) as saver:
                pass
            return flask.redirect(
                flask.url_for('proposal.edit', pid=saver.doc['identifier']))


class CallSaver(AttachmentsSaver):
    "Call document saver context."

    DOCTYPE = constants.CALL

    def initialize(self):
        self.doc['opens'] = None
        self.doc['closes'] = None
        self.doc['proposal'] = []
        self.doc['documents'] = []
        self.doc['review'] = []
        self.doc['reviewers'] = []
        self.doc['chairs'] = []
        self.doc['access'] = {k: False for k in constants.ACCESS}

    def set_identifier(self, identifier):
        "Call identifier."
        if self.doc.get('identifier'):
            raise ValueError('Identifier has already been set.')
        if not identifier:
            raise ValueError('Identifier must be provided.')
        if len(identifier) > flask.current_app.config['CALL_IDENTIFIER_MAXLENGTH']:
            raise ValueError('Too long identifier.')
        if not constants.ID_RX.match(identifier):
            raise ValueError('Invalid identifier.')
        if get_call(identifier):
            raise ValueError('Identifier is already in use.')
        self.doc['identifier'] = identifier

    def set_title(self, title):
        "Call title: non-blank required."
        if not title:
            raise ValueError('Title must be provided.')
        self.doc['title'] = title

    def add_proposal_field(self, form=dict()):
        "Add a field to the proposal definition."
        field = self.get_new_field(form=form)
        if field['identifier'] in [f['identifier'] 
                                   for f in self.doc['proposal']]:
            raise ValueError('Field identifier is already in use.')
        self.doc['proposal'].append(field)

    def get_new_field(self, form=dict()):
        "Get the field definition from the form."
        fid = form.get('identifier')
        if not (fid and constants.ID_RX.match(fid)):
            raise ValueError('Invalid field identifier.')
        type = form.get('type')
        if type not in constants.FIELD_TYPES:
            raise ValueError('Invalid field type.')
        title = form.get('title') or fid.replace('_', ' ')
        title = ' '.join([w.capitalize() for w in title.split()])
        field = {'type': type,
                 'identifier': fid,
                 'title': title,
                 'description': form.get('description') or None,
                 'required': bool(form.get('required'))
                 }
        if type in (constants.TEXT, constants.LINE):
            try:
                maxlength = int(form.get('maxlength'))
                if maxlength <= 0: raise ValueError
            except (TypeError, ValueError):
                maxlength = None
            field['maxlength'] = maxlength

        elif type == constants.INTEGER:
            try:
                minimum = int(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            try:
                maximum = int(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            if minimum is not None and maximum is not None and maximum <= minimum:
                raise ValueError('Invalid score range.')
            field['minimum'] = minimum
            field['maximum'] = maximum

        elif type == constants.FLOAT:
            try:
                minimum = float(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            try:
                maximum = float(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            if minimum is not None and maximum is not None and maximum <= minimum:
                raise ValueError('Invalid score range.')
            field['minimum'] = minimum
            field['maximum'] = maximum

        elif type == constants.SCORE:
            try:
                minimum = int(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            try:
                maximum = int(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            if minimum is None or maximum is None or maximum <= minimum:
                raise ValueError('Invalid score range.')
            field['minimum'] = minimum
            field['maximum'] = maximum
            field['slider'] = utils.to_bool(form.get('slider'))

        return field

    def edit_proposal_field(self, fid, form=dict()):
        "Edit the field for the proposal definition."
        for pos, field in enumerate(self.doc['proposal']):
            if field['identifier'] == fid:
                self.update_field(field, form=form)
                move = form.get('_move')
                if move == 'up':
                    self.doc['proposal'].pop(pos)
                    if pos == 0:
                        self.doc['proposal'].append(field)
                    else:
                        self.doc['proposal'].insert(pos-1, field)
                break
        else:
            raise KeyError('No such proposal field.')

    def update_field(self, field, form=dict()):
        "Edit the field definition from the form."
        title = form.get('title')
        if not title:
            title = ' '.join([w.capitalize() 
                              for w in field['identifier'].replace('_', ' ').split()])
        field['title'] = title
        field['description'] = form.get('description') or None
        field['required'] = bool(form.get('required'))
        if field['type'] in (constants.TEXT, constants.LINE):
            try:
                maxlength = int(form.get('maxlength'))
                if maxlength <= 0: raise ValueError
            except (TypeError, ValueError):
                maxlength = None
            field['maxlength'] = maxlength

        elif field['type'] == constants.INTEGER:
            try:
                minimum = int(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            field['minimum'] = minimum
            try:
                maximum = int(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            field['maximum'] = maximum

        elif field['type'] == constants.FLOAT:
            try:
                minimum = float(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            field['minimum'] = minimum
            try:
                maximum = float(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            field['maximum'] = maximum

        elif field['type'] == constants.SCORE:
            try:
                minimum = int(form.get('minimum'))
            except (TypeError, ValueError):
                minimum = None
            try:
                maximum = int(form.get('maximum'))
            except (TypeError, ValueError):
                maximum = None
            if minimum is None or maximum is None or maximum <= minimum:
                raise ValueError('Invalid score range.')
            field['minimum'] = minimum
            field['maximum'] = maximum
            field['slider'] = utils.to_bool(form.get('slider'))

    def delete_proposal_field(self, fid):
        "Delete the given field from proposal definition."
        for pos, field in enumerate(self.doc['proposal']):
            if field['identifier'] == fid:
                self.doc['proposal'].pop(pos)
                break
        else:
            raise ValueError('No such proposal field.')

    def add_review_field(self, form=dict()):
        "Add a field to the review definition."
        field = self.get_new_field(form=form)
        if field['identifier'] in [f['identifier'] for f in self.doc['review']]:
            raise ValueError('Field identifier is already in use.')
        self.doc['review'].append(field)

    def edit_review_field(self, fid, form=dict()):
        "Edit the review definition field."
        for pos, field in enumerate(self.doc['review']):
            if field['identifier'] == fid:
                self.update_field(field, form=form)
                move = form.get('_move')
                if move == 'up':
                    self.doc['review'].pop(pos)
                    if pos == 0:
                        self.doc['review'].append(field)
                    else:
                        self.doc['review'].insert(pos-1, field)
                break
        else:
            raise KeyError('No such review field.')

    def delete_review_field(self, fid):
        "Delete the field from the review definition."
        for pos, field in enumerate(self.doc['review']):
            if field['identifier'] == fid:
                self.doc['review'].pop(pos)
                break
        else:
            raise ValueError('No such review field.')

    def add_document(self, infile, description):
        "Add a document to the call."
        self.add_attachment(infile.filename,
                            infile.read(),
                            infile.mimetype)
        for document in self.doc['documents']:
            if document['name'] == infile.filename:
                document['description'] = description
                break
        else:
            self.doc['documents'].append({'name': infile.filename,
                                          'description': description})

    def delete_document(self, documentname):
        "Delete the named document from the call."
        for pos, document in enumerate(self.doc['documents']):
            if document['name'] == documentname:
                self.delete_attachment(documentname)
                self.doc['documents'].pop(pos)
                break

    def edit_access(self, form=dict()):
        "Edit the access flags."
        self.doc['access'] = {}
        for flag in constants.ACCESS:
            self.doc['access'][flag] = utils.to_bool(form.get(flag))


def get_call(cid, cache=True):
    "Return the call with the given identifier."
    result = [r.doc for r in flask.g.db.view('calls', 'identifier',
                                             key=cid,
                                             include_docs=True)]
    if len(result) == 1:
        if cache:
            return set_cache(result[0])
        else:
            return result[0]
    else:
        return None

def allow_view(call):
    """Admin may view all calls.
    Others may view a call if it has an opens date.
    """
    if flask.g.am_admin: return True
    return bool(call['opens'])

def allow_edit(call):
    "Allow only admin to edit a call."
    return flask.g.am_admin

def allow_delete(call):
    "Allow admin to delete a call if it has no proposals."
    if not flask.g.am_admin: return False
    return utils.get_count('proposals', 'call', call['identifier']) == 0

def allow_proposal(call):
    "Any logged-in user except designated reviewer may create a proposal. "
    if not flask.g.current_user: return False
    return not am_reviewer(call)

def allow_view_reviews(call):
    """Admin may view all reviews.
    Review chairs may view all reviews.
    Other reviewers may view depending on the access flag for the call.
    """
    if not flask.g.current_user: return False
    if flask.g.am_admin: return True
    if am_reviewer(call):
        if am_chair(call): return True
        return bool(call['access'].get('allow_reviewer_view_all_reviews'))
    return False

def am_reviewer(call):
    "Is the current user a reviewer for proposals in the call?"
    if not flask.g.current_user: return False
    return flask.g.current_user['username'] in call['reviewers']

def am_chair(call):
    "Is the current user a chair for proposals in the call?"
    if not flask.g.current_user: return False
    return flask.g.current_user['username'] in call['chairs']

def set_cache(call):
    """Set the cached, non-saved values for the call.
    This does NOT de-reference any other entities.
    """
    call['cache'] = cache = {}
    # Not all users may actually view this, but for simplicity...
    if flask.g.current_user:
        cache['all_proposals_count'] = utils.get_count('proposals', 'call',
                                                       call['identifier'])
        cache['all_reviews_count'] = utils.get_count('reviews', 'call',
                                                     call['identifier'])
        cache['my_reviews_count'] = utils.get_count(
            'reviews', 'call_reviewer', 
            [call['identifier'], flask.g.current_user['username']])
    # Set the current state of the call, computed from open/close and today.
    if call['opens']:
        if call['opens'] > utils.normalized_local_now():
            cache['is_open'] = False
            cache['is_closed'] = False
            cache['is_published'] = False
            cache['text'] = 'Not yet open.'
            cache['color'] = 'secondary'
        elif call['closes']:
            remaining = utils.days_remaining(call['closes'])
            if remaining > 7:
                cache['is_open'] = True
                cache['is_closed'] = False
                cache['is_published'] = True
                cache['text'] = f"{remaining:.0f} days remaining."
                cache['color'] = 'success'
            elif remaining >= 2:
                cache['is_open'] = True
                cache['is_closed'] = False
                cache['is_published'] = True
                cache['text'] = f"{remaining:.0f} days remaining."
                cache['color'] = 'warning'
            elif remaining >= 0:
                cache['is_open'] = True
                cache['is_closed'] = False
                cache['is_published'] = True
                cache['text'] = f"{remaining:.1f} days remaining."
                cache['color'] = 'danger'
            else:
                cache['is_open'] = False
                cache['is_closed'] = True
                cache['is_published'] = True
                cache['text'] = 'Closed.'
                cache['color'] = 'dark'
        else:
            cache['is_open'] = True
            cache['is_closed'] = False
            cache['is_published'] = True
            cache['text'] = 'Open with no closing date.'
            cache['color'] = 'success'
    else:
        if call['closes']:
            cache['is_open'] = False
            cache['is_closed'] = False
            cache['is_published'] = False
            cache['text'] = 'No open date set.'
            cache['color'] = 'secondary'
        else:
            cache['is_open'] = False
            cache['is_closed'] = False
            cache['is_published'] = False
            cache['text'] = 'No open or close dates set.'
            cache['color'] = 'secondary'
    return call
