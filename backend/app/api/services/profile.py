import uuid
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from backend.app.user_profile.models import Profile
from backend.app.user_profile.schema import ProfileCreateSchema
from backend.app.core.logging import get_logger

logger = get_logger()


async def get_user_profile(user_id: uuid.UUID, session: AsyncSession) -> Profile | None:
    try:
        statement = select(Profile).where(Profile.user_id == user_id)
        result = await session.exec(statement)
        return result.first()

    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to fetch user profile",
            },
        )


async def create_user_profile(
    user_id: uuid.UUID,
    profile_data: ProfileCreateSchema,
    session: AsyncSession,
) -> Profile:
    try:
        existing_profile = await get_user_profile(user_id, session)

        if existing_profile:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Profile already exists for this user",
                },
            )
        profile_data_dict = profile_data.model_dump()
        profile = Profile(user_id=user_id, **profile_data_dict)
        session.add(profile)

        await session.commit()
        await session.refresh(profile)

        logger.info(f"Created profile for user {user_id}")

        return profile

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to create user profile",
            },
        )
