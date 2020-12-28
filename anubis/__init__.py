"Proposals review handling system."

import re

__version__ = '0.9.36'

class Constants:
    VERSION     = __version__
    SOURCE_NAME = 'Anubis'
    SOURCE_URL  = 'https://github.com/pekrau/Anubis'

    BOOTSTRAP_VERSION  = '4.5.3'
    JQUERY_VERSION     = '3.5.1'
    DATATABLES_VERSION = '1.10.22'

    ID_RX    = re.compile(r'^[a-z][a-z0-9_]*$', re.I)
    IUID_RX  = re.compile(r'^[a-f0-9]{32,32}$', re.I)
    EMAIL_RX = re.compile(r'^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$')

    # CouchDB document types
    USER     = 'user'
    CALL     = 'call'
    PROPOSAL = 'proposal'
    REVIEW   = 'review'
    DECISION = 'decision'
    LOG      = 'log'

    # User roles
    ADMIN = 'admin'
    STAFF = 'staff'
    # USER  = 'user' # Defined above
    USER_ROLES = (ADMIN, STAFF, USER)

    # User statuses
    PENDING  = 'pending'
    ENABLED  = 'enabled'
    DISABLED = 'disabled'
    USER_STATUSES = (PENDING, ENABLED, DISABLED)

    # Input field types
    LINE     = 'line'
    BOOLEAN  = 'boolean'
    SELECT   = 'select'
    INTEGER  = 'integer'
    FLOAT    = 'float'
    SCORE    = 'score'
    TEXT     = 'text'
    DOCUMENT = 'document'
    FIELD_TYPES = (LINE, BOOLEAN, SELECT, INTEGER, FLOAT, SCORE, TEXT, DOCUMENT)
    NUMERICAL_FIELD_TYPES = (INTEGER, FLOAT, SCORE)

    # Access flags for each call
    ACCESS = ('allow_reviewer_view_all_reviews',
              'allow_submitter_view_decision',
              # not implemented 'allow_public_view_all_decisions',
    )

    # MIME types
    XLSX_MIMETYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def __setattr__(self, key, value):
        raise ValueError('cannot set constant')


constants = Constants()
