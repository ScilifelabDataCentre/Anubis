---
title: Overview
level: 0
ordinal: 0
---

Anubis is a system to handle calls, proposal submission and reviews.

It is based on the following types of entities:

### Call

A call is the base for all other entities in Anubis. It contains the
descriptions and definitions for proposals, reviews, and more. It can
be prepared by the system administrator or accounts which have been
given this privilege by the administrator.

A call has an open date, from which it becomes visible to the
world. It has a closed date, which determines the last time a proposal
can be submitted in the call.

### Proposal

A proposal is always made in the context of a specific call. The input
fields in the proposal are defined in the call entity by the call
creator (usually an administrator).

In order to create, edit and submit a proposal, one must have an
account in the Anubis system. One account can create at most one
proposal in a call.

A proposal can be edited until the closing date for the call. It must
be submitted before the closing date. It can still be viewed by the
submiter after the closing date.

#### Review

The administrator sets up the review by setting which accounts are
reviewers in a call, and then creating review entities for each
reviewer. Thus, it is possible to assign a subset of proposals to a
reviewer, or all proposals, depending on the policy for that call.

Reviewers cannot create their own review entities; this is done by the administrator.

The review has a deadline, and the reviewers can edit their reviews
until that date. The reviews should be finalized to denote that no
more work is going to be done on the respective review.

#### Decision

The administrator or review chair can create a decision entity for each proposal. The fields of the decision are defined by the administrator in the call. Thus, a decision may contain more information for the proposer than just the accept/reject decision.

#### Grant dossier

A proposal that has been accepted can be assigned a grant dossier, the
purpose of which is to allow the proposer to input further information
regarding e.g. the payment of grant resources, or reports, or similar.

The fields of the grant dossier is defined in the call by the administrator.

#### Modification of input field definitions

All input fields can be changed by the administrator, even when the
call has been published. This must be done with care, since changing a
field may invalidate e.g. a proposal that previously was valid and
complete.
