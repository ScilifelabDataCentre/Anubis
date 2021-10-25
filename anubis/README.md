# Source code description

## General design features

The app tries to use the standard Flask way of doing things, i.e. it
uses functions for dealing with HTTP requests. Object-oriented
programming is used mainly for the document saver context manager (see
below).

Access privileges are checked either by a decorator on the function,
or as early as possible in the request handling using functions named
`allow_xxx`.

CouchDB documents are edited using a `with` context manager called
`XxxSaver`.  It takes care of saving the document and the log entry
for the edit.


## `__init__.py`

Version number and various constants.


## `app.py`

The Anubis Flask app main module.

- Import of modules.
- Read the configuration file and environment variables.
- Initialize the blueprints.
- `setup_template_context`: Does just that.
- `prepare`: Set up the context for each request.
- Setup of URLs; delegation to their respective blueprint.
- `home`: Display home page.
- `status`: Return JSON for the current status.
- `sitemap`: Return an XML sitemap.


## `config.py`

- `DEFAULT_SETTINGS`: Dictionary containing all configuration
  variables and their default values.
- `init`: Setup of the configuration for this instance of
  Anubis. Starting with the default values, check for settings file
  using environment label and two hard-wired locations. It checks
  the sanity of a few settings.


## `user.py`

The user account module. A user is uniquely defined by her account
identifier and also by her email.

The most important functions are:

### URL-mapped functions

- `login`, `logout`: Login and logout the current user.
- `register`: Account creation.
- `reset`: Password reset and send email with one-time code.
- `password`: Password set using one-time code.
- `display`: Display the user account information.
- `edit`: Edit the information for a user account.
- `logs`: Display the log records for the given user account.
- `all`: Display list of all user accounts.
- `pending`: Display list of all pending user accounts.
- `enable`, `disable`: Enable or disable the given user account.

### Other functions

- `init`: CouchDB index creation (design document) for the user document type.
- `class UserSaver`: CouchDB document saver context manager.
  Contains functions to set various fields using form input.
- `get_user`: Return the user for the given username or email.
- `get_users`: Return the users specified by role and optionally by status.
- `get_current_user`: Return the user for the current session from the
   encrypted session cookie.
- `allow_XXX`: Access privilege checking functions.


## `call.py`

Module for call pages. A call is a container of proposals. It is the
fundamental entity which all other entities (except user account)
depend on. It contains all field definitions for the other entities:
proposal, review, decision and grant.

The different sets of fields of a call may be changed at any time.
But beware: if e.g. changing a proposal field from optional to required
may inadvertenly invalidate some proposals (but not break the system itself).
Change an open call with care.

The most important functions are:

### URL-mapped functions

- `create`: Create new a call from scratch.
- `display`: Display the call information.
- `edit`: Edit the top-level information for the call; title, description,
  open and close dates, access, etc.
- `access`: Edit the access privileges for the call.
- `documents`: Edit the documents attached to a call.
- `document`: Download the specified document attached to a call.
- `proposal`: Display the proposal field definitions, for edit, delete or add.
- `proposal_field`: Edit or delete the proposal field definition.
- `reviewers`: Edit the list of reviewers, which must have user accounts.
- `review`: Display the review field definitions, for edit, delete or add.
- `review_field`: Edit or delete the review field definition.
- `decision`: Display the decision field definitions, for edit, delete or add.
- `decision_field`: Edit or delete the decision field definition.
- `grant`: Display the grant field definitions, for edit, delete or add.
- `grant_field`: Edit or delete the grant field definition.
- `reset_counter`: Reset the proposal counter.
- `clone`: Clone the call.
- `logs`: Display the log records for the given call.
- `create_proposal`: Create a proposal in the given call for the current user.
- `call_zip`: Download a zip file containing the XLSX for all
  submitted proposals and all documents attached to those proposals.

### Other functions

- `init`: CouchDB index creation (design document) for the call document type.
- `class CallSaver`: CouchDB document saver context manager.
  Contains functions to set various fields using form input.
