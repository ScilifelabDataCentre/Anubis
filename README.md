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
    - "submitter" if has submitted within a specific call
    - "reviewer" for a specific call; designated by admin
  - Reviewers visible to each other within call: settable
  - Users visible to reviewers within call: settable
  
- Call
  - = Call for submissions.
  - Container of submissions.
  - With info, documents, instructions, etc, for the user (applicant).
  - Configurable fields to be filled in for a submission.
  - Status: Pending, Testing, Published, Closed, Archived.
  - Handled by admin.
  
- Submission
  - = Application; the proposal to be reviewed.
  - Belongs to one and only one call.
  - Information fields; defined in the call.
  - Attached documents (project description, CV,...)
  - Made by user.
  - Status: Preparation, Submitted, Review, Disqualified, Assessed.
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

- Assessment
  - Aggregated evaluation from reviewers.
  - Anonymous reviewers or not.
  - Consensus comment and assessment.
  - Judgement
    - Classes (shortlist, excluded...)
    - Priority; numerical
    - Ranking; relative order

- Overview
  - Tables of various submission properties
  - Tables of various reviewer properties
  - Aggregates of properties

- Report
  - Assessment to be communicated to user (applicant).

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
