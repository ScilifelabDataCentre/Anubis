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
        review_score_field_ids=get_review_score_field_ids(call, proposals),
        review_rank_field_ids=get_review_rank_field_ids(call, proposals),
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

def get_call_xlsx(call, submitted=False, proposals=None):
    """Return the content of an XLSX file for all proposals in a call.
    Optionally only the submitted ones.
    Optionally for the given list proposals.
    """
    if proposals is None:
        title = f"Proposals in call {call['identifier']}"
        proposals = get_call_proposals(
            call,
            category=flask.request.args.get('category'),
            submitted=submitted)
    else:
        title = f"Selected proposals in call {call['identifier']}"
    score_field_ids = get_review_score_field_ids(call, proposals)
    rank_field_ids = get_review_rank_field_ids(call, proposals)
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
    ws = wb.add_worksheet(title)
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
        for id in rank_field_ids:
            row.append(f"Reviews {id}: ranking factor")
            row.append(f"Reviews {id}: stdev")
        if len(score_field_ids) >= 2:
            row.append("Reviews all scores: mean of means")
            row.append("Reviews all scores: stdev of means")
        for id in score_field_ids:
            for field in call['review']:
                if field['identifier'] == id:
                    title = field['title'] or field['identifier'].capitalize()
                    break
            row.append(f"Reviews {title}: N")
            row.append(f"Reviews {title}: mean")
            row.append(f"Reviews {title}: stdev")
    allow_view_decisions = anubis.call.allow_view_decisions(call)
    if allow_view_decisions:
        row.append('Decision')
        row.append('Decision status')
        for field in call['decision']:
            if not field.get('banner'): continue
            title = field['title'] or field['identifier'].capitalize()
            row.append(title)
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
        ws.write_string(nrow, ncol, utils.get_fullname(user))
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
            for id in rank_field_ids:
                value = proposal['ranking'][id]['factor']
                if value is None:
                    ws.write_number(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal['ranking'][id]['stdev']
                if value is None:
                    ws.write_number(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
            if len(score_field_ids) >= 2:
                value = proposal['scores']['__mean__']
                if value is None:
                    ws.write_string(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
                value = proposal['scores']['__stdev__']
                if value is None:
                    ws.write_string(nrow, ncol, '')
                else:
                    ws.write_number(nrow, ncol, value)
                ncol += 1
            for id in score_field_ids:
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
            if decision:
                verdict = decision.get('verdict')
                if verdict:
                    ws.write(nrow, ncol, 'Accepted')
                elif verdict is None:
                    ws.write(nrow, ncol, 'Undecided')
                else:
                    ws.write(nrow, ncol, 'Declined')
            else:
                ws.write(nrow, ncol, '-')
            ncol += 1
            if decision.get('finalized'):
                ws.write(nrow, ncol, 'Finalized')
            else:
                ws.write(nrow, ncol, '-')
            ncol += 1
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

def get_review_score_field_ids(call, proposals):
    """Return a list of identifiers for the score banner fields in the reviews.
    Compute the score means and stdevs. If there are more than two score
    fields, then also compute the mean of the means and the stdev of the means.
    This is done over all finalized reviews for each proposal.
    Store the values in the proposal document.
    """
    field_ids = [f['identifier'] for f in call['review'] 
                 if f.get('banner') and f['type'] == constants.SCORE]
    for proposal in proposals:
        reviews = utils.get_docs_view('reviews', 'proposal', 
                                      proposal['identifier'])
        # Only include finalized reviews in the calculation.
        reviews = [r for r in reviews if r.get('finalized')]
        scores = dict([(field_id, list()) for field_id in field_ids])
        for review in reviews:
            for field_id in field_ids:
                value = review['values'].get(field_id)
                if value is not None: scores[field_id].append(float(value))
        proposal['scores'] = dict()
        for field_id in field_ids:
            proposal['scores'][field_id] = d = dict()
            d['n'] = len(scores[field_id])
            try:
                d['mean'] = round(statistics.mean(scores[field_id]), 1)
            except statistics.StatisticsError:
                d['mean'] = None
            try:
                d['stdev'] = round(statistics.stdev(scores[field_id]), 1)
            except statistics.StatisticsError:
                d['stdev'] = None
        if len(field_ids) >= 2:
            mean_scores = [d['mean'] for d in proposal['scores'].values()
                           if d['mean'] is not None]
            try:
                mean_means = round(statistics.mean(mean_scores), 1)
            except statistics.StatisticsError:
                mean_means = None
            proposal['scores']['__mean__'] = mean_means
            try:
                stdev_means = round(statistics.stdev(mean_scores), 1)
            except statistics.StatisticsError:
                stdev_means = None
            proposal['scores']['__mean__'] = mean_means
            proposal['scores']['__stdev__'] = stdev_means
    return field_ids

def get_review_rank_field_ids(call, proposals):
    """Return a list of identifiers for the rank banner fields in the reviews.
    Compute the ranking factors of each proposal from all finalized reviews.
    """
    field_ids = [f['identifier'] for f in call['review']
                 if f.get('banner') and f['type'] == constants.RANK]
    for field_id in field_ids:
        ranks = dict()          # key: reviewer, value: dict(proposal: rank)
        for proposal in proposals:
            reviews = utils.get_docs_view('reviews', 'proposal', 
                                          proposal['identifier'])
            # Only include finalized reviews in the calculation.
            reviews = [r for r in reviews if r.get('finalized')]
            for review in reviews:
                try:
                    value = review['values'][field_id]
                    if value is None: raise KeyError
                except KeyError:
                    pass
                else:
                    d = ranks.setdefault(review['reviewer'], dict())
                    d[proposal['identifier']] = value
        ranking_factors = dict()
        for proposal in proposals:
            factors = []
            for reviewer, values in ranks.items():
                try:
                    value = ranks[reviewer][proposal['identifier']]
                except KeyError:
                    pass
                else:
                    factors.append(float(len(values) - value + 1) / len(values))
            rf = proposal.setdefault('ranking', dict())
            rf[field_id] = dict()
            try:
                rf[field_id]['factor'] = round(10.0*statistics.mean(factors), 1)
            except statistics.StatisticsError:
                rf[field_id]['factor'] = None
            try:
                rf[field_id]['stdev'] = round(10.0*statistics.stdev(factors), 1)
            except statistics.StatisticsError:
                rf[field_id]['stdev'] = None
    return field_ids