- `get_call`: Return the call with the given identifier.
- `set_tmp`: Set various non-saved parameters in the call document which
  are used in other functions.
- `allow_XXX`: Access privilege checking functions.

## `calls.py`

Module for calls lists pages.

### URL-mapped functions

- `all`: List of all calls.
- `owner`: List of all calls owned (created) by the given user.
- `closed`: List of all closed calls; the closed date has passed.
- `open`: List of all open calls; the open date has passed, but not
  the closed date.
- `grants`: List of all calls that have grants in them.

### Other functions

- `get_open_calls`: Return a list of all open calls.


## `proposal.py`

A proposal is created from an open call. It must be created by a user account
in the system. It may be transferred to another user. A user may have at most
one proposal in a call.

The most important functions are:

### URL-mapped functions

- `display`: Display the proposal information.
- `display_docx`: Return a DOCX file containing the proposal information.
- `display_xlsx`: Return an XLSX file containing the proposal information.
- `edit`: Edit the proposal information, such as title and category.
- `transfer`: Change ownership of the proposal to another user account.
- `submit`: Submit the proposal. This can be done only if the call is still
  open and the proposal's information is correctly filled in.
- `unsubmit`: Unsubmit a previously submitted proposal. This can be done
  only if the call is still open.
- `access`. Edit the access privileges of the given proposal. Specific users
  may be set to have access to the proposal.
- `document`: Download the specified document attached to the proposal.
- `logs`: Display the log records for the given proposal.

### Other functions

- `init`: CouchDB index creation (design document) for the proposal
  document type.
- `send_submission_email`: Send an email confirming the submission.
- `get_document`: Return a dictionary containing the document in the given
  field in the given proposal.
- `class ProposalSaver`: CouchDB document saver context manager.
  Contains functions to set various fields using form input. Checks for
  errors in input; if any, then the proposal cannot be submitted.
- `get_proposal`: Return the proposal given its identifier.
- `get_call_user_proposal`: Return the proposal owned by the user in the call.
- `get_proposal_docx`: Return the proposal as a DOCX file.
- `get_proposal_xlsx`: Return the proposal as a XLSX file.
- `allow_XXX`: Access privilege checking functions.


## `proposals.py`

### URL-mapped functions

- `call`: List all proposals in a call. Optionally by category.
- `call_xlsx`: Produce an XLSX file of all proposals in a call.
- `user`: List all proposals for a user.

### Other functions

- `get_call_xlsx`: Return the content of an XLSX file for all
  proposals in a call.
- `get_call_proposals`: Get the proposals in the call.
- `get_user_proposals`: Get all proposals created by the user.
- `get_review_scoren_fields`: Compute and return score banner field info.
- `get_review_rank_field_errors`: Compute and return rank banner field info.

## `review.py`

There is at most one review per reviewer and proposal. It is possible
to archive reviews if a review process is to be repeated for the
proposals in a call.

### URL-mapped functions

- `create`: Create a new review for the proposal for the given reviewer.
- `display`: Display the review for the proposal.
- `edit`: Edit the review for the proposal.
- `finalize`, `unfinalize`: (Un)finalize the review for the proposal.
- `archive`, `unarchive`: (Un)archive the review for the proposal. An
  archived review is not shown in most views, but is reachable.
- `logs`: Display the log records for the given review.
- `document`: Download the review document (attachment file) for the
  given field id.

### Other functions

- `init`: CouchDB index creation (design document) for the review
  document type.
- `class ReviewSaver`: CouchDB document saver context manager.
  Contains functions to set various fields using form input.
- `get_review`: Get the review by its iuid.
- `get_reviewer_review`: Get the review of the proposal by the reviewer.
- `allow_XXX`: Access privilege checking functions.


## `reviews.py`

### URL-mapped functions

- `call`: List all reviews for a call.
- `call_xlsx`: Produce an XLSX file of all reviews for a call.
- `call_reviewer`: List all reviews in the call by the reviewer (user).
- `call_reviewer_xlsx`: Produce an XLSX file of all reviews in the
  call by the reviewer (user).
