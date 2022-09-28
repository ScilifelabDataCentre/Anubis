# ![Anubis logo](https://github.com/pekrau/Anubis/raw/master/anubis/static/logo32.png) Anubis

Anubis is a web-based system to handle calls, proposal submission,
reviews, decisions and grant dossiers. It allows:

- The publication of calls.
- The creation, editing and submission of proposals.
- A person who wants to prepare and submit a proposal must create an
  account in the system.
- The administrator configures which accounts should be reviewers of
  the proposals in a call.
- The administrator records the decisions that the reviewers (or other group) have made.
- Documents and information related to the grants awarded to successful proposals
  can be handled by the system.

For more information, see the Documentation pages at the reference instance
at [SciLifeLab Anubis](https://anubis.scilifelab.se/).

Some of the steps in a typical worflow are illustrated in the screenshots in the
[PowerPoint presentation](https://github.com/pekrau/Anubis/raw/master/Anubis-common-actions.pptx).

See [install/README.md](install/README.md) for information on how to install
this system.


### Design decision notes

The main entity of the Anubis system is **call**. It is effectively a
container for the instances of **proposal**, **review**, **decision**
and **grant**, which all alway refer to one and exactly one call. The
call contains the definitions of the data fields for these other
entities.

It is possible to change the field definitions for these other
entities even when instances of them already exist. The data for
fields that are removed from the definition the call is retained in
the database, but becomes unreachable via the web interface. This
makes it possible to change the definition of e.g. a proposal while
the call is open. Obviously, this should not be done if possible,
since it may invalidate existing proposals, but it will not crash the
system.
