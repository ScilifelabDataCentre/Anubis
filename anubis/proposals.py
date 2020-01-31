"Lists of proposals."

import tempfile

import flask
import openpyxl
import openpyxl.styles

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
    allow_view_decisions = anubis.call.allow_view_decisions(call)
    bannerfields = [f for f in call['decision'] if f.get('banner')]
    return flask.render_template('proposals/call.html', 
                                 call=call,
                                 proposals=proposals,
                                 allow_view_reviews=allow_view_reviews,
                                 allow_view_decisions=allow_view_decisions,
                                 bannerfields=bannerfields)

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all proposals in a call."
    from openpyxl.utils.cell import get_column_letter
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
    ws.column_dimensions[get_column_letter(2)].width = 30
    for field in call['proposal']:
        row.append(field['identifier'])
        if field['type'] == constants.LINE:
            ws.column_dimensions[get_column_letter(len(row))].width = 40
        elif field['type'] == constants.TEXT:
            ws.column_dimensions[get_column_letter(len(row))].width = 50
        elif field['type'] == constants.DOCUMENT:
            ws.column_dimensions[get_column_letter(len(row))].width = 50
    ws.append(row)
    row_number = 1
    wrap_alignment = openpyxl.styles.Alignment(wrapText=True)
    for proposal in proposals:
        row_number += 1
        row = [proposal['identifier'], 
               proposal.get('title') or '',
               proposal['user']]
        wraptext = []
        hyperlink = []
        for field in call['proposal']:
            value = proposal['values'].get(field['identifier'])
            if value is None:
                row.append('')
            elif field['type'] == constants.TEXT:
                row.append(value)
                col = get_column_letter(len(row))
                wraptext.append(f"{col}{row_number}")
            elif field['type'] == constants.DOCUMENT:
                row.append(flask.url_for('review.document',
                                         iuid=review['_id'],
                                         document=value,
                                         _external=True))
                col = get_column_letter(len(row))
                hyperlink.append(f"{col}{row_number}")
            else:
                row.append(value)
        ws.append(row)
        if wraptext:
            ws.row_dimensions[row_number].height = 40
        while wraptext:
            ws[wraptext.pop()].alignment = wrap_alignment
        while hyperlink:
            colrow = hyperlink.pop()
            ws[colrow].hyperlink = ws[colrow].value
            ws[colrow].style = 'Hyperlink'
        colrow = f"A{row_number}"
        ws[colrow].hyperlink = flask.url_for('proposal.display',
                                             pid=ws[colrow].value,
                                             _external=True)
        ws[colrow].style = 'Hyperlink'
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
    if not anubis.user.allow_view(user):
        utils.flash_error("You may not view the user's proposals.")
        return flask.redirect(flask.url_for('home'))
    proposals = get_user_proposals(user['username'])
    for proposal in proposals:
        decision = proposal['cache'].get('decision')
        if decision:
            anubis.decision.set_cache(decision, call=proposal['cache']['call'])
            decision['cache']['allow_view'] = anubis.decision.allow_view(decision)
    return flask.render_template('proposals/user.html',  
                                 user=user,
                                 proposals=proposals)

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
