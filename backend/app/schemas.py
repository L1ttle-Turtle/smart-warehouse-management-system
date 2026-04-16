from marshmallow import Schema, fields, validate


class LoginSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(required=True, validate=validate.Length(min=6, max=128))


class UserDelegationSchema(Schema):
    target_user_id = fields.Integer(required=True)
    permission_id = fields.Integer(required=True)
    note = fields.String(load_default="")


class ProfileUpdateSchema(Schema):
    email = fields.Email(load_default=None)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    current_password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=6, max=128))
    new_password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=6, max=128))


class UserCreateSchema(Schema):
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=6, max=128))
    full_name = fields.String(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    role_id = fields.Integer(required=True)
    status = fields.String(
        load_default="active",
        validate=validate.OneOf(["active", "inactive"]),
    )


class UserUpdateSchema(Schema):
    username = fields.String(load_default=None, validate=validate.Length(min=3, max=80))
    password = fields.String(load_default=None, allow_none=True, validate=validate.Length(min=6, max=128))
    full_name = fields.String(load_default=None, validate=validate.Length(min=2, max=120))
    email = fields.Email(load_default=None)
    phone = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    role_id = fields.Integer(load_default=None)
    status = fields.String(load_default=None, validate=validate.OneOf(["active", "inactive"]))


class EmployeeCreateSchema(Schema):
    employee_code = fields.String(required=True, validate=validate.Length(min=2, max=30))
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
