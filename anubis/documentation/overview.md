---
title: Overview
level: 0
ordinal: 0
---

Anubis is a system to handle calls, proposal submission and
reviews. It is based on the following entities:

### Call

[A call](/documentation/call) is a call for proposals. It is a
container for **proposals**, **reviews**, **decisions** and
**grants**.  The input fields of all other entities are created and
defined within the call.

### Proposal

[A proposal](/documentation/proposal) can be created within an open
call.  A user has to create an account in order to create and write a
proposal.  The proposal must be submitted by the user before the
**closes** date of the call.

### Review

[The reviews](/documentation/review) of proposal within a call are set
up by the administrator. This entails defining what information the
reviewers must provide, including scores, rank or comments. The
administrator must then create the actual review form for each
reviewer and proposal.

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

### Account

[An account](/documentation/account) is the representation of a user
in the Anubis system. A user must have an account to be able to write
a proposal. An account may have different roles, which gives different
sets of privileges.
