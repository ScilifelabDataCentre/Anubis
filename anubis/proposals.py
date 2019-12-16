"Lists of proposals."

import tempfile

import flask
import openpyxl

import anubis.call
import anubis.proposal
import anubis.user

from . import constants
from . import utils


blueprint = flask.Blueprint('proposals', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all proposals in a call."
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view(call):
        utils.flash_error("You may not view the call.")
        return flask.redirect(flask.url_for('home'))
    proposals = get_call_proposals(call)
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    return flask.render_template('proposals/call.html', 
                                 call=call,
                                 proposals=proposals,
                                 allow_view_reviews=allow_view_reviews)

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Return an XLSX file of all proposals in a call."
    call = anubis.call.get_call(cid)
    if not call:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view(call):
        utils.flash_error("You may not view the call.")
        return flask.redirect(flask.url_for('home'))
    proposals = get_call_proposals(call)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Proposals in call {cid}"
    row = ['Proposal', 'Proposal title', 'Submitter']
    row.extend([f['identifier'] for f in call['proposal']])
    ws.append(row)
    for proposal in proposals:
        row = [proposal['identifier'], 
               proposal.get('title') or '',
               proposal['user']]
        for field in call['proposal']:
            value = proposal['values'].get(field['identifier'])
            if value is None:
                row.append('')
            else:
                row.append(value)
        ws.append(row)
    with tempfile.NamedTemporaryFile(suffix='.xlsx') as tmp:
        wb.save(tmp.name)
        tmp.seek(0)
        content = tmp.read()
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_proposals.xlsx")
    return response

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all proposals for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.user.am_admin_or_self(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    return flask.render_template(
        'proposals/user.html', 
        user=user,
        proposals=get_user_proposals(user['username']))

def get_call_proposals(call):
    "Get the proposals in the call. Only include those allowed to view."
    result = [anubis.proposal.set_cache(r.doc, call=call)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    return [p for p in result if anubis.proposal.allow_view(p)]

def get_user_proposals(username, call=None):
    """Get all proposals created by the user.
    Cache not set. Excludes no proposals.
    """
    return [anubis.proposal.set_cache(r.doc, call=call)
            for r in flask.g.db.view('proposals', 'user',
                                     key=username,
                                     reduce=False,
                                     include_docs=True)]

def get_call_user_proposal(call, username):
    """Get the proposal created by the user in the call.
    Cache not set. Excludes no proposals.
    """
    proposals = [p for p in get_user_proposals(username, call=call)
                 if p['call'] == call['identifier']]
    if proposals:
        return proposals[0]
    else:
        return None
