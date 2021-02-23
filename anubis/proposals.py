"Lists of proposals."

import io
import statistics

import flask
import xlsxwriter

import anubis.call
import anubis.decision
import anubis.proposal
import anubis.user
from anubis import constants
from anubis import utils


blueprint = flask.Blueprint('proposals', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all proposals in a call. Optionally by category."
    call = anubis.call.get_call(cid)
    if not call:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    category = flask.request.args.get('category')
    proposals = get_call_proposals(call, category)
    all_emails = []
    submitted_emails = []
    for proposal in proposals:
        user = anubis.user.get_user(username=proposal['user'])
        if not user: continue
        all_emails.append(user['email'])
        if proposal.get('submitted'):
            submitted_emails.append(user['email'])
    # There may be accounts that have no email!
    all_emails = sorted(set([e for e in all_emails if e]))
    submitted_emails = sorted(set([e for e in submitted_emails if e]))
    email_lists = {'Emails to for submitted proposals': 
                   ', '.join(submitted_emails),
                   'Emails for all proposals': ', '.join(all_emails)}
    return flask.render_template(
        'proposals/call.html', 
        call=call,
        proposals=proposals,
        email_lists=email_lists,
        mean_field_ids=compute_mean_fields(call, proposals),
        am_reviewer=anubis.call.am_reviewer(call),
        allow_view_reviews=anubis.call.allow_view_reviews(call),
        allow_view_decisions=anubis.call.allow_view_decisions(call),
        allow_view_details=anubis.call.allow_view_details(call),
        category=category,
        get_reviewer_review=anubis.review.get_reviewer_review)

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

def get_call_xlsx(call, submitted=False):
    """Return the content of an XLSX file for all proposals in a call.
    Optionally only the submitted ones.
    """
    proposals = get_call_proposals(call,
                                   category=flask.request.args.get('category'),
                                   submitted=submitted)
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
    row.extend(['Submitted', 'Submitter', 'Email', 'Affiliation'])
    ncol = len(row)
    for field in call['proposal']:
        row.append(field['title'] or field['identifier'].capitalize())
        if field['type'] in (constants.LINE, constants.EMAIL):
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
            row.append(f"Reviews {title} N")
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
        ws.write_string(nrow, ncol, user.get('email') or '')
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
            elif field['type'] == constants.SELECT:
                if isinstance(value, list): # Multiselect
                    ws.write(nrow, ncol, '\n'.join(value))
                else:
                    ws.write(nrow, ncol, value)
            else:
                ws.write(nrow, ncol, value)
            ncol += 1

        if allow_view_reviews:
            for id in mean_field_ids:
                ws.write_number(nrow, ncol, proposal['scores'][id]['n'])
                ncol += 1
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
    proposals = get_user_proposals(user['username'])
    proposals.extend(utils.get_docs_view('proposals', 'access', user['username']))
    return flask.render_template('proposals/user.html',  
                                 user=user,
                                 proposals=proposals,
                                 allow_view_decision=anubis.decision.allow_view)

def get_call_proposals(call, category=None, submitted=False):
    """Get the proposals in the call.
    Only include those allowed to view.
    Optionally only those with the given category.
    Optionally only the submitted ones.
    """
    result = [i.doc for i in flask.g.db.view('proposals', 'call',
                                             key=call['identifier'],
                                             reduce=False,
                                             include_docs=True)]
    result = [p for p in result if anubis.proposal.allow_view(p)]
    if category:
        result = [p for p in result if p.get('category') == category]
    if submitted:
        result = [p for p in result if p.get('submitted')]
    result.sort(key=lambda p: p['identifier'])
    for proposal in result:
        flask.g.cache[f"proposal {proposal['identifier']}"] = proposal
    return result

def get_user_proposals(username):
    "Get all proposals created by the user."
    result = [i.doc for i in flask.g.db.view('proposals', 'user',
                                             key=username,
                                             reduce=False,
                                             include_docs=True)]
    result.sort(key=lambda p: p['identifier'])
    for proposal in result:
        flask.g.cache[f"proposal {proposal['identifier']}"] = proposal
    return result

def compute_mean_fields(call, proposals):
    """Compute the mean and stdev of numerical banner fields
    for each proposal. Store values in the proposal document.
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
            d['n'] = len(scores[id])
            try:
                d['mean'] = round(statistics.mean(scores[id]), 2)
            except statistics.StatisticsError:
                d['mean'] = None
            try:
                d['stdev'] = round(statistics.stdev(scores[id]), 2)
            except statistics.StatisticsError:
                d['stdev'] = None
    return field_ids
