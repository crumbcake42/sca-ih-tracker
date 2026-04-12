from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class TimeEntryCreate(BaseModel):
    start_datetime: datetime
    end_datetime: datetime | None = None
    employee_id: int
    employee_role_id: int
    project_id: int
    school_id: int
    notes: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "TimeEntryCreate":
        if self.end_datetime is not None and self.end_datetime <= self.start_datetime:
            raise ValueError("end_datetime must be after start_datetime")
        return self


class TimeEntryUpdate(BaseModel):
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def end_after_start(self) -> "TimeEntryUpdate":
        if self.start_datetime is not None and self.end_datetime is not None:
            if self.end_datetime <= self.start_datetime:
                raise ValueError("end_datetime must be after start_datetime")
        return self


class TimeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_datetime: datetime
    end_datetime: datetime | None
    employee_id: int
    employee_role_id: int
    project_id: int
    school_id: int
    notes: str | None
    created_at: datetime
