import asyncio
import csv
from pathlib import Path
from typing import Type, TypeVar, Any, Sequence
from pydantic import BaseModel, ValidationError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import SessionLocal, engine, Base
from app.users.models import Role, Permission, User

from app.schools.models import School as SchoolModel
from app.schools.schemas import SchoolCreate as SchoolSchema

from app.contractors.models import Contractor as ContractorModel
from app.contractors.schemas import ContractorCreate as ContractorSchema

from app.deliverables.models import Deliverable as DeliverableModel
from app.deliverables.schemas import DeliverableCreate as DeliverableSchema

from app.employees.models import Employee as EmployeeModel
from app.employees.schemas import EmployeeCreate as EmployeeSchema

from app.hygienists.models import Hygienist as HygienistModel
from app.hygienists.schemas import HygienistCreate as HygienistSchema

from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACodeCreate as WACodeSchema


from app.common.enums import PermissionName, RoleName
from app.common.security import hash_password
from app.common.config import settings

# Type Variables for Generic support
ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Path to your seed files
SEED_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seed"


async def seed_from_csv(
    db: AsyncSession,
    model_class: Type[ModelT],
    schema_class: Type[SchemaT],
    filename: str,
    unique_field: str,
) -> None:
    """
    Generic helper to validate and seed models from CSV files.

    Args:
        db: The active async database session.
        model_class: The SQLAlchemy model class (e.g., School).
        schema_class: The Pydantic schema for validation (e.g., SchoolCreate).
        filename: Name of the CSV file in the seed directory.
        unique_field: The attribute name used to check for existing records.
    """
    file_path: Path = SEED_DATA_PATH / filename
    if not file_path.exists():
        print(f"  [SKIP] {filename} not found.")
        return

    print(f"[*] Seeding {model_class.__name__}s from {filename}...")

    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Track counts for the final report
        added_count: int = 0
        error_count: int = 0

        for line_num, row in enumerate(reader, start=2):
            try:
                # 1. Validate with Pydantic
                validated_data: SchemaT = schema_class(**row)

                # 2. Check for existence
                unique_val: Any = getattr(validated_data, unique_field)
                stmt = select(model_class).where(
                    getattr(model_class, unique_field) == unique_val
                )
                result = await db.execute(stmt)
                existing: ModelT | None = result.scalars().first()

                if not existing:
                    # 3. Create SQLAlchemy instance
                    new_obj: ModelT = model_class(**validated_data.model_dump())
                    db.add(new_obj)
                    added_count += 1

            except ValidationError as e:
                error_count += 1
                print(
                    f"  [ERROR] Line {line_num} in {filename}: {e.errors()[0]['msg']}"
                )
            except Exception as e:
                error_count += 1
                print(f"  [FATAL] Line {line_num}: {str(e)}")

        await db.flush()
        print(
            f"  [+] Finished {model_class.__name__}: {added_count} added, {error_count} failed."
        )


async def initialize():
    print("\n" + "=" * 40)
    print(" 🏗️  DATABASE PREPARATION (ASYNC)")
    print("=" * 40)

    # 1. Schema Creation
    async with engine.begin() as conn:
        print(f"[*] Syncing tables for {len(Base.metadata.tables)} models...")
        # In production, use Alembic. In local dev/reset, this is fine.
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        try:
            # 2. Permissions Sync
            print("\n[*] Syncing Permissions...")
            permissions_map = {}
            for perm_enum in PermissionName:
                stmt = select(Permission).where(Permission.name == perm_enum.value)
                result = await db.execute(stmt)
                db_perm = result.scalars().first()

                if not db_perm:
                    db_perm = Permission(name=perm_enum.value)
                    db.add(db_perm)
                    await db.flush()
                    print(f"  [NEW] Permission: {perm_enum.value}")
                permissions_map[perm_enum.value] = db_perm

            # 3. Role Configuration
            print("\n[*] Configuring Roles...")
            role_definitions = {
                RoleName.SUPERADMIN: [p.value for p in PermissionName],
                RoleName.ADMIN: [
                    PermissionName.PROJECT_CREATE,
                    PermissionName.SCHOOL_EDIT,
                ],
                # Add others...
            }

            for role_enum, allowed_perms in role_definitions.items():
                stmt = (
                    select(Role)
                    .where(Role.name == role_enum.value)
                    .options(selectinload(Role.permissions))
                )
                result = await db.execute(stmt)
                db_role = result.scalars().first()

                if not db_role:
                    db_role = Role(name=role_enum.value)
                    db.add(db_role)
                    await db.flush()
                    # Re-fetch so the permissions collection is initialized via
                    # selectinload before we assign to it. Assigning to an
                    # unloaded lazy="joined" collection triggers IO in async.
                    result = await db.execute(
                        select(Role)
                        .where(Role.id == db_role.id)
                        .options(selectinload(Role.permissions))
                    )
                    db_role = result.scalar_one()

                # Link permissions
                db_role.permissions = [permissions_map[p] for p in allowed_perms]
                print(f"  [OK] Role: {role_enum.value:12}")

            # 4. User Check
            print("\n[*] Verifying System Administrator...")
            stmt = select(User).where(User.username == settings.FIRST_ADMIN_USERNAME)
            result = await db.execute(stmt)
            if not result.unique().scalars().first():
                admin_role_stmt = select(Role).where(
                    Role.name == RoleName.SUPERADMIN.value
                )
                admin_role = (await db.execute(admin_role_stmt)).unique().scalar_one()

                new_admin = User(
                    first_name="System",
                    last_name="Administrator",
                    username=settings.FIRST_ADMIN_USERNAME,
                    email=settings.FIRST_ADMIN_EMAIL,
                    hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                    role=admin_role,
                )
                db.add(new_admin)
                print(f"  [CREATE] User '{settings.FIRST_ADMIN_USERNAME}' added.")

            # 5. Seed Base Truth Data (CSV)
            print("\n[*] Seeding Business Data...")
            seed_files = [
                (db, SchoolModel, SchoolSchema, "schools.csv", "code"),
                (db, ContractorModel, ContractorSchema, "contractors.csv", "name"),
                (db, EmployeeModel, EmployeeSchema, "employees.csv", "adp_id"),
                (db, HygienistModel, HygienistSchema, "hygienists.csv", "email"),
                (db, WACodeModel, WACodeSchema, "wa_codes.csv", "code"),
                (db, DeliverableModel, DeliverableSchema, "deliverables.csv", "name"),
            ]
            for seed_args in seed_files:
                await seed_from_csv(*seed_args)

            await db.commit()
            print("\n" + "=" * 40)
            print(" ✅ DATABASE READY")
            print("=" * 40 + "\n")

        except Exception as e:
            await db.rollback()
            print(f"\n[!] FATAL ERROR: {e}")
            raise e


def run_setup():
    """Synchronous entry point for pyproject.toml scripts"""
    try:
        asyncio.run(initialize())
    except KeyboardInterrupt:
        print("\n[!] Setup interrupted by user.")
    except Exception as e:
        print(f"\n[!] Setup failed: {e}")
