# Anubis documentation

Anubis is a web-based system to handle calls, proposal submission,
reviews, decisions and grant dossiers. It allows:

- The publication of calls, with handling of open/close dates.
- Proposals can be created, edited and submitted based on open calls.
- A person who wants to prepare and submit a proposal must create an
  account in the system.
- The administrator configures which accounts should be reviewers of
  the proposals in a call.
- The administrator records the decisions that the reviewers (or other group) have made.
- Grants can have information and documents related to them added by both grantees
  and the Anubis site staff.

# Entities

## Call

This is a call for proposals, with a description, optional files
attached, and open and close dates. It is a container for proposals,
reviews, decisions and grants. The input fields of these entities
are created and defined within their call.

## Proposal

A proposal can be created only within an open call. A user has to
create an account in order to create and write a proposal. The
proposal must be submitted by the user before the close date of the
call.

A proposal is visible only to its creator, the admin, and those
accounts that the proposal owner has explicitly given access to.

## Review

The reviews of proposals within a call are set up by the admin. This
entails defining what information the reviewers must provide,
including scores, rank or comments. The admin must then create the
actual review form for each reviewer and proposal.

The reviews are visible only the admin, the owner of the call, and
optionally by the other reviewers in the call.

### Decision

The purpose of the decision entity is to document what the result of
the review of a proposal is. Creating a decision does not send any
email to the proposal author. This has to be done outside of the
system.

### Grant dossier

A grant dossier is a means for the grantee and staff to share
information and/or documents about a successful proposal.

## User account

A user account is the representation of a user in the Anubis system. A
person must have a user account to be able to write a proposal.

### User roles

There are a few different roles giving different levels of privileges
in the web interface.

- Role **user**: The default role, which allows creating, editing and submitting
  proposals in open calls.
- Role **staff**: Allows viewing user accounts, proposals and the other entities.
- Role **admin**: Allows access to all features of the web interface,
  which includes viewing and changing user accounts, and configuring
  certain aspects of the Anubis instance.

# Instructions

## Instructions for users

### Create a user account

- In order to create a proposal in a call, a user must have an account
  in the system.
- To create an account in the Anubis system, go to the page
  [Register a user account](/user/register) and follow the
  instructions.
- When a new user account has been enabled, you will receive an email
  describing how to set your password.
- Once you have an enabled account with the password set, you may
  create a proposal from an open call.

### Create a proposal

- Go to the page of the open call. All open calls are displayed on the
  home page.
- Unless you have not already created a proposal in the call, there is
  a button in the call page allowing you to do so.
- **Create** the proposal and fill in the values for the input fields.
- You may save the unfinished proposal and return to **editing** it later.
- Once the required fields of the proposal have been filled in correctly,
  you may **submit** it.
- A proposal that has been submitted can no longer be edited.
- As long as the call is open, you may un-submit your proposal if you
  wish to edit it further, or even delete it.
- Once the call's deadline for submission has been passed, the user
  may no longer submit a proposal. **Be sure to submit your proposal
  before the deadline!**

### Display your proposals

- The number of your unsubmitted proposals is displayed on a yellow
  background in the top menu. If there is no such yellow marker, your
  proposals, if any, have all been submitted.
- To list all your proposals, click the item "My proposals" in the
  top menu.

## Instructions for reviewers

The number of your unfinalized reviews is displayed on a yellow
background in the top menu. If there is no such yellow marker, your
reviews are done.

#### How to get the proposals

- As a reviewer, you have access to all submitted proposals in the call.
- Depending on the policy for the call, you should read all or only
  some of the proposals.
- To download all proposals and their attached files, go to the call page. In the
  right-hand upper corner, there are two small black buttons:
  1. "Submitted proposals Excel file", which allows you to download
     the information in all submitted proposals in Excel format. This
     does not contain the files attached to proposals, if any.
  2. "Submitted proposals zip file", which contains the above Excel
     file, **and** all files attached to the proposals. The naming of
     the files indicates which one belongs to which proposal.
- It is also possible to browse the proposals in a list display by
  clicking the blue button by the item "All proposals" on the call
  page.

#### How to fill in your reviews

1. Click on the item "My reviews" in the top menu.
   - The list of all reviews for your user account are shown in a table,
     which can be sorted by any column.
   - **Note** that the table may have more than one page, depending on
     the number of proposals. Use the page selector at the bottom right of
     the table.
2. Click on the link "Review" to view the review of the proposal on
   that line in the table.
3. Edit the review.
4. Click **Finalize** to indicate that you are done with the review.
   - Until the **due** date for reviews in the call, you may
     **Unfinalize** a review if you wish to resume editing it.
