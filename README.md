# Anubis

Proposal review handling system.

## Entities

- User
  - Required: username, email.
  - Configurable: affiliation, postal address, gender, birth date, title.
  - Login required, password and reset code sent by email.
  - Roles:
    - Admin: can do everything.
    - User: ordinary users.
    - Reviewer = a user designated as reviewer for a call by admin.
  - Anonymity
    - Users are anonymous vs other users (except admin, who can see all)
  
- Call
  - = Call for proposals.
  - Container of proposals.
  - Unique prefix (identifier) letters, digits, underscore
  - With info, documents, instructions, etc, for the user (applicant).
  - Configurable fields to be filled in for a proposal.
  - Handled by admin.
  - Date opened
  - Date closed (time, local)
  - Status determined by dates.
  
- Proposal
  - = Application = submission; the proposal to be reviewed.
  - Belongs to one and only one call, and one and only one user.
  - Identifier: {prefix}:001
  - Information fields; defined in the call.
  - Attached documents (project description, CV,...)
  - Made by user.
  - Submitted or not submitted.
  - Reviewer relation: TODO
    - Interest
    - Conflict-of-interest
    - Assignment
    - Responsibility
  
- Review
  - A reviewer's comments and assessment of a proposal.
  - Criteria = reviewer's assessment fields; defined in the call.
  - Owned by reviewer.

- Overview
  - Aggregated reviews from reviewers.
  - Tables of various proposal properties
  - Tables of various assessment properties
  - Aggregates of properties

## Built on

Python3, Flask, CouchDB server, CouchDB2 (Python module),
Bootstrap, jQuery, DataTables.

## Commercial systems

- Evalato
- Apply Surveymonkey
- OpenWater
- AwardForce

The icon "Feather of Ma'at" made by
[freepik from flaticon.com](https://www.flaticon.com/authors/freepik).
