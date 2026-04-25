from enum import Enum
from typing import Any, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.crud import get_paginated_list
from app.common.introspection import filterable_columns
from app.common.schemas import PaginatedResponse
from app.database import get_db
from app.database.base import Base

_RESERVED_PARAMS: frozenset[str] = frozenset({"skip", "limit", "search"})

ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


def create_readonly_router(
    model: type[ModelT],
    read_schema: type[SchemaT],
    prefix: str = "",
    tags: list[str | Enum] | None = None,
    default_sort: Any = None,
    search_attr: Any | None = None,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=tags)

    # Build filterable column map once at factory construction time.
    _filterable: dict[str, Any] = filterable_columns(model)

    @router.get("/", response_model=PaginatedResponse[read_schema])
    async def list_entries(
        request: Request,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        search: str | None = Query(None),
        db: AsyncSession = Depends(get_db),
    ):
        unknown: list[str] = []
        coercion_errors: list[str] = []
        col_values: dict[str, list[Any]] = {}

        for key, value in request.query_params.multi_items():
            if key in _RESERVED_PARAMS:
                continue
            if key not in _filterable:
                if key not in unknown:
                    unknown.append(key)
                continue
            col = _filterable[key]
            try:
                coerced = col.type.python_type(value)
            except (ValueError, TypeError):
                coercion_errors.append(f"Invalid value for '{key}': '{value}'")
                continue
            col_values.setdefault(key, []).append(coerced)

        if unknown:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown query parameters: {', '.join(sorted(unknown))}",
            )
        if coercion_errors:
            raise HTTPException(status_code=422, detail=coercion_errors[0])

        filters: list[ColumnElement[bool]] = [
            getattr(model, name).in_(values) for name, values in col_values.items()
        ]

        items, total = await get_paginated_list(
            db=db,
            model=model,
            skip=skip,
            limit=limit,
            sort_by=default_sort,
            search_attr=search_attr,
            search_query=search,
            filters=filters or None,
        )
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    return router
