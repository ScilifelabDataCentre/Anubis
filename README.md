# Anubis

Proposal submission and review handling system.

See [install/README.md](install/README.md) for information on how to install
this system.

## Entities

- User
  - Required: username
  - Email required for non-dummy accounts.
  - Configurable: affiliation, postal address, gender, birth date, title.
  - Login required, password and reset code sent by email.
  - Roles:
    - Admin: can do everything.
    - Staff: may view everything, but change very little.
    - User: ordinary users; a user may be allowed to create calls.
    - Reviewer = a user designated as reviewer for a call by admin.
    - Chair = reviewer with some additional privileges.
  
- Call
  - = Call for proposals.
  - Unique prefix (identifier) letters, digits, underscore
  - With info, documents, instructions, etc, for the user (applicant).
  - Defines proposal fields, review fields, and access configuration.
  - Handled by admin, or by a user that has been allowed to create calls.
  - Admin sets the reviewers and chairs of a call.
  - Date opens.
  - Date closes (time, local).
  - Date reviews due.
  - Status is determined by dates.
  
- Proposal
  - = Application = submission; the proposal to be reviewed.
  - Belongs to one and only one call, and one and only one user.
  - One user may have at most one proposal within a call.
  - Identifier: {prefix}:001
  - Fields; defined in the call.
  - Attached documents (project description, CV,...)
  - Made by user, ownership may be transferred to another user.
  - Submitted or not submitted.
  
- Review
  - A reviewer's comments and scores for a proposal.
  - A review is created by the admin (or chair) for a given
    submitted proposal and a given reviewer.
  - Fields; defined in the call.
  - Finalized or unfinalized.  

- Lists
  - All proposals in a call (also Excel)
  - All reviews for proposals in a call (also Excel)
  - All reviews for a proposal (also Excel)
  - All reviews from a reviewer in a call (also Excel)

## Workflow

There is no strictly defined workflow, but rather some assumptions implicit
in the system design.

- A call is opened when its opens date is defined, and has passed.
- It is not possible to create a proposal in a non-opened call.
- A call is closed when its closes date is defined, and has passed.
- It is not possible to create or submit a proposal in a closed call.
- Reviews are finalizable until the reviews-due date set for the call.

## Built on

Python3, Flask, CouchDB server, CouchDB2 (Python module),
Bootstrap, jQuery, DataTables.

The icon "Feather of Ma'at" made by
[freepik at flaticon.com](https://www.flaticon.com/authors/freepik).
