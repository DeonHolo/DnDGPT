"""Strict JSON-to-dataclass construction shared by mechanical contracts."""
from dataclasses import MISSING, fields


def text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 20000:
        raise ValueError(f"{name} must be nonblank text of at most 20000 characters")
    return value


def items(value, name, size=None):
    if type(value) is not tuple or (size is not None and len(value) != size):
        raise ValueError(f"{name} must be an immutable tuple" + (f" of {size} entries" if size is not None else ""))
    return value


def sequence(value):
    if type(value) is not list:
        raise ValueError("Expected a JSON array")
    return tuple(value)


def pairs(value):
    rows = sequence(value)
    if any(type(row) is not list or len(row) != 2 for row in rows):
        raise ValueError("Expected key/value pairs")
    keys = [row[0] for row in rows]
    if any(type(key) is not str for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("Pair keys must be unique strings")
    return tuple(tuple(row) for row in rows)


def construct(cls, value, conversions=None):
    if type(value) is not dict:
        raise ValueError(f"Expected {cls.__name__} object")
    definitions = fields(cls)
    allowed = {field.name for field in definitions}
    required = {field.name for field in definitions
                if field.default is MISSING and field.default_factory is MISSING}
    if not required <= value.keys() or value.keys() - allowed:
        raise ValueError(f"Invalid {cls.__name__} fields")
    data = dict(value)
    for name, convert in (conversions or {}).items():
        if name in data:
            data[name] = convert(data[name])
    return cls(**data)
