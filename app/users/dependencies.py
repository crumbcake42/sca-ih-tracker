from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.common.enums import PermissionName
from app.common.config import settings
from app.database import get_db
from app.users.models import User


# This tells FastAPI where to find the login token in the Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Decodes the JWT, validates the user, and returns the User object.
    If the token is invalid or the user is missing, it raises a 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 1. Decode the token using your Secret Key
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str | None = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # 2. Look up the user in the database
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user


class PermissionChecker:
    def __init__(self, required_permission: PermissionName):
        self.required_permission = required_permission

    def __call__(self, user: User = Depends(get_current_user)):
        # user.role.permissions is a list of Permission objects from SQLAlchemy
        # We compare the Enum value to the string stored in the database
        user_permissions = [p.name for p in user.role.permissions]

        if self.required_permission.value not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {self.required_permission.value}",
            )
        return user
