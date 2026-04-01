from sqlalchemy.orm import Session

# Import all model modules to ensure they are registered with Base
from app.projects import models as project_models
from app.users import models as user_models
from app.projects import models as project_models
from app.schools import models as school_models
from app.contractors import models as contractor_models
from app.employees import models as employee_models
from app.database import SessionLocal, engine, Base

from app.users.models import Role, Permission, User
from app.common.enums import PermissionName, RoleName
from app.common.security import hash_password
from app.common.config import settings


def initialize():
    print("\n" + "=" * 40)
    print(" 🏗️  DATABASE PREPARATION STARTING")
    print("=" * 40)

    # 1. Schema Check
    print(f"[*] Checking schema for {len(Base.metadata.tables)} tables...")
    Base.metadata.create_all(bind=engine)
    print("[+] Schema is up to date.")

    db: Session = SessionLocal()

    try:
        # 2. Permissions Sync
        print("\n[*] Syncing Permissions...")
        permissions_map = {}
        for perm_enum in PermissionName:
            db_perm = (
                db.query(Permission).filter(Permission.name == perm_enum.value).first()
            )
            if not db_perm:
                db_perm = Permission(name=perm_enum.value)
                db.add(db_perm)
                db.flush()
                print(f"  [NEW] Permission: {perm_enum.value}")
            permissions_map[perm_enum.value] = db_perm
        print(f"[+] Total permissions synchronized: {len(permissions_map)}")

        # 3. Role Configuration
        print("\n[*] Configuring Roles...")
        role_definitions = {
            RoleName.SUPERADMIN: [p.value for p in PermissionName],
            RoleName.ADMIN: [
                PermissionName.PROJECT_CREATE,
                PermissionName.PROJECT_EDIT,
                PermissionName.PROJECT_DELETE,
                PermissionName.SCHOOL_EDIT,
            ],
            RoleName.COORDINATOR: [
                PermissionName.PROJECT_CREATE,
                PermissionName.PROJECT_EDIT,
            ],
            RoleName.INSPECTOR: [],
        }

        for role_enum, allowed_perms in role_definitions.items():
            db_role = db.query(Role).filter(Role.name == role_enum.value).first()

            if not db_role:
                db_role = Role(name=role_enum.value)
                db.add(db_role)
                db.flush()
                status = "NEW"
            else:
                status = "EXISTING"

            # Update the permissions list (syncs the many-to-many table)
            db_role.permissions = [permissions_map[p] for p in allowed_perms]
            print(
                f"  [{status}] Role: {role_enum.value:12} | Permissions: {len(allowed_perms)}"
            )

        # 4. User Check
        print("\n[*] Verifying System Administrator...")
        admin_username = admin_username = settings.FIRST_ADMIN_USERNAME
        existing_admin = db.query(User).filter(User.username == admin_username).first()

        if not existing_admin:
            superadmin_role = (
                db.query(Role).filter(Role.name == RoleName.SUPERADMIN.value).first()
            )

            hashed_password = hash_password(settings.FIRST_ADMIN_PASSWORD)
            new_admin = User(
                first_name="System",
                last_name="Administrator",
                username=admin_username,
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=hashed_password,
                role=superadmin_role,
            )
            db.add(new_admin)
            print(f"  [CREATE] User '{admin_username}' added with SuperAdmin role.")
        else:
            print(f"  [OK] User '{admin_username}' already exists.")

        db.commit()
        print("\n" + "=" * 40)
        print(" ✅ DATABASE READY FOR DEVELOPMENT")
        print("=" * 40 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n[!] FATAL ERROR DURING PREPARATION: {e}")
    finally:
        db.close()
