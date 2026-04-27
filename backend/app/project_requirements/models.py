from typing import TYPE_CHECKING
from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import AuditMixin, Base

if TYPE_CHECKING:
    from app.wa_codes.models import WACode

class WACodeRequirementTrigger(Base, AuditMixin):
    __tablename__ = "wa_code_requirement_triggers"

    id: Mapped[int] = mapped_column(primary_key=True)
    wa_code_id: Mapped[int] = mapped_column(
        ForeignKey("wa_codes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_type_name: Mapped[str] = mapped_column(String, nullable=False)
    template_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    template_params_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "wa_code_id",
            "requirement_type_name",
            "template_params_hash",
            name="uq_wa_code_requirement_trigger",
        ),
    )

    wa_code: Mapped["WACode"] = relationship("WACode", lazy="selectin")
