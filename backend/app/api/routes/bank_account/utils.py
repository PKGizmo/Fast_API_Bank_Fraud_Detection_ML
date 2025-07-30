from uuid import UUID
from fastapi import HTTPException, status


def validate_uuid4(value: str) -> str:
    try:
        uuid_obj = UUID(value, version=4)
        if str(uuid_obj) != value.lower():
            raise ValueError("Not a valid UUID v4")
        return value
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Idempotency-Key must be a valid UUID v4",
            },
        )
