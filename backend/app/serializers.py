from datetime import datetime
from typing import Any


def serialize_model(item: Any) -> dict[str, Any]:
    result = {}
    for column in item.__table__.columns:
        value = getattr(item, column.name)
        result[column.name] = value.isoformat() if isinstance(value, datetime) else value
    return result
