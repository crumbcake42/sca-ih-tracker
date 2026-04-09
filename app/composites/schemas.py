from app.projects.schemas import Project
from app.schools.schemas import School


# This folder is the ONLY place allowed to import from
# multiple domain schema files at once.
class ProjectWithSchools(Project):
    schools: list[School] = []


class SchoolWithProjects(School):
    projects: list[Project] = []
