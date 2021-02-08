"Grants dossier lists."

import io

import flask
import xlsxwriter

import anubis.call
import anubis.user
import anubis.proposal
import anubis.grant

from . import constants
from . import utils

blueprint = flask.Blueprint('grants', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all grants for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    if not anubis.call.allow_view_grants(call):
        return utils.error('You may not view the grants of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    grants = utils.get_docs_view('grants', 'call', call['identifier'])
    return flask.render_template('grants/call.html',
                                 call=call,
                                 grants=grants)

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all grants for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    if not anubis.call.allow_view_grants(call):
        return utils.error('You may not view the grants of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    grants = utils.get_docs_view('grants', 'call', call['identifier'])
    content = get_grants_xlsx(call, grants)
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_grants.xlsx")
    return response

def get_grants_xlsx(call, grants):
    "Return the content for the XLSX file for the list of grants."
    output = io.BytesIO()
    wb = xlsxwriter.Workbook(output, {'in_memory': True})
    head_text_format = wb.add_format({'bold': True,
                                      'text_wrap': True,
                                      'bg_color': '#9ECA7F',
                                      'font_size': 15,
                                      'align': 'center',
                                      'border': 1})
    normal_text_format = wb.add_format({'font_size': 14,
                                        'align': 'left',
                                        'valign': 'vcenter'})
    ws = wb.add_worksheet(f"Grants in call {call['identifier']}")
    ws.freeze_panes(1, 1)
    ws.set_row(0, 60, head_text_format)
    ws.set_column(1, 1, 40, normal_text_format)
    if call.get('categories'):
        ws.set_column(2, 2, 10, normal_text_format)
        ws.set_column(3, 3, 20, normal_text_format)
        ws.set_column(4, 4, 40, normal_text_format)
    else:
        ws.set_column(2, 2, 20, normal_text_format)
        ws.set_column(3, 3, 40, normal_text_format)

    nrow = 0
    row = ['Grant']
    for field in call['grant']:
        row.append(field['title'] or field['identifier'].capitalize())
    row.extend(['Proposal', 'Proposal title', 
                'Submitter', 'Email', 'Affiliation'])
    ws.write_row(nrow, 0, row)
    nrow += 1

    for grant in grants:
        ncol = 0
        ws.write_url(nrow, ncol,
                     flask.url_for('grant.display',
                                   gid=grant['identifier'],
                                   _external=True),
                     string=grant['identifier'])
        ncol += 1
        for field in call['grant']:
            value = grant['values'].get(field['identifier'])
            if value is None:
                ws.write_string(nrow, ncol, '')
            elif field['type'] == constants.TEXT:
                ws.write_string(nrow, ncol, value)
            elif field['type'] == constants.DOCUMENT:
                ws.write_url(nrow, ncol,
                             flask.url_for('grant.document',
                                           gid=grant['identifier'],
                                           fid=field['identifier'],
                                           _external=True),
                             string='Download')
            else:
                ws.write(nrow, ncol, value)
            ncol += 1

        proposal = anubis.proposal.get_proposal(grant['proposal'])
        ws.write_url(nrow, ncol,
                     flask.url_for('proposal.display',
                                   pid=proposal['identifier'],
                                   _external=True),
                     string=proposal['identifier'])
        ncol += 1
        ws.write_string(nrow, ncol, proposal.get('title') or '')
        ncol += 1
        user = anubis.user.get_user(grant['user'])
        ws.write_string(
            nrow, ncol,
            f"{user.get('familyname') or '-'}, {user.get('givenname') or '-'}")
        ncol += 1
        ws.write_string(nrow, ncol, user.get('email') or '')
        ncol += 1
        ws.write_string(nrow, ncol, user.get('affiliation') or '')
        ncol += 1

        nrow += 1

    wb.close()
    return output.getvalue()
