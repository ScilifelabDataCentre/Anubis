Basic concepts
==============

The basic concepts used in the Anubis system are described briefly
here.

Call
----

A call in the Anubis system is a call for proposals. It contains a
description of the call, optionally with documents such as PDFs. It
functions as the container for the proposals, the reviews and the
decisions in it.

The admin creates a call, and sets up the input fields for the
proposal, the reviews and the decision for each proposal.

A call has an **opens** date, which defines when the call becomes
publicly available so that proposals can be created by users.

The call has a **closes** date, after which is not possible for a user
to create a proposal or to submit it.

Proposal
--------

A proposal is created within an open call by a user. Only one proposal
in each call can be created by a user. The user fills in the proposal
input fields, which are defined by the admin.

When all required input fields have been filled in, the user may
submit the proposal. Note that the call must still be open for a
proposal within in to be submitted!

Review
------

A review is an evaluation by a reviewer of a specific proposal. Review
instance are created by the admin for the reviewers in a call.

The admin may create reviews of all proposals for all reviewers, or
of only some proposals for each reviewer, according to the policy of the call.

Review instances have input fields defined by the admin, similar to
how a proposal is defined.

Decision
--------

A decision is created by the admin for each proposal. The admin or the chair
(a special reviewer) may edit and finalize the decision.

The admin may make the decision for each proposal viewable by the
respective submitter by setting an access flag in the call. Currently,
no email is automatically sent by the system to the submitter when
this is done.

User
----

User of the system must register an account, and each user must have a valid
email account to which emails with instructions on how to set the password
is sent.

Depending on the site configuration, user accounts may be
automatically enabled, or require the explicit enabling by the admin.

The admin may register accounts, which do not have a valid email address. This
can be used for pseudo-user accounts which may be useful in some scenarios.

Reviewer
--------

A reviewer is a user account which has been designated as a reviewer in
a specific call by the admin. A reviewer is not allowed to have a proposal
of her own in that call.

A user that is a reviewer in one call, is not automatically a reviewer in any
other call. This makes it possible for a user to be an ordinary submitter of
a proposal in one call, while being a reviewer in another call.

Chair
-----

A chair is a special kind of reviewer, which has the privilege to create
and delete review instances within the call. The chair can also view
the reviews of all reviewers in that call.

Admin
-----

An admin is a user that has all privileges to perform the action allowed
by the web interface of the Anubis system.
