from uuid import UUID
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from backend.app.next_of_kin.models import NextOfKin
from backend.app.next_of_kin.schema import NextOfKinCreateSchema, NextOfKinReadSchema
from backend.app.core.logging import get_logger

logger = get_logger()


async def get_next_of_kin_count(user_id: UUID, session: AsyncSession) -> int:
    statement = select(NextOfKin).where(NextOfKin.user_id == user_id)
    result = await session.exec(statement)
    return len(result.all())


async def get_primary_next_of_kin(
    user_id: UUID, session: AsyncSession
) -> NextOfKin | None:
    statement = select(NextOfKin).where(
        NextOfKin.user_id == user_id, NextOfKin.is_primary  # is True
    )

    result = await session.exec(statement)
    return result.first()


async def validate_next_of_kin_creation(
    user_id: UUID, is_primary: bool, session: AsyncSession
) -> None:
    """ "Function to check if user has maxed out allowed next of kin which is 3"""
    current_count = await get_next_of_kin_count(user_id, session)

    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Maximum number of kin (3) already reached.",
            },
        )

    if is_primary:
        existing_primary = await get_primary_next_of_kin(user_id, session)
        if existing_primary:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "A primary next of kin already exists.",
                },
            )


async def create_next_of_kin(
    user_id: UUID, next_of_kin_data: NextOfKinCreateSchema, session: AsyncSession
) -> NextOfKinReadSchema:
    try:
        current_count = await validate_next_of_kin_creation(
            user_id, next_of_kin_data.is_primary, session
        )

        if current_count == 0:
            next_of_kin_data.is_primary = True

        next_of_kin = NextOfKin(**next_of_kin_data.model_dump())
        next_of_kin.user_id = user_id

        session.add(next_of_kin)
        await session.commit()
        await session.refresh(next_of_kin)

        logger.info(f"Next of kin created successfully for user: {user_id}")

        return NextOfKinReadSchema.model_validate(next_of_kin)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Failed to create next of kin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to create next of kin",
            },
        )


async def get_user_next_of_kins(
    user_id: UUID,
    session: AsyncSession,
) -> list[NextOfKin]:
    try:
        statement = select(NextOfKin).where(NextOfKin.user_id == user_id)
        result = await session.exec(statement)
        next_of_kins = list(result.all())

        return next_of_kins
    except Exception as e:
        logger.error(f"Failed to retrieve next of kins: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to retrieve user next of kins",
            },
        )
