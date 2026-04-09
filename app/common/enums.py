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


class EmployeeRoleType(StrEnum):
    AIR_MONITOR = "Air Monitor"
    AIR_TECH = "Air Technician"
    PROJECT_MONITOR = "Project Monitor"
    LEAD_RISK_ASSESSOR = "Lead Risk Assessor"
