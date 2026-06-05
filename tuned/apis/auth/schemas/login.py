from marshmallow import Schema, fields, validates, post_load, ValidationError
from typing import Any


class LoginSchema(Schema):
    identifier = fields.Str(load_default=None)
    email = fields.Str(load_default=None)   # accepted as alias for identifier
    password = fields.Str(required=True, load_only=True)
    remember_me = fields.Bool(load_default=False)

    @post_load
    def normalize_identifier(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        if not data.get('identifier') and data.get('email'):
            data['identifier'] = data.pop('email')
        elif 'email' in data:
            data.pop('email', None)
        return data

    @validates('password')
    def validate_password_field(self, value: str, **kwargs: Any) -> None:
        if not value:
            raise ValidationError('Password is required')

    def load(self, data: Any, **kwargs: Any) -> Any:
        result = super().load(data, **kwargs)
        if not result.get('identifier'):
            raise ValidationError({'identifier': ['Email or username is required']})
        return result
