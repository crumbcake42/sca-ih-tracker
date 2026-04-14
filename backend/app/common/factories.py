import csv
import inspect
import io
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.crud import get_paginated_list
from app.common.errors import ImportErrorReport
from app.common.responses import BatchImportResponse
from app.common.schemas import PaginatedResponse
from app.database import get_db
from app.database.base import Base
from app.users.dependencies import get_current_user

ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Define a Type Alias for the callback for better readability
# It takes (db, validated_pydantic_model, raw_csv_row)
# May be sync or async.
ImportValidator = Callable[[AsyncSession, Any, dict[str, Any]], Any | Coroutine[Any, Any, Any]]


def create_batch_import_router(
    model: type[ModelT],
    schema: type[SchemaT],
    create_schema: type[SchemaT],
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
        db: AsyncSession = Depends(get_db),
        current_user=Depends(get_current_user),
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
                    exists = (
                        await db.execute(select(model).where(model_col == unique_val))
                    ).scalar_one_or_none()
                    if exists:
                        raise ValueError(
                            f"{unique_col_name} '{unique_val}' already exists."
                        )

                # 3. Custom Validation Callback (The "Brain")
                if custom_validator:
                    result = custom_validator(db, obj_in, row_dict)
                    obj_in = await result if inspect.isawaitable(result) else result

                # 4. Final Create
                new_obj = model(**obj_in.model_dump(), created_by_id=current_user.id)
                db.add(new_obj)
                created_items.append(new_obj)

            except Exception as e:
                errors.append(ImportErrorReport(row=line_num, msg=str(e)))

        await db.commit()
        for item in created_items:
            await db.refresh(item)

        return {
            "message": f"Import of {len(created_items)} items complete.",
            "created_count": len(created_items),
            "created_items": created_items,
            "errors": errors,
        }

    return router


def create_readonly_router(
    model: type[ModelT],
    read_schema: type[SchemaT],
    prefix: str = "",
    tags: list[str | Enum] | None = None,
    default_sort: Any = None,
    search_attr: Any | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)

    @router.get("/", response_model=PaginatedResponse[read_schema])
    async def list_entries(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: str | None = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        items, total = await get_paginated_list(
            db=db,
            model=model,
            skip=skip,
            limit=limit,
            sort_by=default_sort,
            search_attr=search_attr,
            search_query=search,
        )
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    return router