5. To view the proposal of the review, click the link to the proposal
   in the title. (Tip: do right-click and "Open in new tab".)
6. Before the **due** date, ensure that all your reviews have been
   finalized.

### Reviewer: Basic information

- A user account is set as a reviewer for a specific call by the admin
  of the Anubis system.
- The admin also creates the review instances for the proposals for
  each reviewer. A reviewer cannot create the review instances, only the admin
  can do this.
- Depending on the policy for the call, a reviewer may have to write a
  review for all or only some proposals. The admin handles this by creating those
  review instances that the reviewer should fill in.
- The content (input fields) of the reviews are set for the call by the admin.
- The reviews of a call have a **due** date, before which all reviews must
  have been finalized by the reviewers.
- There may be a chair designated for a call. This is a reviewer
  heading the reviewer group. He or she has additional privileges, if
  so set by the admin.

### Reviewer privileges

- The reviewer may view all proposals in the call.
- The reviewer can edit her review instance.
- The reviewers cannot create or delete review instances.
- The chair, if any, of a call may create review instances, if so set by the admin.
- The chair, if any, may view all reviews, if so set by the admin.
- A reviewer may view finalized reviews by other reviewers only if the
  admin allows it for the call.

## Instructions for staff

## Instructions for admins

The admin is a user account which has full privileges for the Anubis
site. She may perform all operations that are possible to do via the
web interface.

### User account handling

- The admin may register user accounts.
- The admin may edit, enable or disable user accounts.
- An admin may set other user accounts to be admin.

### Call handling

- The admin creates a call, and edits its content.
- The admin controls when a call becomes published by setting the
  **opens** date of the call.
- The admin controls the deadline for creating and submitting
  proposals to a call by setting the **closes** date.
- The contents of a call (the input fields for proposals, reviews and
  decisions) can be edited whenever by the admin, but when a call has
  been published it should be kept intact, or users will be confused.

### Reviewers and reviews

- The admin may set a user account as a **reviewer** in a call.
- The admin may also set a user account as a **chair** for a
  call. This is a special type of reviewer who has slightly higher
  privileges than ordinary reviewers.
- The admin must create the **review** instances for each reviewer and
  proposal in a call. It is up to the admin to decide which proposals
  a reviewer must review.

### Proposal handling

- The admin is allowed to edit and submit any user's proposals. This
  can be done even when the call for the proposal has been closed. Of
  course, this should be done only in special circumstances.
- The admin is allowed to change the ownership of a proposal.

# Installation

## Software

