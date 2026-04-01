from enum import Enum
from typing import Type, TypeVar
from typing import Callable, Any, Awaitable
import csv
import io
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.users.dependencies import get_current_user
from app.common.responses import BatchImportResponse
from app.common.errors import ImportErrorReport


# Define a Type Alias for the callback for better readability
# It takes (db, validated_pydantic_model, raw_csv_row)
ImportValidator = Callable[[Session, Any, dict[str, Any]], Any]

# Type variables for our generic models
ModelT = TypeVar("ModelT")  # The SQLAlchemy Model
SchemaT = TypeVar("SchemaT")  # The "Response" Schema (e.g. School)
CreateSchemaT = TypeVar(
    "CreateSchemaT", bound=BaseModel
)  # The "Create" Schema (e.g. SchoolCreate)


def create_batch_import_router(
    model: Type[ModelT],
    schema: Type[SchemaT],
    create_schema: Type[CreateSchemaT],
    unique_col_name: str | None,
    prefix: str,
    tags: list[str | Enum],
    custom_validator: ImportValidator | None = None,
) -> APIRouter:

    router = APIRouter(
        prefix=prefix, tags=tags, dependencies=[Depends(get_current_user)]
    )

    @router.post("/import", response_model=BatchImportResponse[schema])  # type: ignore
    async def import_batch(
        file: UploadFile = File(...),
        has_headers: bool = Query(True),
        db: Session = Depends(get_db),
    ):
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV.")

        content = await file.read()
        stream = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(stream) if has_headers else csv.reader(stream)

        created_items = []
        errors = []

        for line_num, row in enumerate(reader, start=1 if not has_headers else 2):
            try:
                # Handle CSV row to dict conversion
                row_dict = (
                    row
                    if isinstance(row, dict)
                    else dict(zip(create_schema.model_fields.keys(), row))
                )

                # 1. Validate
                obj_in = create_schema.model_validate(row_dict)

                # 2. Global Unique Check (Simple Case)
                if unique_col_name:
                    unique_val = getattr(obj_in, unique_col_name)
                    model_col = getattr(model, unique_col_name)
                    exists = db.execute(
                        select(model).where(model_col == unique_val)
                    ).scalar_one_or_none()
                    if exists:
                        raise ValueError(
                            f"{unique_col_name} '{unique_val}' already exists."
                        )

                # 3. Custom Validation Callback (The "Brain")
                if custom_validator:
                    # The validator can perform calculations or multi-column checks
                    # It can even return a modified version of obj_in
                    obj_in = custom_validator(db, obj_in, row_dict)

                # 4. Final Create
                new_obj = model(**obj_in.model_dump())
                db.add(new_obj)
                created_items.append(new_obj)

            except Exception as e:
                errors.append(ImportErrorReport(row=line_num, msg=str(e)))

        db.commit()
        for item in created_items:
            db.refresh(item)

        return {
            "message": f"Import of {len(created_items)} items complete.",
            "created_count": len(created_items),
            "created_items": created_items,
            "errors": errors,
        }

    return router
