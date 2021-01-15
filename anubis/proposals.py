"Lists of proposals."

import io
import statistics

import flask
import xlsxwriter

import anubis.call
import anubis.decision
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
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    category = flask.request.args.get('category')
    proposals = get_call_proposals(call, category)
    mean_field_ids = compute_mean_fields(call, proposals)
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    allow_view_decisions = anubis.call.allow_view_decisions(call)
    allow_view_details = anubis.call.allow_view_details(call)
    return flask.render_template('proposals/call.html', 
                                 call=call,
                                 proposals=proposals,
                                 mean_field_ids=mean_field_ids,
                                 allow_view_reviews=allow_view_reviews,
                                 allow_view_decisions=allow_view_decisions,
                                 allow_view_details=allow_view_details,
                                 category=category)

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all proposals in a call."
    call = anubis.call.get_call(cid)
    if not call:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    response = flask.make_response(get_call_xlsx(call))
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{call['identifier']}_proposals.xlsx")
    return response

def get_call_xlsx(call):
    "Return the content of an XLSX file for all proposals in a call."
    proposals = get_call_proposals(call, flask.request.args.get('category'))
    mean_field_ids = compute_mean_fields(call, proposals)
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
    ws = wb.add_worksheet(f"Proposals in call {call['identifier']}")
    ws.freeze_panes(1, 1)
    ws.set_row(0, 60, head_text_format)
    ws.set_column(1, 1, 40, normal_text_format)
    if call.get('categories'):
        ws.set_column(2, 3, 10, normal_text_format)
        ws.set_column(4, 5, 20, normal_text_format)
    else:
        ws.set_column(2, 2, 10, normal_text_format)
        ws.set_column(3, 4, 20, normal_text_format)

    nrow = 0
    row = ['Proposal', 'Proposal title']
    if call.get('categories'):
        row.append('Category')
    row.extend(['Submitted', 'Submitter', 'Affiliation'])
    ncol = len(row)
    for field in call['proposal']:
        row.append(field['title'] or field['identifier'].capitalize())
        if field['type'] == constants.LINE:
            ws.set_column(ncol, ncol, 40, normal_text_format)
        elif field['type'] == constants.TEXT:
            ws.set_column(ncol, ncol, 60, normal_text_format)
        ncol += 1
    allow_view_reviews = anubis.call.allow_view_reviews(call)
    if allow_view_reviews:
        for id in mean_field_ids:
            for field in call['review']:
                if field['identifier'] == id:
                    title = field['title'] or field['identifier'].capitalize()
                    break
            row.append(f"Reviews {title} mean")
            row.append(f"Reviews {title} stdev")
    allow_view_decisions = anubis.call.allow_view_decisions(call)
    if allow_view_decisions:
        for field in call['decision']:
            if not field.get('banner'): continue
            title = field['title'] or field['identifier'].capitalize()
            row.append(f"Decision {title}")
    ws.write_row(nrow, 0, row)
    nrow += 1

    for proposal in proposals:
        ncol = 0
        ws.write_url(nrow, ncol,
                     flask.url_for('proposal.display',
                                   pid=proposal['identifier'],
                                   _external=True),
                     string=proposal['identifier'])
        ncol += 1
        ws.write_string(nrow, ncol, proposal.get('title') or '')
        ncol += 1
        if call.get('categories'):
            ws.write_string(nrow, ncol, proposal.get('category') or '')
            ncol += 1
        ws.write_string(nrow, ncol, proposal.get('submitted') and 'yes' or 'no')
        ncol += 1
        user = anubis.user.get_user(username=proposal['user'])
        ws.write_string(
            nrow, ncol,
            f"{user.get('familyname') or '-'}, {user.get('givenname') or '-'}")
        ncol += 1
        ws.write_string(nrow, ncol, user.get('affiliation') or '')
        ncol += 1

        for field in call['proposal']:
            value = proposal['values'].get(field['identifier'])
            if value is None:
                ws.write_string(nrow, ncol, '')
            elif field['type'] == constants.TEXT:
                ws.write_string(nrow, ncol, value)
            elif field['type'] == constants.DOCUMENT:
                ws.write_url(nrow, ncol,
                             flask.url_for('proposal.document',
                                           pid=proposal['identifier'],
                                           fid=field['identifier'],
                                           _external=True),
                             string='Download')
            else:
                if isinstance(value, list):
                    ws.write(nrow, ncol, 'LIST')
                else:
                    ws.write(nrow, ncol, value)
            ncol += 1

        if allow_view_reviews:
            for id in mean_field_ids:
                value = proposal['scores'][id]['mean']
                if value is None:
                    ws.write_string(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal['scores'][id]['stdev']
                if value is None:
                    ws.write_string(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1

        if allow_view_decisions:
            decision = anubis.decision.get_decision(proposal.get('decision')) or {}
            for field in call['decision']:
                if not field.get('banner'): continue
                if decision.get('finalized'):
                    value = decision['values'].get(field['identifier'])
                    ws.write(nrow, ncol, value)
                else:
                    ws.write_string(nrow, ncol, '')
                ncol += 1

        nrow += 1

    wb.close()
    return output.getvalue()

@blueprint.route('/user/<username>')
@utils.login_required
def user(username):
    "List all proposals for a user."
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not anubis.user.allow_view(user):
        return utils.error("You may not view the user's proposals.",
                           flask.url_for('home'))
    return flask.render_template('proposals/user.html',  
                                 user=user,
                                 proposals=get_user_proposals(user['username']),
                                 allow_view_decision=anubis.decision.allow_view)

def get_call_proposals(call, category=None):
    """Get the proposals in the call.
    Only include those allowed to view.
    Optionally only those with the given category.
    """
    result = [i.doc for i in flask.g.db.view('proposals', 'call',
                                             key=call['identifier'],
                                             reduce=False,
                                             include_docs=True)]
    result = [p for p in result if anubis.proposal.allow_view(p)]
    if category:
        result = [p for p in result if p.get('category') == category]
    return result

def get_user_proposals(username, call=None):
    "Get all proposals created by the user."
    return [i.doc for i in flask.g.db.view('proposals', 'user',
                                           key=username,
                                           reduce=False,
                                           include_docs=True)]

def compute_mean_fields(call, proposals):
    """Compute the mean and stdev of numerical banner fields
    for each proposal. 
    Return the identifiers of the fields.
    """
    field_ids = [f['identifier'] for f in call['review'] 
                 if f.get('banner') and
                 f['type'] in constants.NUMERICAL_FIELD_TYPES]
    for proposal in proposals:
        reviews = utils.get_docs_view('reviews', 'proposal', 
                                      proposal['identifier'])
        scores = dict([(id, list()) for id in field_ids])
        for review in reviews:
            for id in field_ids:
                value = review['values'].get(id)
                if value is not None: scores[id].append(float(value))
        proposal['scores'] = dict()
        for id in field_ids:
            proposal['scores'][id] = d = dict()
            try:
                d['mean'] = statistics.mean(scores[id])
            except statistics.StatisticsError:
                d['mean'] = None
            try:
                d['stdev'] = statistics.stdev(scores[id])
            except statistics.StatisticsError:
                d['stdev'] = None
    return field_ids