The source code is available the
[Anubis GitHub repo](https://github.com/pekrau/Anubis).

Anubis requires Python >= 3.9 and [CouchDB >= 2.3.1](https://couchdb.apache.org/);
installation of those systems is not documented here.

### Source code

Get the source code by downloading the
[latest release from GitHub](https://github.com/pekrau/Anubis/releases)
and unpacking it. For simplicity, rename the top directory to `Anubis`.

It is recommended to set up a virtual environment for Anubis. On my
development machine, I am using the `virtualenv` system:

```bash
$ mkvirtualenv Anubis
$ cd Anubis
$ add2virtualenv        # To add the top Anubis dir to Python path.
$ setvirtualenvproject  # To make this dir the default when doing 'workon'.
```

The installation of a virtual environment system is not documented here.

Within the virtual environment, download and install the required
Python packages from PyPi:

```bash
$ workon Anubis  # Activate the virtual environment
$ pip install -r requirements.txt
```

### Docker container

A Docker container of the
[latest release is available at GitHub](https://github.com/pekrau/Anubis/pkgs/container/anubis).

## CouchDB database

The Anubis system relies on the [CouchDB database system](https://couchdb.apache.org/).
This has to be installed and running.

A user account has to be created in the CouchDB system with sufficient privileges
to create a database within it. This is the account used by Anubis to create,
access and modify its data.

For these actions, refer to the CouchDB documentation.

### Configuration

The Anubis `flask` app needs to be run within another web server. This
depends on the web server you select and is not documented here.

In order to execute, there are some configuration that needs to be done
at the system level. This can be done in one of two ways:

1. Setting environment variables that specify the configuration values.
2. Using a file `settings.json` containing the configuration values.
or
runs as a `uwsgi` web server. It
needs to be configured. This is done in a JSON file called
`settings.json` located in the `site` directory.

```bash
$ cd Anubis
$ cp -r site_template site
$ cd site
$ chmod go-rw settings.json  # Since it contains secrets
$ emacs settings.json  # Ok, ok, vim also works...
```

In particular, the following settings should be looked at:

- `"DEBUG": "true"` Web server debug mode: should be "false" in production.
- `"SECRET_KEY": "long-string-of-random-chars"` Needed for proper
  session handling.
- `"COUCHDB_URL"` The URL to the CouchDB instance.
- `"COUCHDB_DATABASE"` The name of the CouchDB database for Anubis.
- `"COUCHDB_USERNAME"` The name of the user account with read/write
  access to the CouchDB database.
- `"COUCHDB_PASSWORD"` The password for the user account.
- `"SITE_STATIC_DIRPATH"`: The full path to the directory containing
  site-specific files, such as logo image files.
- `"HOST_LOGO"`: The file name of the site-specific logo image
  file. It must be locaded in the `SITE_STATIC_DIRPATH`.
- `"HOST_NAME"`: The name of host of the site; e.g. the institution.
- `"HOST_URL"`: The URL to the home page of the host.
- `"MAIL_SERVER"`: The name of the mail server. There are more
  settings to define if the mail server cannot be set as
  `localhost`. See the `Anubis/anubis/config.py` file.

Place any image files defined in the `settings.json` file in the
`site/static` directory.

#### CouchDB

A database for Anubis needs to be created within the CouchDB
instance. See the CouchDB documentation on how to do this.

If a username and password is required for read/write access to the
CouchDB database for Anubis, then add those with the name of the database
to the `settings.json` file; see above.

#### Web server

The SciLifeLab instance uses `nginx` as a reverse proxy for the
`flask` web server that implements Anubis. The file
`Anubis/install/uwsgi.conf` contains the setup for `nginx`.
It should be located in the directory `/etc/nginx/conf.d`.

To run Anubis as a `systemd` service under Linux, the file
`Anubis/install/anubis.system` contains the setup. It should be
located in the directory `/etc/systemd/system`.

Useful `systemctl` commands are:

```bash
$ sudo systemctl status anubis
$ sudo systemctl start anubis
$ sudo systemctl restart anubis
$ sudo systemctl stop anubis
```

There is also a updating script `Anubis/install/deploy_anubis.bash` to
be located in a site-dependent directory and run like so:

```bash
$ sudo /etc/scripts/deploy_anubis.bash
```

This script contains the somewhat mysterious commands needed to make
things work under the restrictive security policies of SELinux.

# XXX Needs refactoring!

## Privileges

Different user roles have different sets of privileges, which
determine what they are allowed to do within the Anubis system.

Anonymous users (not logged-in) are allowed to view open calls and not
much else.

In order to create and edit anything in Anubis, a user account is
required.

The privileges determine which actions are allowed for a logged-in
user. The role of the user account controls this. A user account has
one single role for the whole system at all times. There are three
roles:

1. **Admin**: The system administrator, who can do everything that can
   be done via the web interface.
2. **Staff**: The Anubis staff, who can view everything, but not
   change all that much.
3. **User**: Anyone who has registered an account in Anubis. She is
   allowed to create, edit and submit a proposal in an open call. She can
   view all her current and previous proposals, and view decisions and
   grant pages, if any, for each specific proposal.

Accounts with the user role can be given additional privileges, which
relate to specific calls only:

- A user can be set as a reviewer in a call, in which case she gets
  more privileges for that call.
- In addition, a reviewer can be set as chair for that review. This gives
  further privileges.
- A user can be allowed to create calls, in which case she has more privileges
  for that call.

Here's a summary of privileges for some actions. Note that some
exceptions are omitted, such as a user explicitly allowing another
user to view and/or edit their proposal.

<table class="table">

<tr>
<th></th>
<th>User</th>
<th>User (reviewer)</th>
<th>User (call creator)</th>
<th>Staff</th>
<th>Admin</th>
</tr>

<tr>
<th>Create proposal in open call</th>
<td><span class="bi-check-lg text-success"></span></td>
<td>N/A</td>
<td>N/A</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a proposal in open call</th>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a proposal</th>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a call</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a call</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a review</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> One's own</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Create a decision</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>Edit a decision</th>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-x-lg text-danger"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

<tr>
<th>View a decision</th>
<td><span class="bi-check-lg text-warning"></span> One's own, when allowed</td>
<td><span class="bi-check-lg text-warning"></span> Only chair</td>
<td><span class="bi-check-lg text-warning"></span> Any in call</td>
<td><span class="bi-check-lg text-success"></span></td>
<td><span class="bi-check-lg text-success"></span></td>
</tr>

</table>

## Account

In order to do any work in Anubis, a user must have an account.

Open calls are public, and can be viewed by anyone, including persons
who do not have an account.

A user can [register an account](/user/register). Depending on the
site policy, the account will be immediately enabled, or an
administrator will have to enable the account after inspection. An
email will be sent to the user once the account is enabled. It
contains information on how to set the password.

### User role

A user of the system must register an account, and each user must have
a valid email account to which emails with instructions on how to set
the password is sent.

Depending on the site configuration, user accounts may be
automatically enabled, or require the explicit enabling by the
administrator.

The administrator may register accounts, which do not have a valid
email address. This can be used for pseudo-user accounts which may be
useful in some scenarios.

The administrator may allow a user to create calls. A user who has
created a call becomes the administrator of it, and can deal with
nearly all aspects of it.

See [Instructions for users](/documentation/instructions-for-users).

### Staff role

A staff user can read most data in the Anubis system, but can edit only
certain data.

### Administrator role

An administrator is a user that has privileges to perform any action
that is available in the web interface of the Anubis system.

See [Instructions for administrators](/documentation/instructions-for-admins).

### Reviewer

A reviewer is a user account who has been designated as a reviewer in
a specific call by the administrator. A reviewer cannot have a
proposal of her own in that call.

A user that is a reviewer in one call, is not automatically a reviewer
in another call. This makes it possible for a user to be an ordinary
submitter of a proposal in one call, while being a reviewer in another
call.

See [Instructions for reviewers](/documentation/instructions-for-reviewers).

### Chair

A chair is a special kind of reviewer, who has the privilege to create
and delete review instances within the call. The chair can also view
the reviews of all reviewers in that call.

## Call

A call in the Anubis system is a representation of a a call for
proposals. It is the basis for all other entities in the Anubis
system.

A call has an identifier, a title, and a description. It may have
documents attached. It contains the descriptions and definitions for
proposals, reviews, decisions and grant dossiers.

A call is prepared and handled by a call owner, which is either an
administrator or an account which hase been given this privilege by
the administrator. The call owner sets up the
[input fields](/documentation/input-field-types) for the proposal, and
the reviews, the decision and grant dossier for each proposal.

A user with an account in the Anubis system  can create a
[proposal](/documentation/proposal) within an open call. The structure
of the proposal is determined by the call owner when setting up the
call.

A call has an **opens** date, from which it becomes visible to the
world. It has a **closes** date, which determines the last time a
proposal can be submitted in the call.

The **opens** date of a call defines when the call becomes publicly
available so that proposals can be created by users. The call cannot
be open unless this has been set.

After the **closes** date of a call, a user can no longer create, edit
or submit a proposal in it.

The input fields for proposals within a call should, of course, be
defined before the call is opened. However, it is possible to modify
an input field even when the call has been opened. This feature should
be used as little as possible since the users writing their proposals
may become confused when the their proposal form changes.

## Proposal

A proposal is created within an open call by a user, who must be
logged in to an Anubis [account](/documentation/account). Only one
proposal in each call can be created by any given user.

The user fills in the proposal [input fields](/documentation/input-field-types),
which are configured in the call by the call owner.

Some input fields may be optional, while some many be required. This is defined when
the call owner creates and edits the input fields for the proposals of the call.

An input field has an allowed type of input, such as text, integer, file, etc.

When all required input fields have been filled in with values of the
correct type, the user may submit the proposal. A proposal may be
un-submitted by the user while the call is open.

If the call has been closed, it is no longer possible to submit a
proposal, nor to edit it in any way. The proposal can still be viewed
by the user after the call has been closed.

An admin has additional privileges for handling proposals, see [Instructions
for administrators](/documentation/instruction-for-admins).

## Decision

The administrator or review chair can create a decision entity for
each proposal. The fields of the decision are configured in the call
by the call owner. Thus, a decision may contain more information for
the proposer than just the accept/reject decision.

The call owner or the chair of the call may edit and finalize the
decision.

The administrator may make the decision for each proposal viewable by
the respective submitter by setting an access flag in the
call.

Currently, no email is automatically sent by the Anubis system to the
submitter when the decision is finalized.

## Grant dossier

A grant dossier contains information about the grant which is the
result of positive decision for the proposal. It may contain
information about the grant and documents provided by the grant giver,
or by the grantee, for example grant conditions, budget, agreement,
and similar.

A grant dossier which has valid values in all required fields is
automatically set as complete.

A grant dossier is created by the administrator or staff, who also
configure the input fields in it. The proposal owner (which presumably
is the grant receiver) can view and edit it.

## Review

A review is an evaluation by a reviewer of a specific proposal. The
administrator sets up the review of the proposals in a call.

First, the review input fields are configured, in the same way as the
input fields for a proposal.

Second, the accounts of the persons who will review the proposals are
added as reviewers to the call.

Third, the administrator must also create the review objects (forms)
for each proposal for each reviewer. Thus, it is possible to assign a
subset of proposals to a reviewer, or all proposals, depending on the
policy for that call.

Reviewers cannot create their own review entities; this is done by the
administrator. A reviewer can only edit their reviews, not create or
delete them.

The review has a deadline, and the reviewers can edit their reviews
until that date. The reviews should be finalized to denote that no
more work is going to be done on the respective review.

Review instances have [input fields](/documentation/input-field-types)
defined by the administrator, similar to how a proposal is defined. All reviews
within a call have the same input fields.

## Input field types

The proposals of a call must be defined in terms of which data a proposer is
supposed to provide. This is configure by the call creator by defining the
input fields to be used, their instruction texts and their possible values.

The input fields are the means to store information in proposals,
reviews, decisions and grants. They have types which define what kind
of information they can store.

All input fields for proposals, etc, can be changed by the call owner,
even when the call has been published. This must be done with care,
since changing a field may invalidate a proposal, etc, that previously
was valid and complete, although the Anubis system should be able to
tolerate this.  The data for fields that are removed or modified may
become unreachable.

### Available input field types

- **Line**. One single line of text, such as a name or title.
- **Email**. One single email address.
- **Boolean**. A selection between Yes and No.
- **Select**. A choice among a set of text given values.
- **Integer**. A number that is a whole integer.
- **Float**. A number that may contain fractions.
- **Score**. A number in the range of integer values defined on setup.
- **Rank**. A number in the series 1, 2, 3,...
- **Text**. A multiline text which may use Markdown formatting.
- **Document**. An attached file.

### Common settings for all input field types

All input field types have a number of settings that can be set at creation
or modified later. These are:

- **Identifier**. The internal name of the field, which must be unique within
  the form. It must begin with a letter and continue with letters,
  numbers or underscores.

- **Title**. The name of the field as shown to the user.
  Defaults to the identifier capitalized.

- **Required**. Is a value required in this field for the form to be valid?

- **Staff edit**. Only the staff may edit the field. The user will see it.

- **Staff only**. Only the staff may edit and view the field.
  It is not visible to the user.

- **Banner**. The field will be shown in various tables.

- **Description**. The help text displayed for the field.
   May contain Markdown formatting.

### Line field

One single line of text, such as a name or title. May contain any text.

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.

### Email field

One single email address, which must look like a proper email
address. However, its actual validity is not checked.

### Boolean field

A selection between Yes and No. If it is not required, then also "No
value" will be allowed.

### Select field

A choice among a set of given text values.

- **Selection values**.  The values to let the user choose from. Give
  the values as text where each line is one value.

- **Multiple choice**. Is the user allowed to choose more than one value?

### Integer field

A number that is a whole integer.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.

### Float field

A number that may contain fractions, i.e. a decimal point.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.

### Score field

A number in the range of integer values defined on setup. The choice
of value is presented as a set of buttons, or optionally by input from
a slider.

- **Minimum**: The lower limit for the value given by the user.

- **Maximum**: The upper limit for the value given by the user.

### Rank field

A field of type rank is intended for reviews. The reviewer must assign
a value to the field of each of her reviews in a call such that the
values are unique and consecutive starting from 1, else an error will
be flagged.

A field set as banner will produce an extra column named "Ranking
factor" (F(x) below) which is computed from all values in finalized
reviews in that call. The formula is:

```
    A(i) = total number of ranked proposals for reviewer i
    R(x,i) = rank for proposal x by reviewer i

    F(x) = round(decimals(1, 10 * average(all reviewers( (A(i) - R(x, i) + 1) / A(i)) ))))
```

For a proposal which has been ranked 1 by all reviewers of it, this will produce
a ranking factor of 10, which is the maximum. If a reviewer has ranked it at,
say, 3, then the ranking factor will become slightly less than 10.

**NOTE**: This is currently implemented only for reviews; it is not
very meaningful for other entities.

### Text field

A multiline text which may use Markdown formatting.

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.

### Document field

 An attached file.

- **Extensions**. A list of allowed extensions for the attached file.
  A simple-minded mechanism to restrict the allowed types of files.

### Repeat field

This field allow the number of a set of input fields to depend on a
number that the user must input. For example, if the user has three
collaborators and the name, affiliation and email address of these
collaborators must be entered.

When the user inputs a number in a repeat field, the system brings up
that number of copies of the other fields that have been associated
with.

After having defined a repeat field, the other fields that should be
repeated need be associated with it. When creating a new field, there
will be a select list field to specify whether that field is repeated
by a previously defined repeat field.

**NOTE**: The repeat field is currently implemented only for grant dossiers.
