# Anubis documentation

Anubis is a web-based system to handle calls for proposals, proposal submission,
reviews, decisions and grant dossiers. It allows:

- The creation of calls, which includes defining what information a
  proposals should contain.
- The publication of calls, with handling of open/close dates.
- Proposals can be created, edited and submitted by users based on
  open calls.
- To prepare and submit a proposal, a person must must create an
  account in the Anubis system.
- Accounts with the role admin (or 'admin', for short) have the
  privileges to use all features in the system, including inspecting
  and handling calls, proposals, reviews, decisions and grants.
- Specific accounts can be given the privilege of creating calls by
  the admin.  They will be owners of the calls they create.
- A call owner designates which accounts should be reviewers of the
  proposals in a call.
- The call owner or admin records the decisions that the reviewers have made.
- Grants can have information and documents added by grant receivers and/or
  the Anubis site staff.


# Entities


## Call

A call in the Anubis system is a representation of a call for
proposals. It is the primary entity in the Anubis system.

A call has a unique identifier, a title, description, optional files
attached, and open and close dates.  It is the container for its
proposals, reviews, decisions and grants. The input fields of these
entities are created and defined within their call.

#### Open call

A call is open when its **opens** date has passed, but its **closes** date has not.
A call that does not have both of these values set is unpublished, and
is not visible to ordinary user. This means that there can be no open calls
without a closing date.

When a call is open, it is visible to the world on the
[Anubis home page](/).

The opening and closing of a call is automatically done by the Anubis system
based on the date and time as given by the server the system is running on. The
admin does not have to do anything once the date and time for opens
and closes have been set.

#### Call owner

A call is prepared and handled by the admin or a user account that is
an account that has been given this privilege explicity by the admin.
The account creating the call is the call owner.