- `call_reviewer_zip`: Return a zip file containing the XLSX file of
  all reviews in the call by the reviewer (user), and all documents
  for the proposals to be reviewed.
- `proposal`: List all reviewers and reviews for a proposal.
- `proposal_archived`: List all archived reviews for a proposal.
- `call_archived`: List all archived reviews in the call.
- `call_reviewer_archived`: List all archived reviews in the call by
  the reviewer (user).
- `proposal_xlsx`: Produce an XLSX file of all reviewers and reviews
  for a proposal.
- `reviewer`: List all reviews by the given reviewer (user).

### Other functions

- `get_review_xlsx`: Return the content for the XLSX file for the list
  of reviews.


## `decision.py`

A decision represents the result of the review and decision
process. It is intended to be shown to the proposer, but this is not
done until the switch for this is set for the call.

There are no decision lists; the decisions are shown in the proposals lists.

### URL-mapped functions

- `create`: Create a decision for the proposal.
- `display`: Display the decision.
- `edit`: Edit the decision.
- `finalize`, `unfinalize`: (Un)finalize the decision for the proposal.
- `logs`: Display the log records for the given decision.
- `document`: Download the decision document (attachment file) for the
  given field id.

### Other functions

- `init`: CouchDB index creation (design document) for the decision
  document type.
- `class DecisionSaver`: CouchDB document saver context manager.
- `get_decision`: Get the decision by its iuid.
- `allow_XXX`: Access privilege checking functions.


## `grant.py`

Grants, or grant dossiers, are containers for information and documents
relating to payment and tracking of grants relating to accepted proposals.

### URL-mapped functions

- `create`: Create a grant dossier for the proposal.
- `display`: Display the grant dossier.
- `edit`: Edit the grant dossier.
- `access`: Edit the access privileges for the grant record.
- `lock`, `unlock`: (Un)lock the grant dossier for edits by the user.
- `document`: Download the grant document (attachment file) for the
  given field id.
- `grant_zip`: Return a zip file containing all documents in the grant
  dossier.
- `logs`: Display the log records for the given grant.

### Other functions

- `init`: CouchDB index creation (design document) for the grant
  document type.
- `get_grant_documents`: Get all documents in a grant as a list of
  dict(filename, content).
- `class GrantSaver`: CouchDB document saver context manager.
- `get_grant`: Return the grant dossier with the given identifier.
- `get_grant_proposal`: Return the grant dossier for the proposal with
  the given identifier.
- `allow_XXX`: Access privilege checking functions.


## `grants.py`

### URL-mapped functions

- `call`: List all grants for a call.
- `call_xlsx`: Produce an XLSX file of all grants for a call.
- `call_zip`: Return a zip file containing the XLSX file of all grants
  for a call and all documents in all grant dossiers.
- `user`: List all grants for a user, including the grants the user
  has access to.

### Other functions

- `get_call_grants_xlsx`: Return the content for the XLSX file for the
  list of grants.


## `about.py`

Information pages endpoints; documentation, contact, gdpr, software info.

### URL-mapped functions

- `documentation`: Display the given documentation page.
- `contact`: Display the contact information page.
- `gdpr`: Display the personal data policy page.
- `software`: Show the current software versions.
- `settings`: Display all configuration settings.


## `site.py`

- `static`: Return the given site-specific static file.


## `utils.py`

Various utility functions used in other modules.
- Fetching data and counts from the database.
- Access decorators.
- Value converters.
- Date and time functions.
- Request HTTP method determination.
- Error messages.
- HTML template filters.
- Markdown handling.
- Email send utilities.


## `saver.py`

Base classes and mixins for the saver context classes specific to each
document type.


## `cli.py`

A simple command-line interface; see its help text output.


## documentation

Directory containing documentation files to display within the app.


## static

Directory for static resources; `robots.txt`, logo, local JavaScript files.


## templates

Directory containing HTML templates for Flask/Jinja2.
