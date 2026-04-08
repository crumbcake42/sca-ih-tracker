from enum import Enum


class TitleEnum(str, Enum):
    MR = "Mr."
    MS = "Ms."
    MRS = "Mrs."


class Boro(str, Enum):
    BROOKLYN = "BROOKLYN"
    MANHATTAN = "MANHATTAN"
    BRONX = "BRONX"
    QUEENS = "QUEENS"
    STATEN_ISLAND = "STATEN ISLAND"


class PermissionName(str, Enum):
    # User Management
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    # Project Management
    PROJECT_CREATE = "project:create"
    PROJECT_EDIT = "project:edit"
    PROJECT_DELETE = "project:delete"
    # School/Contractor Management
    SCHOOL_EDIT = "school:edit"


class RoleName(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    INSPECTOR = "inspector"


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"  # Can delete anything, manage users
    ADMIN = "admin"  # Can edit/add/delete projects, schools, contractors
    COORDINATOR = "coordinator"  # Can assign projects, view all results
    INSPECTOR = "inspector"  # Can create lab results and notes


class WACodeLevel(str, Enum):
    PROJECT = "project"
    BUILDING = "building"


class EmployeeRoleType(str, Enum):
    AIR_MONITOR = "Air Monitor"
    AIR_TECH = "Air Technician"
    PROJECT_MONITOR = "Project Monitor"
    LEAD_RISK_ASSESSOR = "Lead Risk Assessor"
