import asyncio
import csv
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.projects.models  # noqa: F401 — registers Project/links mappers
import app.work_auths.models  # noqa: F401
from app.common.config import settings
from app.common.enums import EmployeeRoleType, PermissionName, UserRole
from app.common.security import hash_password
from app.contractors.models import Contractor as ContractorModel
from app.contractors.schemas import ContractorCreate as ContractorSchema
from app.database import Base, SessionLocal, engine
from app.deliverables.models import Deliverable as DeliverableModel
from app.deliverables.schemas import DeliverableCreate as DeliverableSchema
from app.employees.models import Employee as EmployeeModel
from app.employees.models import EmployeeRole as EmployeeRoleModel
from app.employees.schemas import EmployeeCreate as EmployeeSchema
from app.hygienists.models import Hygienist as HygienistModel
from app.hygienists.schemas import HygienistCreate as HygienistSchema
from app.schools.models import School as SchoolModel
from app.schools.schemas import SchoolCreate as SchoolSchema
from app.users.models import Permission, Role, User
from app.wa_codes.models import WACode as WACodeModel
from app.wa_codes.schemas import WACodeCreate as WACodeSchema

# Type Variables for Generic support
ModelT = TypeVar("ModelT", bound=Base)
SchemaT = TypeVar("SchemaT", bound=BaseModel)

# Path to your seed files
SEED_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "seed"


async def seed_from_csv(
    db: AsyncSession,
    model_class: type[ModelT],
    schema_class: type[SchemaT],
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

    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Track counts for the final report
        added_count: int = 0
        error_count: int = 0

        for line_num, row in enumerate(reader, start=2):
            try:
                # 1. Validate with Pydantic — coerce empty CSV strings to None
                cleaned = {k: (v if v != "" else None) for k, v in row.items()}
                validated_data: SchemaT = schema_class(**cleaned)

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


async def seed_employee_roles(db: AsyncSession) -> None:
    """Seed employee_roles from CSV, matching rows to employees via adp_id."""
    filename = "employee_roles.csv"
    file_path = SEED_DATA_PATH / filename
    if not file_path.exists():
        print(f"  [SKIP] {filename} not found.")
        return

    print(f"[*] Seeding EmployeeRoles from {filename}...")
    added_count = 0
    error_count = 0

    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for line_num, row in enumerate(reader, start=2):
            adp_id = row.pop("adp_id", "").strip()
            role_type_value = row.pop("role_type", "").strip()
            row.pop("name", None)  # ignore reference-only column if present
            try:
                from datetime import date as date_type
                from decimal import Decimal

                start_date = date_type.fromisoformat(row["start_date"])
                end_date = date_type.fromisoformat(row["end_date"]) if row.get("end_date") else None
                hourly_rate = Decimal(row["hourly_rate"])

                # Resolve employee
                employee = (
                    await db.execute(
                        select(EmployeeModel).where(EmployeeModel.adp_id == adp_id)
                    )
                ).scalar_one_or_none()
                if not employee:
                    print(f"  [ERROR] Line {line_num}: No employee with adp_id={adp_id!r}")
                    error_count += 1
                    continue

                # Coerce role_type to enum
                try:
                    role_type = EmployeeRoleType(role_type_value)
                except ValueError:
                    print(
                        f"  [ERROR] Line {line_num}: Unknown role_type={role_type_value!r}"
                    )
                    error_count += 1
                    continue

                # Skip duplicates
                existing = (
                    await db.execute(
                        select(EmployeeRoleModel).where(
                            EmployeeRoleModel.employee_id == employee.id,
                            EmployeeRoleModel.role_type == role_type,
                            EmployeeRoleModel.start_date == start_date,
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    continue

                db.add(
                    EmployeeRoleModel(
                        employee_id=employee.id,
                        role_type=role_type,
                        start_date=start_date,
                        end_date=end_date,
                        hourly_rate=hourly_rate,
                    )
                )
                added_count += 1

            except Exception as e:
                error_count += 1
                print(f"  [FATAL] Line {line_num}: {str(e)}")

    await db.flush()
    print(f"  [+] Finished EmployeeRole: {added_count} added, {error_count} failed.")


async def initialize():
    print("\n" + "=" * 40)
    print(" [*] DATABASE PREPARATION (ASYNC)")
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
                UserRole.SUPERADMIN: [p.value for p in PermissionName],
                UserRole.ADMIN: [
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

            # 4. System User Sentinel (must be inserted before any other users
            #    so it receives id=1 on a fresh database)
            print("\n[*] Ensuring system user sentinel...")
            stmt = select(User).where(User.username == "system")
            result = await db.execute(stmt)
            if not result.unique().scalars().first():
                superadmin_role_stmt = select(Role).where(
                    Role.name == UserRole.SUPERADMIN.value
                )
                superadmin_role = (await db.execute(superadmin_role_stmt)).scalar_one()
                system_user = User(
                    first_name="System",
                    last_name="User",
                    username="system",
                    email="system@system.internal",
                    hashed_password="!",  # Impossible bcrypt hash — cannot authenticate
                    role=superadmin_role,
                )
                db.add(system_user)
                await db.flush()
                print(f"  [CREATE] System user created (id={system_user.id}).")
            else:
                print("  [OK] System user already exists.")

            # 5. User Check
            print("\n[*] Verifying System Administrator...")
            stmt = select(User).where(User.username == settings.FIRST_ADMIN_USERNAME)
            result = await db.execute(stmt)
            if not result.unique().scalars().first():
                admin_role_stmt = select(Role).where(
                    Role.name == UserRole.SUPERADMIN.value
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
            else:
                print(
                    f"  [OK] User '{settings.FIRST_ADMIN_USERNAME}' already exists with pw {settings.FIRST_ADMIN_PASSWORD}."
                )
            # 6. Seed Base Truth Data (CSV)
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

            await seed_employee_roles(db)

            await db.commit()
            print("\n" + "=" * 40)
            print(" [OK] DATABASE READY")
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
