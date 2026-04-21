from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from .security import validate_password_policy


class LoginSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))


class UserDelegationSchema(Schema):
    target_user_id = fields.Integer(required=True)
    permission_id = fields.Integer(required=True)
    note = fields.String(load_default="")
    expires_at = fields.DateTime(load_default=None, allow_none=True)


class RoleCreateSchema(Schema):
    role_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    description = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))


class ProfileUpdateSchema(Schema):
    email = fields.Email(load_default=None)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    current_password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=6, max=128))
    new_password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=8, max=128))

    @validates_schema
    def validate_password(self, data, **kwargs):
        new_password = data.get("new_password")
        if new_password:
            try:
                validate_password_policy(new_password)
            except ValueError as error:
                raise ValidationError({"new_password": [str(error)]}) from error


class UserCreateSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    role_id = fields.Integer(required=True)
    status = fields.String(
        load_default="active",
        validate=validate.OneOf(["active", "inactive"]),
    )

    @validates_schema
    def validate_password(self, data, **kwargs):
        password = data.get("password")
        if password:
            try:
                validate_password_policy(password)
            except ValueError as error:
                raise ValidationError({"password": [str(error)]}) from error


class UserUpdateSchema(Schema):
    username = fields.String(load_default=None, validate=validate.Length(min=3, max=80))
    password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(load_default=None, validate=validate.Length(min=2, max=120))
    email = fields.Email(load_default=None)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    role_id = fields.Integer(load_default=None)
    status = fields.String(load_default=None, validate=validate.OneOf(["active", "inactive"]))

    @validates_schema
    def validate_password(self, data, **kwargs):
        password = data.get("password")
        if password:
            try:
                validate_password_policy(password)
            except ValueError as error:
                raise ValidationError({"password": [str(error)]}) from error


class EmployeeCreateSchema(Schema):
    employee_code = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=2, max=30))
    user_id = fields.Integer(load_default=None, allow_none=True)
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=120))
    department = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    position = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    email = fields.Email(load_default=None, allow_none=True)
    status = fields.String(
        load_default="active",
        validate=validate.OneOf(["active", "inactive"]),
    )


class EmployeeUpdateSchema(Schema):
    employee_code = fields.String(load_default=None, validate=validate.Length(min=2, max=30))
    user_id = fields.Integer(load_default=None, allow_none=True)
    full_name = fields.String(load_default=None, validate=validate.Length(min=2, max=120))
    department = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    position = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=120))
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    email = fields.Email(load_default=None, allow_none=True)
    status = fields.String(load_default=None, validate=validate.OneOf(["active", "inactive"]))
