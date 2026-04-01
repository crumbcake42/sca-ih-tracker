from .base import Project
from .links import ProjectContractor

# This allows other modules to do: from app.projects.models import Project
__all__ = ["Project", "ProjectContractor"]
