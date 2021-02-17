"Grants dossier lists."

import io
import zipfile

import flask
import xlsxwriter

import anubis.call
import anubis.user
import anubis.proposal
import anubis.grant
from anubis import constants
from anubis import utils

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
    # Convert username for grant to full user dict.
    for grant in grants:
        grant['user'] = anubis.user.get_user(grant['user'])
    # There may be accounts that have no emails.
    receiver_emails = [g['user']['email'] for g in grants]
    receiver_emails = [e for e in receiver_emails if e]
    access_emails = []
    for grant in grants:
        access_emails.extend([anubis.user.get_user(a)['email']
                              for a in grant.get('access_view', [])])
    access_emails = [e for e in access_emails if e]
    all_emails = receiver_emails + access_emails
    email_lists = {'Grant receivers (= proposal submitters)':
                   ', '.join(receiver_emails),
                   'Persons with access to a grant': ', '.join(access_emails),
                   'All involved persons': ', '.join(all_emails)}
    return flask.render_template('grants/call.html',
                                 call=call,
                                 grants=grants,
                                 email_lists=email_lists)

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
    grants.sort(key=lambda g: g['identifier'])
    content = get_call_grants_xlsx(call, grants)
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_grants.xlsx")
    return response

def get_call_grants_xlsx(call, grants):
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
    ws.freeze_panes(2, 1)
    ws.set_row(0, 60, head_text_format)
    ws.set_row(1, 60, head_text_format)
    ws.set_column(0, 2, 10, normal_text_format)
    ws.set_column(3, 3, 40, normal_text_format)
    ws.set_column(4, 6, 20, normal_text_format)

    nrow = 0
    row = ['Grant', 'Status', 'Proposal', 'Proposal title', 
           'Submitter', 'Email', 'Affiliation']
    ws.write_row(nrow, 0, row)

    # Repeated fields are those fields to be repeated N number
    # of times as given in a repeat field. Notice the difference!
    # Repeated fields are in a certain sense dependent on their repeat field.

    # First all non-repeated fields, including any repeat fields.
    pos = len(row) - 1
    start_pos = pos
    for field in call['grant']:
        if field.get('repeat'): continue
        title = field['title'] or field['identifier'].capitalize()
        pos += 1
        n_repeat = len([f for f in call['grant'] 
                        if f.get('repeat') == field['identifier']])
        if n_repeat:
            ws.merge_range(0, pos, 0, pos+n_repeat-1, title)
            pos += n_repeat - 1
        else:
            ws.write_row(nrow, pos, [title])
    nrow += 1

    # Then repeated fields; their titles beneath the repeat field.
    pos = start_pos
    for field in call['grant']:
        if field.get('repeat'): continue
        pos += 1
        repeat = [f['title'] or f['identifier'].capitalize()
                  for f in call['grant'] 
                  if f.get('repeat') == field['identifier']]
        n_repeat = len(repeat)
        if n_repeat:
            ws.write_row(nrow, pos, repeat)
            pos += n_repeat - 1
    nrow += 1

    for grant in grants:
        # Find the maximum number of rows to merge for this grant.
        n_merge = 1
        for field in call['grant']:
            if field['type'] != constants.REPEAT: continue
            try:
                n_merge = max(n_merge, grant['values'][field['identifier']])
            except KeyError:
                pass

        ncol = 0
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_url(nrow, ncol,
                     flask.url_for('grant.display',
                                   gid=grant['identifier'],
                                   _external=True),
                     string=grant['identifier'])
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_string(nrow, ncol,
                        grant['errors'] and 'Incomplete' or 'Complete')
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_url(nrow, ncol,
                     flask.url_for('proposal.display',
                                   pid=grant['proposal'],
                                   _external=True),
                     string=grant['proposal'])
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        proposal = anubis.proposal.get_proposal(grant['proposal'])
        ws.write_string(nrow, ncol, proposal['title'])
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        user = anubis.user.get_user(username=proposal['user'])
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_string(
            nrow, ncol,
            f"{user.get('familyname') or '-'}, {user.get('givenname') or '-'}")
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_string(nrow, ncol, user.get('email') or '')
        ncol += 1
        if n_merge > 1:
            ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
        ws.write_string(nrow, ncol, user.get('affiliation') or '')
        ncol += 1

        for field in call['grant']:
            if field.get('repeat'): continue
            if field['type'] == constants.REPEAT:
                n_repeat = grant['values'][field['identifier']]
                col_offset = 0
                for repeated in call['grant']:
                    if repeated.get('repeat') != field['identifier']:
                        continue
                    for row_offset in range(n_repeat):
                        fid = f"{repeated['identifier']}-{row_offset+1}"
                        write_cell(ws,
                                   nrow + row_offset,
                                   ncol + col_offset,
                                   grant['values'].get(fid),
                                   repeated['type'],
                                   grant['identifier'],
                                   fid)
                    col_offset += 1
            else:
                if n_merge > 1:
                    ws.merge_range(nrow, ncol, nrow+n_merge-1, ncol, '')
                write_cell(ws,
                           nrow,
                           ncol,
                           grant['values'].get(field['identifier']),
                           field['type'],
                           grant['identifier'],
                           field['identifier'])
            ncol += 1

        nrow += n_merge

    wb.close()
    return output.getvalue()

def write_cell(ws, nrow, ncol, value, field_type, gid, fid):
    if value is None:
        ws.write_string(nrow, ncol, '')
    elif field_type == constants.TEXT:
        ws.write_string(nrow, ncol, value)
    elif field_type == constants.DOCUMENT:
        ws.write_url(nrow, ncol,
                     flask.url_for('grant.document',
                                   gid=gid,
                                   fid=fid,
                                   _external=True),
                     string='Download')
    else:
        ws.write(nrow, ncol, value)

@blueprint.route('/call/<cid>.zip')
@utils.login_required
def call_zip(cid):
    """Return a zip file containing the XLSX file of all grants for a call
    and all documents in all grant dossiers.
    """
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    if not anubis.call.allow_view_grants(call):
        return utils.error('You may not view the grants of the call.',
                           flask.url_for('call.display',cid=call['identifier']))
    # Colon ':' is a problematic character in filenames; replace by dash '_'
    cid = cid.replace(':', '-')
    grants = utils.get_docs_view('grants', 'call', call['identifier'])
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as outfile:
        outfile.writestr(f"{cid}_grants.xlsx",
                         get_call_grants_xlsx(call, grants))
        for grant in grants:
            for document in anubis.grant.get_grant_documents(grant):
                outfile.writestr(document['filename'], document['content'])
    response = flask.make_response(output.getvalue())
    response.headers.set('Content-Type', constants.ZIP_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_grants.zip")
    return response

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all grants for a user, including the grants the user has access to."
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not anubis.user.allow_view(user):
        return utils.error("You may not view the user's grants.",
                           flask.url_for('home'))
    grants = utils.get_docs_view('grants', 'user', user['username'])
    grants.extend(utils.get_docs_view('grants', 'access', user['username']))
    return flask.render_template('grants/user.html', user=user, grants=grants)
