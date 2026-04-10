from .auth import router as auth_router
from .users import router as users_router

# Now you can import these directly from app.users.router
__all__ = ["auth_router", "users_router"]
