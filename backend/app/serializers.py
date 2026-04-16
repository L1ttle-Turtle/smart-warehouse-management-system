from .constants import ROLE_DELEGATION_ALLOWED_TARGETS
from .models import Employee, Role, User, UserPermissionDelegation


def serialize_user_delegation(delegation: UserPermissionDelegation):
    return {
        "id": delegation.id,
        "permission_id": delegation.permission_id,
        "permission_name": delegation.permission.permission_name if delegation.permission else None,
        "target_user_id": delegation.target_user_id,
        "target_username": delegation.target_user.username if delegation.target_user else None,
        "target_user_name": delegation.target_user.full_name if delegation.target_user else None,
        "target_role_id": delegation.target_role_id,
        "target_role_name": delegation.target_role.role_name if delegation.target_role else None,
        "grantor_user_id": delegation.grantor_user_id,
        "grantor_user_name": delegation.grantor_user.full_name if delegation.grantor_user else None,
        "grantor_role_id": delegation.grantor_role_id,
        "grantor_role_name": delegation.grantor_role.role_name if delegation.grantor_role else None,
        "note": delegation.note,
        "created_at": delegation.created_at.isoformat() if delegation.created_at else None,
        "updated_at": delegation.updated_at.isoformat() if delegation.updated_at else None,
    }


def serialize_role(role: Role):
    data = role.to_dict()
    data["base_permissions"] = [permission.permission_name for permission in role.permissions]
    data["delegated_permissions"] = []
    data["effective_permissions"] = list(data["base_permissions"])
    data["user_count"] = len(role.users)
    return data


def serialize_user(user: User):
    data = user.to_dict(exclude={"password_hash"})
    data["role"] = user.role.role_name if user.role else None
    data["employee_id"] = user.employee.id if user.employee else None
    data["employee_code"] = user.employee.employee_code if user.employee else None
    data["permissions"] = user.permission_names
    data["delegated_permission_sources"] = [
        serialize_user_delegation(delegation)
        for delegation in sorted(
            user.delegations_received,
            key=lambda item: (
                item.permission.permission_name if item.permission else "",
                item.grantor_user.full_name if item.grantor_user else "",
            ),
        )
    ]
    return data


def serialize_user_summary(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
        "role_id": user.role_id,
        "role_name": user.role.role_name if user.role else None,
        "employee_id": user.employee.id if user.employee else None,
        "employee_code": user.employee.employee_code if user.employee else None,
        "can_receive_delegation_manage": bool(
            user.role and ROLE_DELEGATION_ALLOWED_TARGETS.get(user.role.role_name, [])
        ),
    }


def serialize_management_user(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
        "role_id": user.role_id,
        "role": user.role.role_name if user.role else None,
        "employee_id": user.employee.id if user.employee else None,
        "employee_code": user.employee.employee_code if user.employee else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def serialize_employee(employee: Employee):
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "user_id": employee.user_id,
        "username": employee.user.username if employee.user else None,
        "full_name": employee.full_name,
        "department": employee.department,
        "position": employee.position,
        "phone": employee.phone,
        "email": employee.email,
        "role": employee.user.role.role_name if employee.user and employee.user.role else None,
        "status": employee.status,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
        "updated_at": employee.updated_at.isoformat() if employee.updated_at else None,
    }
