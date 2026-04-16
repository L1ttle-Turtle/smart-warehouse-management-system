from __future__ import annotations

from .constants import ROLE_DELEGATION_ALLOWED_TARGETS
from .extensions import bcrypt, db
from .utils import model_to_dict, utc_now


class SerializerMixin:
    def to_dict(self, exclude=None):
        return model_to_dict(self, exclude=exclude)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class RolePermission(db.Model, SerializerMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (
        db.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)


class Role(db.Model, SerializerMixin):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    users = db.relationship("User", back_populates="role")
    permissions = db.relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        order_by="Permission.permission_name",
    )


class Permission(db.Model, SerializerMixin):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    permission_name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    roles = db.relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )
    delegations = db.relationship(
        "UserPermissionDelegation",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class UserPermissionDelegation(db.Model, SerializerMixin, TimestampMixin):
    __tablename__ = "user_permission_delegations"
    __table_args__ = (
        db.UniqueConstraint(
            "grantor_user_id",
            "target_user_id",
            "permission_id",
            name="uq_user_permission_delegation",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    grantor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    grantor_role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey("permissions.id"), nullable=False)
    note = db.Column(db.String(255))

    grantor_user = db.relationship(
        "User",
        foreign_keys=[grantor_user_id],
        back_populates="delegations_granted",
    )
    target_user = db.relationship(
        "User",
        foreign_keys=[target_user_id],
        back_populates="delegations_received",
    )
    grantor_role = db.relationship("Role", foreign_keys=[grantor_role_id])
    target_role = db.relationship("Role", foreign_keys=[target_role_id])
    permission = db.relationship("Permission", back_populates="delegations")


class Employee(db.Model, SerializerMixin, TimestampMixin):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(30), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120))
    position = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default="active", nullable=False)

    user = db.relationship("User", back_populates="employee", foreign_keys=[user_id])


class User(db.Model, SerializerMixin, TimestampMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)

    role = db.relationship("Role", back_populates="users")
    employee = db.relationship("Employee", back_populates="user", uselist=False)
    delegations_granted = db.relationship(
        "UserPermissionDelegation",
        back_populates="grantor_user",
        foreign_keys="UserPermissionDelegation.grantor_user_id",
    )
    delegations_received = db.relationship(
        "UserPermissionDelegation",
        back_populates="target_user",
        foreign_keys="UserPermissionDelegation.target_user_id",
    )

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def permission_names(self):
        if not self.role:
            return []
        base_permissions = {permission.permission_name for permission in self.role.permissions}
        delegated_permissions = {
            delegation.permission.permission_name
            for delegation in self.delegations_received
            if delegation.permission
            and not (
                delegation.permission.permission_name == "delegations.manage"
                and not ROLE_DELEGATION_ALLOWED_TARGETS.get(self.role.role_name, [])
            )
        }
        return sorted(base_permissions | delegated_permissions)
