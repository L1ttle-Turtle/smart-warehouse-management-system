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


class AuditLog(db.Model, SerializerMixin):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    target_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id = db.Column(db.Integer, index=True)
    entity_label = db.Column(db.String(255))
    description = db.Column(db.String(500), nullable=False)
    ip_address = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    actor_user = db.relationship(
        "User",
        foreign_keys=[actor_user_id],
        back_populates="audit_logs_actor",
    )
    target_user = db.relationship(
        "User",
        foreign_keys=[target_user_id],
        back_populates="audit_logs_target",
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
    expires_at = db.Column(db.DateTime)
    revoked_at = db.Column(db.DateTime)
    revoked_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    revoke_reason = db.Column(db.String(255))

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
    revoked_by_user = db.relationship("User", foreign_keys=[revoked_by_user_id])

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    @property
    def is_expired(self):
        return self.expires_at is not None and self.expires_at < utc_now()

    @property
    def is_active(self):
        return not self.is_revoked and not self.is_expired

    @property
    def status(self):
        if self.is_revoked:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "active"


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
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)
    password_changed_at = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)

    role = db.relationship("Role", back_populates="users")
    employee = db.relationship("Employee", back_populates="user", uselist=False)
    audit_logs_actor = db.relationship(
        "AuditLog",
        back_populates="actor_user",
        foreign_keys="AuditLog.actor_user_id",
    )
    audit_logs_target = db.relationship(
        "AuditLog",
        back_populates="target_user",
        foreign_keys="AuditLog.target_user_id",
    )
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

    def set_password(self, password, mark_changed=True):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        self.password_changed_at = utc_now() if mark_changed else None

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
            and delegation.is_active
            and not (
                delegation.permission.permission_name == "delegations.manage"
                and not ROLE_DELEGATION_ALLOWED_TARGETS.get(self.role.role_name, [])
            )
        }
        return sorted(base_permissions | delegated_permissions)
