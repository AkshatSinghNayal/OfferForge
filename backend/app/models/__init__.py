"""Models package — imports all model classes so SQLAlchemy registers them
on Base.metadata before Alembic autogenerate runs.
"""

from app.models.activity_log import ActivityLog
from app.models.company import (
    CHECKLIST_ITEMS,
    APPLICATION_STATUSES,
    COMPANY_CLUSTERS,
    ChecklistItem,
    Company,
    UserCompany,
)
from app.models.dsa import (
    DSA_DIFFICULTIES,
    DSA_PLATFORMS,
    DSA_REVISION_STATUSES,
    DSA_STATUSES,
    DsaProblem,
    DsaProblemTag,
    DsaTag,
)
from app.models.note import NOTE_TYPES, Note
from app.models.resource import RESOURCE_CATEGORIES, Resource
from app.models.resume import Resume, ResumeCompanyMap, ResumeKeyword
from app.models.user import PasswordResetToken, RefreshToken, User

__all__ = [
    # Models
    "User",
    "RefreshToken",
    "PasswordResetToken",
    "Company",
    "UserCompany",
    "ChecklistItem",
    "DsaProblem",
    "DsaTag",
    "DsaProblemTag",
    "Resume",
    "ResumeKeyword",
    "ResumeCompanyMap",
    "Resource",
    "Note",
    "ActivityLog",
    # Constants (consumed by services + migrations + tests)
    "CHECKLIST_ITEMS",
    "APPLICATION_STATUSES",
    "COMPANY_CLUSTERS",
    "DSA_PLATFORMS",
    "DSA_DIFFICULTIES",
    "DSA_STATUSES",
    "DSA_REVISION_STATUSES",
    "NOTE_TYPES",
    "RESOURCE_CATEGORIES",
]
