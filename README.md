# Anubis

Submission review handling system.

## Entities

- User
  - Name, email, affiliation, gender, birth date, title.
  - Login required.
  - Role admin
  - Role user
  - Users are anonymous vs other users by default (except admin)
  - Capacity; role within a specific call
    - "submitter" if user has submitted within a specific call
    - "reviewer" for a specific call; designated by admin
  - Reviewers visible to each other within call: settable
  - Users visible to reviewers within call: settable
  
- Call
  - = Call for submissions.
  - Container of submissions.
  - With info, documents, instructions, etc, for the user (applicant).
  - Configurable fields to be filled in for a submission.
  - Status: Preparation, Published, Closed, Archived.
  - Handled by admin.
  - Date opened
  - Date closed (time? local)
  
- Submission
  - = Application; the proposal to be reviewed.
  - Belongs to one and only one call.
  - Information fields; defined in the call.
  - Attached documents (project description, CV,...)
  - Made by user.
  - Status: Preparation, Submitted, Reviewing, Discarded, Decided.
  - Consortium = group of user that may access a submission.
  - Reviewer relation
    - Interest
    - Conflict-of-interest
    - Assignment
    - Responsibility
  
- Evaluation
  - A reviewer's comments and assessment of a submission.
  - Criteria = reviewer's assessment fields; defined in the call.
  - Versions?
  - Owned by reviewer; settable privileges for other reviewers.

- Decision
  - Aggregated evaluations from reviewers.
  - Anonymous reviewers or not? settable
  - Conclusion: Consensus comment and assessment.
  - Judgement
    - Classes (shortlist, excluded...)
    - Priority; numerical
    - Ranking; relative order
  - Grant (amount of money, or other resource)
  - Which info to communicate to submitter, and to public
  - Date of communication

- Overview
  - Tables of various submission properties
  - Tables of various assessment properties
  - Aggregates of properties

## Built on

Python3, Flask, CouchDB server, CouchDB2 (Python module), jsonschema,
Bootstrap, jQuery, DataTables.

## Commercial systems

- Evalato
- Apply Surveymonkey
- OpenWater
- AwardForce

The icon "Feather of Ma'at" made by
[freepik from flaticon.com](https://www.flaticon.com/authors/freepik).