The call contains the [input fields](/documentation#input-field-types)
that the call owner sets up for the proposals, the reviews, decisions
and grant dossiers in the call.

Before the call is opened, the call owner should set up at least the
input fields for the proposals. However, it is technically possible to
modify the proposal fields after the call has been opened, but this
is strongly discouraged, since it will likely cause confusion for the users.

The input fields for the reviews, decisions and grant dossiers can be
set up later. The mechanism is the basically same as for the proposal
input fields.

The call owner can choose to use or not use the Anubis system for
reviews, decisions and grant dossiers.


## Proposal

A proposal can be created only within an open call. A user has to
create and log in to an account in order to create, write and submit a
proposal. Only one proposal can be created by a user within one call.

The proposal must be submitted by the user before the **closes** date of
the call.  A user will be alerted to the presence of unsubmitted
proposals in the top menu of the Anubis pages.

A proposal is visible only to its creator (the proposal owner), the
admin, and those accounts that the proposal owner has explicitly given
access to.

An admin has additional privileges for handling proposals.
See [Instructions for admins](/documentation#instructions-for-admins).

#### Proposal input fields

The proposals of a call must be defined in terms of which data the
creator of a proposal is supposed to provide. This is configure by the
call creator by defining the [input fields](/documentation#input-field-types)
to be used, their instruction texts and their possible values.

An input field has an allowed type of input, such as text, integer,
file, etc. There may be additional constraints on the values allowed
in an input field.

Some input fields may be set as optional by the call owner, while some
many be set as required, meaning that a value must provided by the
user.

#### Submitting proposal

When all required input fields in a proposal have been filled in with
values of the correct type, the user may submit the proposal. A
proposal may be un-submitted by the user while the call is open. This may
be useful if errors need to be corrected.

If the call has been closed, it is no longer possible to submit a
proposal, nor to edit it in any way. The proposal can still be viewed
by the user after the call has been closed.


## Review

A review is an evaluation by a reviewer of a specific proposal. The
admin sets up the review of the proposals in a call.

The reviews of proposals within a call are set up by the call
owner. This entails defining what input fields a review should
contain, including scores, rank or comments.

#### Creating reviews

The call owner must explicitly set which accounts should be reviewers
for the proposals in a call.

In addition, the call owner must create the actual review form for
each reviewer and proposal. This has to be done manually via the web
interface. A reviewer can edit their reviews, but she cannot create or
delete the reviews.

A date and time for when reviews are due is set by the call owner.

#### Review visibility

The reviews are visible to the admin, the call owner, and optionally
by the other reviewers in the call.

At no stage can the proposal creator view the reviews of her proposal.

#### Reviewer actions

The reviewers typically download the proposals and their files via a
link that is visible to them in the call page. The reviewers should
then fill in the review form and set to **finalized** when done. This
makes it clear to the call owner that they have finished the review.

A reviewer will be alerted to the presence of unfinalized reviews in
the top menu of the Anubis pages.


## Decision

The purpose of the decision entity is to document what the final
result of the review of a proposal is.

The call owner or review chair can create a decision entity for each
proposal. The fields of the decision are configured in the call by the
call owner. A decision may contain more information just the
accept/reject decision.

Creating a decision does not send any email to the proposal
author. This has to be done outside of the Anubis system.

Finalizing a decision does not automatically let the proposal creator view it;
in addition, the call owner has to set the flag for this in the call.


## Grant dossier

A grant dossier is a means for the grant receiver and staff to share
information and/or documents about a successful proposal. This could
information about other grant participants, the names and email
addresses of the economists, documents relating to grant conditions,
budget, agreement, and similar.

A grant dossier which has valid values in all required fields is
automatically set as complete.

It is possible for the admin to add new input fields to existing grant
dossiers. However, a grant dossier is not automatically set as
incomplete. The admin has to go into edit mode for each grant dossier
and save it; only at save time are the current values of the grant
dossier checked against the requirements of the input fields as
defined for it in the call.

A grant dossier is created by the admin or staff, who also configure
the input fields in it. The proposal owner (which presumably is the
grant receiver) can view and edit it.

A grant dossier can be locked by the admin, which makes it impossible
for the grant receiver to further edit it. It can also be unlocked by the
admin.


## User account

A user account is the representation of a user in the Anubis system.
In order to do any work in Anubis, a user must have an account.

A user can [register an account](/user/register). Depending on the
site policy, the account will be immediately enabled, or an
admin will have to enable the account after inspection. An
email will be sent to the user once the account is enabled. It
contains information on how to set the password.

A user has an identifier that is unique within the Anubis
instance. The email address must also be unique within the Anubis
instance.

Depending on the site configuration, user accounts may be
automatically enabled, or require the explicit enabling by the
admin.

The admin may register accounts, which do not have a valid
email address. This can be used for pseudo-user accounts which may be
useful in some scenarios.

The admin may set a user to be able to create calls. A user who has
created a call becomes the owner of it, and can deal with nearly all
aspects of it.


# Roles and privileges

Anubis uses a role-based privileges system which determines what operations
are allowed for an account.

A user who has not logged in can view the open calls in Anubis, but not much else.

In order to create and edit anything in Anubis, a user account is
required.


## User roles

There are a few different roles for user account, which give different
levels of privileges in the web interface.

A user account has one and only one role. However, the admin can change
the role of a user.

1. Role **admin**: This role can do use all features of the web interface.
   which includes viewing and changing user accounts, and configuring
   certain aspects of the Anubis instance. It is recommended to have only a
   few admin accounts for an Anubis instance.
2. Role **staff**: This role allows viewing user accounts, proposals and
   the other entities, with some limited editing privileges.
3. Role **user**: The default role, which allows creating, editing and
   submitting proposals in open calls. She can view all her current
   and previous proposals, and view decisions and grant pages, if any,
   for each specific proposal.


### Call creator

An account having the role **user** may be allowed to create
calls. This is done explicitly by the admin for that specific
account. A user that has created a call has extended privileges for
that call.


### Reviewer

A reviewer is a user account who has been explicitly set as a reviewer in
a specific call by the admin. This is technically not a role.

A reviewer may view the submitted proposals of the call and write reviews for them.

A reviewer cannot have a proposal of her own in that call.

A user that is a reviewer in one call, is not automatically a reviewer
in another call. This makes it possible for a user to be an ordinary
submitter of a proposal in one call, while being a reviewer in another
call.


### Chair

A chair is a special kind of reviewer, who has the privilege to create
and delete review instances within the call, among other actions. The
chair can also view the reviews of all reviewers in that call.

The chair may also create the decision entities for the proposals and edit them.


## Privileges

The privileges in the web interface are determined by the role of the logged-in
user account.

Accounts with the user role can be given additional privileges, which only
relate to specific calls:

- A user can be set as a reviewer in a call, which gives more
  privileges for that call.
- In addition, a reviewer can be set as chair for that review. This
  gives further privileges.
- A user can be allowed to create calls. If the user then creates a call,
  she has more privileges for that call.

The table below summarizes the privileges for most actions. Note that
some exceptions are omitted, such as a user explicitly allowing
another user account to view and/or edit her proposal.

<table class="table">

<thead class="sticky">
<tr>
<th colspan="2"></th>
<th>User</th>
<th>User (reviewer)</th>
<th>User (call creator)</th>
<th>Staff</th>
<th>Admin</th>
</tr>
</thead>

<tbody>
<tr>
<th rowspan="4">Call</th>
<th>Create</th>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Configurable</td>
<td>Yes</td>
</tr>

<tr>
<th>View</th>
<td>Yes, if published</td>
<td>Yes, if published</td>
<td>One's own</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Edit</th>
<td>No</td>
<td>No</td>
<td>One's own</td>
<td>Configurable; one's own</td>
<td>Yes</td>
</tr>

<tr>
<th>Delete</th>
<td>No</td>
<td>No</td>
<td>One's own, if no proposals</td>
<td>No</td>
<td>Yes, if no proposals</td>
</tr>

<tr>
<th rowspan="6">Proposal</th>
<th>Create</th>
<td>Yes, while call open</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>View</th>
<td>One's own</td>
<td>Any in the call to be reviewed</td>
<td>Any in one's own call</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Edit</th>
<td>One's own, while not submitted</td>
<td>No</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Delete</th>
<td>One's own, while not submitted</td>
<td>No</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Transfer ownership</th>
<td>No</td>
<td>No</td>
<td>Yes, if one's own call</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Submit</th>
<td>One's own, while call open</td>
<td>No</td>
<td>Any in one's own call</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th rowspan="6">Review</th>
<th>Create</th>
<td>No</td>
<td>Chair if call setting</td>
<td>In one's own call</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>View</th>
<td>No</td>
<td>One's own, or all if call setting; chair all</td>
<td>Any in one's own</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Edit</th>
<td>No</td>
<td>One's own</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Finalize</th>
<td>No</td>
<td>One's own</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Unfinalize</th>
<td>No</td>
<td>One's own, before due date</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Delete</th>
<td>No</td>
<td>No</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th rowspan="4">Decision</th>
<th>Create</th>
<td>No</td>
<td>Only chair</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>View</th>
<td>One's own, depends on call setting</td>
<td>Only chair</td>
<td>Any in one's own call</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Edit</th>
<td>No</td>
<td>Only chair</td>
<td>Any in one's own call</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th>Delete</th>
<td>No</td>
<td>No</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
</tr>

<tr>
<th rowspan="6">Grant dossier</th>
<th>Create</th>
<td>No</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>View</th>
<td>One's own</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Edit</th>
<td>One's own, if not locked</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Change access</th>
<td>One's own</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Lock</th>
<td>No</td>
<td>No</td>
<td>No</td>
<td>Yes</td>
<td>Yes</td>
</tr>

<tr>
<th>Delete</th>
<td>No</td>
<td>No</td>
<td>No</td>
<td>No</td>
<td>Yes, if not locked</td>
</tr>

</tbody>
</table>


# Instructions

In this section are described typical operations for users in different roles.


## Instructions for users


### Create a user account

- In order to create a proposal in a call, a user must have an account
  in the system.
- To create an account in the Anubis system, go to the page
  [Register a user account](/user/register) and follow the
  instructions.
- When a new user account has been enabled, you will receive an email
  describing how to set your password.
- Once you have set your password, you may create a proposal from an open call.


### Create a proposal

- Go to the page of the open call. All open calls are displayed on the
  [home page](/), so use the links there.
- Unless you have already created a proposal in the call, there is
  a button **Create proposal** in the call page allowing you to do so.
- Fill in the values for the input fields.
- You may save the unfinished proposal and return to **editing** it later.
- Once the required fields of the proposal have been filled in correctly,
  you may **submit** it.
- A proposal that has been submitted can no longer be edited.
- However, as long as the call is open, you may un-submit your
  proposal if you wish to edit it further.
- A proposal that has not been submitted may be deleted by you.
- Once the call's deadline for submission has been passed, the user
  may no longer submit a proposal.
- **Be sure to submit your proposal before the deadline!**


### Display your proposals

- The number of your unsubmitted proposals is displayed on a yellow
  background in the top menu. If there is no such yellow marker, your
  proposals, if any, have all been submitted.
- To list all your proposals, click the item **My proposals** in the
  top menu. If there is no such item, then you have no proposals.


## Instructions for reviewers

The number of your unfinalized reviews is displayed on a yellow
background in the top menu. If there is no such yellow marker, your
reviews are done.


### How to get the proposals

- As a reviewer, you have access to all submitted proposals in the call.
- Depending on the policy for the call, you should read all or only
  some of the proposals.
- To download all proposals and their attached files, go to the call page.
  In the right-hand upper corner, there are two small black buttons:
  1. **Submitted proposals Excel file**, which allows you to download
     the information in all submitted proposals in Excel format. This
     does not contain the files attached to proposals, if any.
  2. **Submitted proposals zip file**, which contains the above Excel
     file and all files attached to the proposals. The naming of
     the files indicates which one belongs to which proposal.
- It is also possible to browse the proposals in a list display by
  clicking the blue button by the item **All proposals** on the call
  page.


### How to fill in your reviews

1. Click on the item **My reviews** in the top menu.
   - The list of all reviews for your user account are shown in a table,
     which can be sorted by any column.
   - **Note** that the table may have more than one page, depending on
     the number of proposals. Use the page selector at the bottom right of
     the table.
2. Click on the link **Review** to view the review of the proposal on
   that line in the table.
3. Edit the review.
4. Click **Finalize** to indicate that you are done with the review.
   - Until the **due** date for reviews in the call, you may
     **Unfinalize** a review if you wish to resume editing it.
5. To view the proposal of the review, click the link to the proposal
   in the title. (Tip: do right-click and "Open in new tab".)
6. Before the **due** date, ensure that all your reviews have been
   finalized.


### Basic information about reviewers

- A user account is set as a reviewer for a specific call by the admin
  or the call creator.
- The admin or call creator also creates the review instances for the
  proposals for each reviewer. A reviewer cannot create their own
  review instances, only edit existing ones.
- Depending on the policy for the call, a reviewer may have to write a
  review for all or only some proposals. The admin or call creator
  handles this by creating those review instances that the reviewer
  should fill in.
- The content (input fields) of the reviews are set for the call by the admin
  or call creator.
- The reviews of a call have a **due** date, before which all reviews must
  have been finalized by the reviewers.
- There may be a chair designated for a call. This is a reviewer
  heading the reviewer group. He or she has additional privileges, if
  so set by the admin.


### Reviewer privileges

- The reviewer may view all proposals in the call.
- The reviewer can edit her review instances.
- The reviewers cannot create or delete review instances.
- The chair, if any, of a call may create review instances, if so set
  by the admin or call creator.
- The chair, if any, may view all reviews, if so set by the admin or call creator.
- A reviewer may view finalized reviews by other reviewers only if the
  admin or call creator allows it for the call.


## Instructions for staff

Since staff can view most data in Anubis, but have only limited editing
privileges, there are no special instructions.


## Instructions for admins

The admin is a user account which has full privileges for the Anubis
site. She may perform all operations that are possible to do via the
web interface.


### User account handling

- The admin may register user accounts.
- The admin may edit, enable or disable user accounts.
- An admin may set other user accounts to be admin.
- An admin may enable an ordinary user account to create calls.


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


## How to create a call

A call can be created by
- An admin account.
- A staff account, if so set by the admin in the [call configuration page](/admin/call_configuration)
- An ordinary user account which an admin has explicitly set to be able to create calls.

There are two ways of creating a call: From scratch, or by cloning an existing call.

### Alt 1: Create a call from scratch

1. In the top pull-down menu **Calls**, use the item **Create a call**.
2. Provide the identifier for the new call. When the call has been opened and any
   proposals created, this cannot be changed, so choose wisely.
3. Provide the title for the new call. This can be edited later.
4. Click **Create**.
5 Edit the call; see the section after the next.

### Alt 2: Create a call by cloning

1. Find an existing call to clone from. Since it's the creation and editing of
   input fields for proposals and reviews that requires most work, use a call
   that has similar input fields.
2. Click the button **Clone**.
3. Provide the identifier for the new call. When the call has been opened and any
   proposals created, this cannot be changed, so choose wisely.
4. Provide the title for the new call. This can be edited later.
5. Click **Create**.
6. Edit the call; see next section.

### Edit the call metadata

- The field "Description" is intended to give the potential proposal writer an
  explanation of what the call is about. It can use
  [Markdown](https://www.markdownguide.org/basic-syntax/) formatting.
- The field "Home page description", if provided, is used on the home page of the
  Anubis web service. The description there has to be short in order not to crowd
  out the other open calls. It should be used then the "Description" field (see above)
  is too long.
- Field "Labels" is to assist filtering when using the API to fetch call information.
  It is optional.
- The field "Opens" determines when the call is automatically opened for
  the applicants to create their proposals. It is a date-and-time field,
  e.g. "2023-06-12 10:00". The date must be an ISO-format date,
  i.e. year-month-day. The time is in the 24 hour clock, and in the
  timezone set for the Anubis web server.
- **NOTE**: If the date is supposed to denote midnight in the evening of 2023-06-12,
  then the time must be given as **23:59**. If one specifies 00:00, then this
  means the morning of that day.
- **NOTE**: This field has to be set for a call to be published.
- The field **Closes** determines the deadline for creating and submitting a
  proposal in a call. When set, the Anubis system automatically closes the call
  on the given date and time. The format is the same as for the "Opens" field.
- **NOTE**: This field has to be set for a call to be published.
- The field **Reviews due** is for the deadline for reviews. This is a "soft" deadline;
  reviews can still be submitted after it. This field is optional.
- The "Privileges" checkboxes allows selecting certain additional privileges for
  the call, if required.

### Edit the input fields

The input fields for the **proposals**, **reviews**, **decisions** and **grants**
are all defined in the call.

- To edit the input fields of an entity, click one of the buttons
  **Edit {entity} fields**.
- The input fields should be created before allowing users
  to create and edit the entity.
- It is possible to modify the fields later, but it may invalidate an existing
  entity by creating a mismatch between the data of a field and its definition.
- The input fields have a type which is determined when it is
  created. It is not possible to change a field type; one has to delete
  that field and create it again.
- It is possible, but cumbersome, to change the order of fields. It is a good idea
  to plan the order the fields before actually creating them.
- Existing fields can be edited for anything except their identifier and type.
- An existing field can be delete. All data for it in an entity (proposal, etc) will
  then be irretrievably list.

### Test the proposal in a call

- As admin, one may test the proposal defined in a call by creating it before the
  call has been published.
- After having edited and viewed the test proposal, one should delete it.
- One should also click the button **Reset proposals counter** to begin the numbering
  of proposals created starting from 1 again.

# Input field types

The input fields are the means to store information in proposals,
reviews, decisions and grants. They have types which define what kind
of information they can store.

All input fields for proposals, etc, can be changed by the call owner,
even when the call has been published. This must be done with care,
since changing a field may invalidate a proposal, etc, that previously
was valid and complete.

The Anubis system does not re-check the validity of a proposal, etc,
when the input field definitions are modified. This is detected only
when the proposal, etc, is edited and saved. This means that a
proposal, etc, which looks fine to the user may, in fact, be invalid
because the call owner has changed the input field definitions. This
should be avoided. In addition, the data for fields whose definition
has been removed will disappear.


## Available input field types

- **Line**. One single line of text, such as a name or title.
- **Email**. One single email address.
- **Boolean**. A selection between Yes and No.
- **Select**. A choice among a set of text given values.
- **Integer**. A number that is a whole integer.
- **Float**. A number that may contain fractions.
- **Score**. A number in the range of integer values defined on setup.
- **Rank**. A number in the series 1, 2, 3,...
- **Text**. A multiline text which may use
  [Markdown formatting](https://www.markdownguide.org/basic-syntax/).
- **Document**. An attached file.


## Input field common settings

All input field types have a number of settings, most of which may be edited
after the field has been created. These are:

- **Identifier**. The internal name of the field, which must be unique within
  the form. It must begin with a letter and continue with letters,
  numbers or underscores. This cannot be changed once set.

- **Title**. The name of the field as shown to the user.
  Defaults to the identifier capitalized.

- **Required**. Is a value required in this field for the form to be valid?

- **Staff edit**. Only the staff may edit the field. The user will see it.

- **Staff only**. Only the staff may edit and view the field.
  It is not visible to the user.

- **Banner**. The field will be shown in various tables.

- **Description**. The help text displayed for the field.
  May contain [Markdown formatting](https://www.markdownguide.org/basic-syntax/).


## Line field

One single line of text, such as a name or title. May contain any text.

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.


## Email field

One single email address, which must look like a proper email
address. However, its actual validity is not checked.


## Boolean field

A selection between Yes and No. If a value is not required, then also "No
value" will be allowed.


## Select field

A choice among a set of given text values.

- **Selection values**.  The values to let the user choose from. Give
  the values as text where each line is one value.

- **Multiple choice**. Is the user allowed to choose more than one value?


## Integer field

A number that is a whole integer.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.


## Float field

A number that may contain fractions, i.e. a decimal point.

- **Minimum**: An optional lower limit for the value given by the user.

- **Maximum**: An optional upper limit for the value given by the user.


## Score field

A number in the range of integer values defined on setup. The choice
of value is presented as a set of buttons, or optionally by input from
a slider.

- **Minimum**: The lower limit for the value given by the user.

- **Maximum**: The upper limit for the value given by the user.


## Rank field

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

    F(x) = 10 * average(all reviewers( (A(i) - R(x, i) + 1) / A(i)) )
```

For a proposal which has been ranked 1 by all reviewers of it, this will produce
a ranking factor of 10, which is the maximum. If a reviewer has ranked it at,
say, 3, then the ranking factor will become slightly less than 10. The number is
rounded to one decimal place.

**NOTE**: This is currently implemented only for reviews; it is not
very meaningful for other entities.


## Text field

A multiline text which may use
[Markdown formatting](https://www.markdownguide.org/basic-syntax/).

- **Maxlength**. The maximum number of characters allowed in the
  field, blanks included.


## Document field

 An attached file.

- **Extensions**. A list of allowed extensions for the attached file.
  A simple-minded mechanism to restrict the allowed types of files.


## Repeat field

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


# Installation

Installation instructions are available at the
[GitHub page for Anubis](https://github.com/pekrau/Anubis).


# Software design

The implementation of Anubis is based on the following design decisions:

- The back-end is written in Python using [Flask](https://pypi.org/project/Flask/ "!").
  - The back-end generates HTML for display using [Jinja2](https://pypi.org/project/Jinja2/ "!").
  - The front-end uses [Bootstrap](https://getbootstrap.com/docs/4.6/getting-started/introduction/ "!").
- The back-end uses the No-SQL database  [CouchDB](https://couchdb.apache.org/ "!").
  - Each entity instance is stored in one document in the CouchDB database.
  - The entities are in most cases identified internally by a IUID
    (Instance-unique identifier) which is a UUID4 value.
  - The entities contain pointers to each other using the IUIDs.
  - The CouchDB indexes ("designs") are vital for the computational efficiency
    of the system.
- There is a command-line interface (CLI) tool for certain operations,
  such as creating and loading backup dumps.
