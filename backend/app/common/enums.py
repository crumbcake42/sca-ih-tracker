from enum import StrEnum


class TitleEnum(StrEnum):
    MR = "Mr."
    MS = "Ms."
    MRS = "Mrs."


class Boro(StrEnum):
    BROOKLYN = "BROOKLYN"
    MANHATTAN = "MANHATTAN"
    BRONX = "BRONX"
    QUEENS = "QUEENS"
    STATEN_ISLAND = "STATEN ISLAND"


class PermissionName(StrEnum):
    # User Management
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    # Project Management
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    # School/Contractor Management
    SCHOOL_EDIT = "school:edit"


class RoleName(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    INSPECTOR = "inspector"


class UserRole(StrEnum):
    SUPERADMIN = "superadmin"  # Can delete anything, manage users
    ADMIN = "admin"  # Can edit/add/delete projects, schools, contractors
    COORDINATOR = "coordinator"  # Can assign projects, view all results
    INSPECTOR = "inspector"  # Can create lab results and notes


class WACodeLevel(StrEnum):
    PROJECT = "project"
    BUILDING = "building"


class WACodeStatus(StrEnum):
    RFA_NEEDED = "rfa_needed"
    RFA_PENDING = "rfa_pending"
    ACTIVE = "active"
    ADDED_BY_RFA = "added_by_rfa"
    REMOVED = "removed"


class RFAStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RFAAction(StrEnum):
    ADD = "add"
    REMOVE = "remove"


class InternalDeliverableStatus(StrEnum):
    INCOMPLETE = "incomplete"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    IN_REVISION = "in_revision"
    COMPLETED = "completed"


class SCADeliverableStatus(StrEnum):
    PENDING_WA = "pending_wa"
    PENDING_RFA = "pending_rfa"
    OUTSTANDING = "outstanding"
    UNDER_REVIEW = "under_review"
    REJECTED = "rejected"
    APPROVED = "approved"


class TimeEntryStatus(StrEnum):
    ASSUMED = "assumed"
    ENTERED = "entered"
    LOCKED = "locked"


class SampleBatchStatus(StrEnum):
    ACTIVE = "active"
    DISCARDED = "discarded"
    LOCKED = "locked"


class NoteEntityType(StrEnum):
    PROJECT = "project"
    TIME_ENTRY = "time_entry"
    DELIVERABLE = "deliverable"
    SAMPLE_BATCH = "sample_batch"


class NoteType(StrEnum):
    """System-generated note types. NULL for user-authored notes."""

    TIME_ENTRY_CONFLICT = "time_entry_conflict"


class EmployeeRoleType(StrEnum):
    ACM_AIR_TECH = "Asbestos On Site Technical Air Testing"
    ACM_PROJECT_MONITOR = "Asbestos Project Monitor"
    ACM_INSPECTOR_A = "Asbestos Inspector Level A"
    ACM_INVESTIGATOR_A = "Asbestos Investigator Level A"
    ACM_PROJECT_MANAGER_A = "Asbestos Project Manager Level A"
    LBP_RISK_ASSESSOR_A = "Certified Lead Inspector / Risk Assessor Level A"
    LBP_RISK_ASSESSOR_B = "Certified Lead Inspector / Risk Assessor Level B"
    MOLD_FIELD_TECH = "Mold Field Technician"
    MOLD_PROJECT_MANAGER_A = "Mold Project Manager Level A"
    MOLD_PROJECT_MANAGER_B = "Mold Project Manager Level B"
