import inspect
from typing import Any, TypeVar, cast

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.guards import assert_deletable
from app.database import get_db
from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


def create_guarded_delete_router(
    *,
    model: type[ModelT],
    not_found_detail: str,
    refs: list[tuple[Any, Any, str]],
    path_param_name: str,
) -> APIRouter:
    """Factory that emits GET /{id}/connections + guarded DELETE /{id}.

    refs: list of (selectable, fk_column, label). selectable is the SQLAlchemy
    FromClause (ORM model class or Table) to count from. fk_column is the
    column whose == entity_id predicate identifies references. label is the
    public response key — preserve it verbatim across migrations.
    """
    _fields: dict[str, Any] = {label: (int, ...) for _, _, label in refs}
    ConnectionsSchema = pydantic.create_model(f"{model.__name__}Connections", **_fields)  # type: ignore[call-overload]

    async def _count_refs(db: AsyncSession, entity_id: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        for selectable, fk_col, label in refs:
            c = await db.scalar(
                select(func.count()).select_from(selectable).where(fk_col == entity_id)
            )
            counts[label] = c or 0
        return counts

    async def _connections_impl(entity_id: int, db: AsyncSession = Depends(get_db)):
        obj = await db.get(model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=not_found_detail)
        return await _count_refs(db, entity_id)

    async def _delete_impl(entity_id: int, db: AsyncSession = Depends(get_db)):
        obj = await db.get(model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=not_found_detail)
        assert_deletable(await _count_refs(db, entity_id))
        await db.delete(obj)
        await db.commit()

    # FastAPI matches path params to function arg names via the function's
    # __signature__. We rename `entity_id` → path_param_name in the signature
    # FastAPI inspects, then wrap each handler to translate the kwarg back before
    # calling the implementation (FastAPI calls the wrapper with path_param_name=...,
    # but the impl expects entity_id=...).
    def _wrap(impl):
        async def wrapper(**kwargs):
            kwargs["entity_id"] = kwargs.pop(path_param_name)
            return await impl(**kwargs)

        sig = inspect.signature(impl)
        cast(Any, wrapper).__signature__ = sig.replace(
            parameters=[
                p.replace(name=path_param_name) if p.name == "entity_id" else p
                for p in sig.parameters.values()
            ]
        )
        return wrapper

    _connections = _wrap(_connections_impl)
    _delete = _wrap(_delete_impl)

    router = APIRouter()
    router.add_api_route(
        f"/{{{path_param_name}}}/connections",
        _connections,
        methods=["GET"],
        response_model=ConnectionsSchema,
    )
    router.add_api_route(
        f"/{{{path_param_name}}}",
        _delete,
        methods=["DELETE"],
        status_code=204,
    )
    return router
