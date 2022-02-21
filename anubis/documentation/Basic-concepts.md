# Basic concepts

The basic concepts used in the Anubis system are described briefly
here.

## Call

A **call** in the Anubis system is a call for proposals. It contains a
description of the call, optionally with documents such as PDFs. It
is a container for proposals, reviews and decisions.

The admin creates a call. The admin also sets up the input fields for
the proposal, the reviews and the decision for each proposal.

The **opens** date of a call defines when the call becomes publicly
available so that proposals can be created by users. The call cannot
be open unless this has been set.

After the **closes** date of a call, if defined, a user can no longer
create or submit a proposal in it. A call that does not have a
**closes** date is open indefinitely.

## Proposal

A proposal is created within an open call by a user. Only one proposal
in each call can be created by any given user. The user fills in the
proposal input fields, which are defined by the call.

When all required input fields have been filled in, the user may
submit the proposal. If the call has been closed, it is no longer
possible to submit a proposal.

## Review

A review is an evaluation by a reviewer of a specific proposal. Review
instance are created by the admin. A reviewer can only edit her
review, not create or delete it.

The admin may create reviews of all proposals for all reviewers, or of
only some proposals for each reviewer, according to the policy of the
call.

Review instances have input fields defined by the admin, similar to
how a proposal is defined. All reviews within a call have the same
input fields.

## Decision

A decision is created by the admin for each proposal. The admin or the
chair (a special reviewer) may edit and finalize the decision.

The admin may make the decision for each proposal viewable by the
respective submitter by setting an access flag in the call. Currently,
no email is automatically sent by the system to the submitter when
this is done.

## Grant dossier

A grant dossier contains information about the grant which is the result of
positive decision for the proposal. It may contain information about the grant
and documents provided by the grant giver, or by the grantee, for example grant
conditions, budget, agreement, and similar.

A grant dossier which has valid values in all required fields is set as complete.

A grant dossier is created by the admin or staff. The proposal owner (which
presumably is the grant receiver) can view and edit it.

## User

A user of the system must register an account, and each user must have
a valid email account to which emails with instructions on how to set
the password is sent.

Depending on the site configuration, user accounts may be
automatically enabled, or require the explicit enabling by the admin.

The admin may register accounts, which do not have a valid email
address. This can be used for pseudo-user accounts which may be useful
in some scenarios.

The admin may allow a user to create calls. A user who has created a
call becomes the administrator of it, and can deal with nearly all
aspects of it.

## Reviewer

A reviewer is a user account who has been designated as a reviewer in
a specific call by the admin. A reviewer is not allowed to have a
proposal of her own in that call.

A user that is a reviewer in one call, is not automatically a reviewer
in any other call. This makes it possible for a user to be an ordinary
submitter of a proposal in one call, while being a reviewer in another
call.

## Chair

A chair is a special kind of reviewer, who has the privilege to create
and delete review instances within the call. The chair can also view
the reviews of all reviewers in that call.

## Admin

An admin is a user that has privileges to perform any action in the
web interface of the Anubis system.
