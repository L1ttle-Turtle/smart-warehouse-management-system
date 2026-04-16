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
