import itertools

from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import Role, User

_user_counter = itertools.count(1)


async def seed_user_role(db: AsyncSession, *, name: str = "staff") -> Role:
    role = Role(name=name)
    db.add(role)
    await db.flush()
    return role


async def seed_user(db: AsyncSession, role: Role, **overrides) -> User:
    n = next(_user_counter)
    defaults = dict(
        first_name="Test",
        last_name="User",
        username=f"user{n}",
        email=f"user{n}@example.com",
        hashed_password="irrelevant",
        role_id=role.id,
    )
    user = User(**{**defaults, **overrides})
    db.add(user)
    await db.flush()
    return user
