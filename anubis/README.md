# Source code description

## General design features

The app uses the standard Flask way of doing things, i.e. it is uses mostly
functions. Object-oriented programming is used sparingly.

Access privileges are checked either by a decorator on the function,
or as early as possible in the execution using functions named `allow_xxx`.

CouchDB documents are edited using a `with` context manager called `XxxSaver`.
This takes care of saving the document and the log entry for the edit.

## `__init__.py`

Version number and various constants.

## app.py

The Anubis Flask app main module.

- Import of modules.
- Read the configuration file and environment variables.
- Initialize the blueprints.
- `setup_template_context`: Does just that.
- `prepare`: Set up the context for each request.
- Setup of URLs; delegation to their respective blueprint.
- `home`: Display home page.

## user.py

The user account module. A user is uniquely defined by her account identifier
and also by her email.

- `init`: CouchDB index creation (design document) for the user document type.
- `register`: Account creation. URL.
- `login`, `logout`: Login and logout the current user. URL.
- `reset`: Password reset and send email with one-time code. URL.
- `password`: Password set using one-time code. URL.
- `display`: Show info page for a user account. URL.
- `edit`: Edit the information for a user account. URL.
- `logs`: Display the log records for the given user account. URL.
- `all`: Display list of all user accounts. URL.
- `pending`: Display list of all pending user accounts. URL.
- `enable`, `disable`: Enable or disable the given user account. URL.
- `class UserSaver`: User document saver context manager.
- `get_user`: Return the user for the given username or email.
- `get_users`: GEt the users specified by role and optionally by status.
- `get_current_user`: Return the user for the current session from the
   encrypted session cookie.
- `do_login`: Set the session cookie if successful login.
- `send_password_code`: Send an email with the one-time code.
- `am_admin`: Is the user admin? Be default checks the current user.
- `am_staff`: Is the user staff? Be default checks the current user.
- `allow_view`: Is the current user allowed to view the user account?
- `allow_edit`: Is the current user allowed to edit the user account?
- `allow_delete`: Can the given user account be deleted?
- `allow_enable_disable`: Is the current user allowed to enable or disable
   the given user account?
- `allow_change_role`: Is the current user allowed to change the role
   of the current user account?

## call.py

## calls.py

## command_line_tool.py

## config.py

## decision.py

## grant.py

## grants.py

## proposal.py

## proposals.py

## review.py

## reviews.py

## saver.py

## about.py

Information pages endpoints; documentation, contact, gdpr, software info.

## site.py

## dump.py

## undump.py

## utils.py

## documentation

Directory containing documentation files to display within the app.

## static

Directory for static resources; `robots.txt`, logo, local JavaScript files.

## templates

Directory containing HTML templates for Flask/Jinja2.
