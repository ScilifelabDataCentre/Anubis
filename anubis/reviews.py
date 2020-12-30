"Reviews lists."

import io

import flask
import xlsxwriter

import anubis.call
import anubis.user
import anubis.proposal
import anubis.review

from . import constants
from . import utils

blueprint = flask.Blueprint('reviews', __name__)

@blueprint.route('/call/<cid>')
@utils.login_required
def call(cid):
    "List all reviews for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    if not anubis.call.allow_view_reviews(call):
        return utils.error('You may not view the reviews of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    proposals = utils.get_docs_view('proposals', 'call', call['identifier'])
    for proposal in proposals:
        proposal['allow_create_review'] = anubis.review.allow_create(proposal)
    reviews = utils.get_docs_view('reviews', 'call', call['identifier'])
    # For ordinary reviewer, list only finalized reviews.
    if not (flask.g.am_admin or anubis.call.am_chair(call)):
        finalized = True
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    else:
        finalized = False
    reviews_lookup = {f"{r['proposal']} {r['reviewer']}":r for r in reviews}
    result = flask.render_template('reviews/call.html',
                                   call=call,
                                   proposals=proposals,
                                   reviews_lookup=reviews_lookup,
                                   finalized=finalized)
    return result

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all reviews for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    if not anubis.call.allow_view(call):
        return utils.error('You may not view the call.', flask.url_for('home'))
    if not anubis.call.allow_view_reviews(call):
        return utils.error('You may not view the reviews of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    proposals = utils.get_docs_view('proposals', 'call', call['identifier'])
    reviews = utils.get_docs_view('reviews', 'call', call['identifier'])
    # For ordinary reviewer, list only finalized reviews.
    if not (flask.g.am_admin or anubis.call.am_chair(call)):
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    reviews_lookup = {f"{r['proposal']} {r['reviewer']}":r for r in reviews}
    content = get_xlsx(call, proposals, reviews_lookup)
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_reviews.xlsx")
    return response

@blueprint.route('/call/<cid>/reviewer/<username>')
@utils.login_required
def call_reviewer(cid, username):
    "List all reviews in the call by the reviewer (user)."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if user['username'] not in call['reviewers']:
        return utils.error('The user is not a reviewer in the call.',
                           flask.url_for('home'))
    if not (user['username'] == flask.g.current_user['username']  or
            anubis.call.allow_view_reviews(call)):
        return utils.error("You may not view the user's reviews.",
                           flask.url_for('call.display',cid=call['identifier']))

    proposals = utils.get_docs_view('proposals', 'call', call['identifier'])
    reviews = utils.get_docs_view('reviews', 'call_reviewer',
                                  [call['identifier'], user['username']])
    reviews_lookup = {r['proposal']:r for r in reviews}
    return flask.render_template('reviews/call_reviewer.html', 
                                 call=call,
                                 proposals=proposals,
                                 user=user,
                                 reviews_lookup=reviews_lookup)

@blueprint.route('/call/<cid>/reviewer/<username>.xlsx')
@utils.login_required
def call_reviewer_xlsx(cid, username):
    "Produce an XLSX file of all reviews in the call by the reviewer (user)."
    call = anubis.call.get_call(cid)
    if call is None:
        return utils.error('No such call.', flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if user['username'] not in call['reviewers']:
        return utils.error('The user is not a reviewer in the call.',
                           flask.url_for('home'))
    if not (user['username'] == flask.g.current_user['username']  or
            anubis.call.allow_view_reviews(call)):
        return utils.error("You may not view the user's reviews.",
                           flask.url_for('call.display',cid=call['identifier']))

    proposals = utils.get_docs_view('proposals', 'call', call['identifier'])
    reviews = utils.get_docs_view('reviews', 'call_reviewer',
                                  [call['identifier'], user['username']])
    reviews_lookup = {f"{r['proposal']} {username}":r for r in reviews}
    content = get_xlsx(call, proposals, reviews_lookup)
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{cid}_{username}_reviews.xlsx")
    return response

@blueprint.route('/proposal/<pid>')
@utils.login_required
def proposal(pid):
    "List all reviewers and reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))

    call = anubis.call.get_call(proposal['call'])
    if not anubis.call.allow_view_reviews(call):
        return utils.error('You may not view the reviews of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    reviews = utils.get_docs_view('reviews', 'proposal', proposal['identifier'])
    if not (flask.g.am_admin or anubis.call.am_chair(call)):
        finalized = True
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    else:
        finalized = False
    allow_create_review = anubis.review.allow_create(proposal)
    reviews_lookup = {r['reviewer']:r for r in reviews}
    return flask.render_template('reviews/proposal.html',
                                 proposal=proposal,
                                 call=call,
                                 allow_create_review=allow_create_review,
                                 reviewers=call['reviewers'],
                                 reviews_lookup=reviews_lookup,
                                 finalized=finalized)

@blueprint.route('/proposal/<pid>/archived')
@utils.login_required
def proposal_archived(pid):
    "List all archived reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))

    call = anubis.call.get_call(proposal['call'])
    if not (flask.g.am_admin or anubis.call.am_chair(call)):
        return utils.error('You may not view the archived reviews of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    reviews = utils.get_docs_view('reviews', 'proposal_archived',
                                  proposal['identifier'])
    return flask.render_template('reviews/proposal_archived.html',
                                 reviews=reviews,
                                 proposal=proposal,
                                 call=call)

@blueprint.route('/proposal/<pid>.xlsx')
@utils.login_required
def proposal_xlsx(pid):
    "Produce an XLSX file of all reviewers and reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        return utils.error('No such proposal.', flask.url_for('home'))
    if not anubis.proposal.allow_view(proposal):
        return utils.error('You may not view the proposal.',
                           flask.url_for('call.display',cid=call['identifier']))
    call = anubis.call.get_call(proposal['call'])
    if not anubis.call.allow_view_reviews(call):
        return utils.error('You may not view the reviews of the call.',
                           flask.url_for('call.display',cid=call['identifier']))

    reviews = utils.get_docs_view('reviews', 'proposal', proposal['identifier'])
    if not (flask.g.am_admin or anubis.call.am_chair(call)):
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    reviews_lookup = {f"{pid} {r['reviewer']}":r for r in reviews}
    content = get_xlsx(call, [proposal], reviews_lookup)
    response = flask.make_response(content)
    response.headers.set('Content-Type', constants.XLSX_MIMETYPE)
    response.headers.set('Content-Disposition', 'attachment', 
                         filename=f"{pid}_reviews.xlsx")
    return response

@blueprint.route('/reviewer/<username>')
@utils.login_required
def reviewer(username):
    """List all reviews by the given reviewer (user).
    If the user is reviewer in only one call, redirect to that page.
    """
    user = anubis.user.get_user(username=username)
    if user is None:
        return utils.error('No such user.', flask.url_for('home'))
    if not anubis.user.allow_view(user):
        return utils.error("You may not view the user's reviews.",
                           flask.url_for('call.display',cid=call['identifier']))

    reviewer_calls = [anubis.call.get_call(r.value)
                      for r in flask.g.db.view('calls', 'reviewer', 
                                               key=user['username'],
                                               reduce=False)]
    # Reviews in only one call; redirect to its reviews page for the reviewer.
    if len(reviewer_calls) == 1:
        return flask.redirect(flask.url_for('reviews.call_reviewer',
                                            cid=reviewer_calls[0]['identifier'],
                                            username=username))

    reviews = utils.get_docs_view('reviews', 'reviewer', user['username'])
    return flask.render_template('reviews/reviewer.html',
                                 user=user,
                                 reviewer_calls=reviewer_calls,
                                 reviews=reviews)

def get_xlsx(call, proposals, reviews_lookup):
    "Return the content for the XLSX file for the list of reviews."
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
    long_text_format = wb.add_format({'text_wrap': True,
                                      'font_size': 14,
                                      'align': 'left',
                                      'valign': 'vcenter'})
    ws = wb.add_worksheet(f"Reviews in call {call['identifier']}")
    ws.freeze_panes(1, 1)
    ws.set_row(0, None, head_text_format)
    ws.set_column(1, 1, 40, normal_text_format)
    ws.set_column(2, 3, 20, normal_text_format)

    row = ['Proposal', 'Proposal title', 'Submitter', 'Affiliation',
           'Review', 'Finalized', 'Reviewer']
    for field in call['review']:
        row.append(field['title'] or field['identifier'])
    nrow = 0
    ws.write_row(nrow, 0, row)
    nrow += 1
    for proposal in proposals:
        for reviewer in call['reviewers']:
            review = reviews_lookup.get("{} {}".format(proposal['identifier'],
                                                       reviewer))
            if not review: continue
            user = anubis.user.get_user(username=proposal['user'])
            ncol = 0
            ws.write_url(nrow, ncol,
                         flask.url_for('proposal.display',
                                       pid=proposal['identifier'],
                                       _external=True),
                         string=proposal['identifier'])
            ncol += 1
            ws.write_string(nrow, ncol, proposal.get('title') or '')
            ncol += 1
            ws.write_string(nrow, ncol,
                            f"{user['familyname']}, {user['givenname']}")
            ncol += 1
            ws.write_string(nrow, ncol, user['affiliation'] or '')
            ncol += 1
            ws.write_url(nrow, ncol,
                         flask.url_for('review.display',
                                       iuid=review['_id'],
                                       _external=True),
                         string='Link')
            ncol += 1
            ws.write_string(nrow, ncol,
                            review.get('finalized') and 'yes' or 'no')
            ncol += 1
            ws.write_string(nrow, ncol, reviewer)
            ncol += 1
            for field in call['review']:
                value = review['values'].get(field['identifier'])
                if value is None:
                    ws.write_string(nrow, ncol, '')
                elif field['type'] == constants.TEXT:
                    ws.write_string(nrow, ncol, value)
                elif field['type'] == constants.DOCUMENT:
                    ws.write_url(nrow, ncol,
                                 flask.url_for('review.document',
                                               iuid=review['_id'],
                                               fid=field['identifier'],
                                               _external=True),
                                 string='Link')
                else:
                    ws.write(nrow, ncol, value)
                ncol += 1
            nrow += 1

    wb.close()
    return output.getvalue()
