from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import PermissionName
from app.common.config import settings
from app.database import get_db
from app.users.models import User, Role, Permission  # Ensure these are imported

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Because you have lazy="joined" in your models,
    # SQLAlchemy will automatically JOIN 'roles' and 'permissions'.
    # We just need to execute the select.
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)

    # unique() is required when using joined loads for many-to-many
    # to prevent duplicate row objects in the result set.
    user = result.unique().scalars().first()

    if user is None:
        raise credentials_exception

    return user


class PermissionChecker:
    def __init__(self, required_permission: PermissionName):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(get_current_user)):
        # Because we used selectinload, user.role.permissions is already in memory
        user_permissions = [p.name for p in user.role.permissions]

        if self.required_permission.value not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.required_permission.value}",
            )
        return user
