# Source code description

## General design features

The app uses the standard Flask way of doing things, i.e. it is uses
mostly functions. Object-oriented programming is used mainly for the
document saver context manager (see below).

Access privileges are checked either by a decorator on the function,
or as early as possible in the execution using functions named
`allow_xxx`.

CouchDB documents are edited using a `with` context manager called
`XxxSaver`.  This takes care of saving the document and the log entry
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


## `config.py`

- `DEFAULT_SETTINGS`: Dictionary containing all configuration
  variables and their default values.
- `init`: Setup of the configuration for this instance of
  Anubis. Starting with the default values, check for settings file
  using argument, environment label and two hard-wired locations. Then
  also check a few hard-wired environment labels.


## `user.py`

The user account module. A user is uniquely defined by her account identifier
and also by her email.

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
- `class UserSaver`: CouchDB user document saver context manager. Contains
   functions to set various fields using form input.
- `get_user`: Return the user for the given username or email.
- `get_users`: Return the users specified by role and optionally by status.
- `get_current_user`: Return the user for the current session from the
   encrypted session cookie.
- `allow_XXX`: Access privilege checking functions.


## `call.py`

Module for call pages. A call is a container of proposals. It is the
fundamental entity which all other entities (except user account) must
refer. It contains all field definitions for the other entities
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
- `documents`: Edit the documents attached to a call.
- `document`: Download the specified document attached to a call.
- `proposal`: Display the proposal field definitions, and add field.
- `proposal_field`: Edit or delete the proposal field definition.
- `reviewers`: Edit the list of reviewers, which must have user accounts.
- `review`: Display the review field definitions, and add field.
- `review_field`: Edit or delete the review field definition.
- `decision`: Display the decision field definitions, and add field.
- `decision_field`: Edit or delete the decision field definition.
- `grant`: Display the grant field definitions, and add field.
- `grant_field`: Edit or delete the grant field definition.
- `reset_counter`: Reset the proposal counter.
- `clone`: Clone the call.
- `logs`: Display the log records for the given call.
- `create_proposal`: Create a proposal in the given call for the current user.
- `call_zip`: Download a zip file containing the XLSX for all
  submitted proposals and all documents attached to those proposals.

### Other functions

- `init`: CouchDB index creation (design document) for the call document type.
- `class CallSaver`: CouchDB call document saver context manager. Contains
   functions to set various fields using form input.
- `get_call`: Return the call with the given identifier.
- `set_tmp`: Set various parameters in the call document which are used
  in other functions, but will not be stored.
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
- `get_document`: Return a dictionary containing the document in the given
  field in the given proposal.
- `class ProposalSaver`: CouchDB proposal document saver context manager.
  Contains functions to set various fields using form input. Checks for
  errors in input; if any, then the proposal cannot be submitted.
- `get_proposal`: Return the proposal given its identifier.
- `get_call_user_proposal`: Return the proposal owned by the user in the call.
- `allow_XXX`: Access privilege checking functions.


## `proposals.py`

### URL-mapped functions

### Other functions


## `review.py`

### URL-mapped functions

### Other functions


## `reviews.py`

### URL-mapped functions

### Other functions


## `decision.py`

### URL-mapped functions

### Other functions


## `grant.py`

### URL-mapped functions

### Other functions


## `grants.py`

### URL-mapped functions

### Other functions


## `about.py`

Information pages endpoints; documentation, contact, gdpr, software info.

### URL-mapped functions

### Other functions


## `site.py`


## `utils.py`


## `saver.py`


## `dump.py`


## `undump.py`


## `command_line_tool.py`


## documentation

Directory containing documentation files to display within the app.


## static

Directory for static resources; `robots.txt`, logo, local JavaScript files.


## templates

Directory containing HTML templates for Flask/Jinja2.
