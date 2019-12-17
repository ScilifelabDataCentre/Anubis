"Reviews lists."

import tempfile

import flask
import openpyxl
import openpyxl.styles

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
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view(call):
        utils.flash_error("You may not view the call.")
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view_reviews(call):
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    for proposal in proposals:
        proposal['cache']['allow_review_create'] = anubis.review.allow_create(proposal)
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call',
                                        key=call['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    # For ordinary reviewer, list only finalized reviews.
    if not (flask.g.am_admin or anubis.call.is_chair(call)):
        finalized = True
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    else:
        finalized = False
    reviews_lookup = {f"{r['proposal']} {r['reviewer']}":r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/call.html',
                                 call=call,
                                 proposals=proposals,
                                 reviews_lookup=reviews_lookup,
                                 finalized=finalized,
                                 scorefields=scorefields)

@blueprint.route('/call/<cid>.xlsx')
@utils.login_required
def call_xlsx(cid):
    "Produce an XLSX file of all reviews for a call."
    call = anubis.call.get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view(call):
        utils.flash_error("You may not view the call.")
        return flask.redirect(flask.url_for('home'))
    if not anubis.call.allow_view_reviews(call):
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call',
                                        key=call['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    # For ordinary reviewer, list only finalized reviews.
    if not (flask.g.am_admin or anubis.call.is_chair(call)):
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
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if user['username'] not in call['reviewers']:
        utils.flash_error("The user is not a reviewer in the call.")
        return flask.redirect(flask.url_for('home'))
    if not (user['username'] == flask.g.current_user['username']  or
            anubis.call.allow_view_reviews(call)):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call_reviewer',
                                        key=[call['identifier'],
                                             user['username']],
                                        reduce=False,
                                        include_docs=True)]
    reviews_lookup = {r['proposal']:r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/call_reviewer.html', 
                                 call=call,
                                 proposals=proposals,
                                 user=user,
                                 reviews_lookup=reviews_lookup,
                                 scorefields=scorefields)

@blueprint.route('/call/<cid>/reviewer/<username>.xlsx')
@utils.login_required
def call_reviewer_xlsx(cid, username):
    "Produce an XLSX file of all reviews in the call by the reviewer (user)."
    call = anubis.call.get_call(cid)
    if call is None:
        utils.flash_error('No such call.')
        return flask.redirect(flask.url_for('home'))
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    if user['username'] not in call['reviewers']:
        utils.flash_error("The user is not a reviewer in the call.")
        return flask.redirect(flask.url_for('home'))
    if not (user['username'] == flask.g.current_user['username']  or
            anubis.call.allow_view_reviews(call)):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    proposals = [anubis.proposal.set_cache(r.doc)
                 for r in flask.g.db.view('proposals', 'call',
                                          key=call['identifier'],
                                          reduce=False,
                                          include_docs=True)]
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'call_reviewer',
                                        key=[call['identifier'],
                                             user['username']],
                                        reduce=False,
                                        include_docs=True)]
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
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))

    call = proposal['cache']['call']
    if not anubis.call.allow_view_reviews(call):
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    is_chair = anubis.call.is_chair(call)
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'proposal',
                                        key=proposal['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    if not (flask.g.am_admin or anubis.call.is_chair(call)):
        finalized = True
        reviews = [r for r in reviews
                   if r['reviewer'] != flask.g.current_user['username'] and 
                   r.get('finalized')]
    else:
        finalized = False
    allow_create = anubis.review.allow_create(proposal)
    reviews_lookup = {r['reviewer']:r for r in reviews}
    scorefields = [f for f in call['review'] if f['type'] == constants.SCORE]
    return flask.render_template('reviews/proposal.html',
                                 proposal=proposal,
                                 allow_create=allow_create,
                                 reviewers=call['reviewers'],
                                 reviews_lookup=reviews_lookup,
                                 finalized=finalized,
                                 scorefields=scorefields)

@blueprint.route('/proposal/<pid>.xlsx')
@utils.login_required
def proposal_xlsx(pid):
    "Produce an XLSX file of all reviewers and reviews for a proposal."
    proposal = anubis.proposal.get_proposal(pid)
    if proposal is None:
        utils.flash_error('No such proposal.')
        return flask.redirect(flask.url_for('home'))
    if not anubis.proposal.allow_view(proposal):
        utils.flash_error('You may not view the proposal.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))
    call = proposal['cache']['call']
    if not anubis.call.allow_view_reviews(call):
        utils.flash_error('You may not view the reviews of the call.')
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    is_chair = anubis.call.is_chair(call)
    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'proposal',
                                        key=proposal['identifier'],
                                        reduce=False,
                                        include_docs=True)]
    if not (flask.g.am_admin or anubis.call.is_chair(call)):
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
    "List all reviews by the given reviewer (user)."
    user = anubis.user.get_user(username=username)
    if user is None:
        utils.flash_error('No such user.')
        return flask.redirect(flask.url_for('home'))
    # Access to view all reviews of a specific call is not sufficient.
    if not anubis.user.am_admin_or_self(user):
        utils.flash_error("You may not view the user's reviews.")
        return flask.redirect(
            flask.url_for('call.display', cid=call['identifier']))

    reviews = [anubis.review.set_cache(r.doc)
               for r in flask.g.db.view('reviews', 'reviewer',
                                        key=user['username'],
                                        reduce=False,
                                        include_docs=True)]
    return flask.render_template('reviews/reviewer.html', 
                                 user=user,
                                 reviews=reviews)

def get_xlsx(call, proposals, reviews_lookup):
    "Return the content for the XLSX file for the list of reviews."
    from openpyxl.utils.cell import get_column_letter
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Reviews in call {call['identifier']}"
    row = ['Proposal', 'Proposal title', 'Submitter', 
           'Review', 'Finalized', 'Reviewer']
    ws.column_dimensions[get_column_letter(2)].width = 30
    review_column = get_column_letter(4)
    ws.column_dimensions[review_column].width = 30
    for field in call['review']:
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
        for reviewer in call['reviewers']:
            review = reviews_lookup.get("{} {}".format(proposal['identifier'],
                                                       reviewer))
            if review:
                row_number += 1
                row = [proposal['identifier'], 
                       proposal.get('title') or '',
                       proposal['user'],
                       flask.url_for('review.display',
                                     iuid=review['_id'], _external=True),
                       review.get('finalized') and 'yes' or 'no',
                       reviewer]
                wraptext = []
                hyperlink = []
                for field in call['review']:
                    value = review['values'].get(field['identifier'])
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
                colrow = f"{review_column}{row_number}"
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
    return content
