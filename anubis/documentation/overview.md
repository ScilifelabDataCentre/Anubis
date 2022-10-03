---
title: Overview
level: 0
ordinal: 0
---

Anubis is a system to handle calls, proposal submission and reviews.

It is based on the following entities:

### Call

[A call](/documentation/call) is a call for proposals. In the Anubis
system, it is a container for **proposals**, **reviews**, **decisions** and **grants**.

The input fields of all other entities are created and defined within
the call by the call owner.

### Proposal

[A proposal](/documentation/proposal) can be created and written by
anyone who has an account in the Anubis system.  A proposal always belongs
to one and only one specific call.

The proposal must be submitted by the user before the **closes** date of the call.

The input fields for proposals within a call should, of course, be
defined before the call is opened. However, it is possible to modify
an input field even when the call has been opened, but this feature
should be used as little as possible.

### Review

[The reviews](/documentation/review) of proposal within a call is set
up by the administrator. This entails defining what information the
reviewers must provide, including scores or rank. The administrator must then
create the actual review forms for each reviewer and proposal.

The reviews are visible only the administrator, the owner of the call,
and optionally by the other reviewers in the call.

### Decision

The purpose of [the decision](/documentation/decision) entity is to
document what the result of the review of a proposal is. Creating a
decision does not send any email to the proposal author. This has to
be done outside of the system.

### Grant dossier

[A grant dossier](/documentation/grant-dossier) is a means for the
researcher and staff to share information, such as documents, about a
successful proposal.

### Input field types

Most of the above entities are configured for each call to provide a
set of input fields, to be filled in by the user, reviewer or
staff. There are a number of [input field types](/documenation/input-field-types)
that may be used.

### Account

[An account](/documentation/account) is the representation of a user
in the Anubis system. A user must have an account to be able to write
a proposal. An account may have different roles, which gives different
sets of privileges.

### Privileges

Different user roles have different sets of [privileges](/documentation/privileges),
which determine what they are allowed to do within the Anubis system.
