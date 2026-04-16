from __future__ import annotations

from .constants import DEFAULT_ROLE_PASSWORDS, RESOURCE_PERMISSIONS, ROLE_PERMISSION_MAP
from .extensions import db
from .models import Employee, Permission, Role, User


def seed_roles_and_permissions():
    permission_map = {}
    for permission_name in sorted(RESOURCE_PERMISSIONS):
        permission = Permission.query.filter_by(permission_name=permission_name).first()
        if not permission:
            permission = Permission(
                permission_name=permission_name,
                description=f"Permission for {permission_name}",
            )
            db.session.add(permission)
        permission_map[permission_name] = permission
    db.session.flush()

    for role_name, permissions in ROLE_PERMISSION_MAP.items():
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            role = Role(
                role_name=role_name,
                description=f"{role_name.title()} role",
            )
            db.session.add(role)
        role.permissions = [permission_map[name] for name in permissions]
    db.session.flush()


def seed_default_users():
    role_lookup = {role.role_name: role for role in Role.query.all()}
    for index, role_name in enumerate(
        ["admin", "manager", "staff", "accountant", "shipper"],
        start=1,
    ):
        user = User.query.filter_by(username=role_name).first()
        if user:
            continue
        user = User(
            username=role_name,
            full_name=role_name.title(),
            email=f"{role_name}@warehouse.local",
            phone=f"09000000{index}",
            status="active",
            role=role_lookup[role_name],
        )
        user.set_password(DEFAULT_ROLE_PASSWORDS[role_name])
        db.session.add(user)


def seed_default_employees():
    seeded_users = User.query.order_by(User.id.asc()).all()
    for index, user in enumerate(seeded_users, start=1):
        employee = Employee.query.filter_by(user_id=user.id).first()
        if employee:
            continue
        employee = Employee(
            employee_code=f"EMP{index:03d}",
            user_id=user.id,
            full_name=user.full_name,
            department="Van hanh" if user.role.role_name in {"staff", "shipper"} else "Quan tri",
            position=user.role.role_name.title(),
            phone=user.phone,
            email=user.email,
            status="active",
        )
        db.session.add(employee)


def seed_all():
    seed_roles_and_permissions()
    seed_default_users()
    seed_default_employees()
    db.session.commit()
