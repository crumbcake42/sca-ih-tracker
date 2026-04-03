from .base import Project
from .links import ProjectContractorLink

# This allows other modules to do: from app.projects.models import Project
__all__ = ["Project", "ProjectContractorLink"]
