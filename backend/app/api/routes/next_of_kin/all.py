from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.core.logging import get_logger
from backend.app.core.db import get_session
from backend.app.next_of_kin.schema import NextOfKinReadSchema
from backend.app.api.routes.auth.dependencies import CurrentUser
from backend.app.api.services.next_of_kin import get_user_next_of_kins
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger()

router = APIRouter(prefix="/next-of-kin", tags=["Next of Kin"])


@router.get(
    "/all",
    response_model=list[NextOfKinReadSchema],
    status_code=status.HTTP_200_OK,
    description="Get all next of kins for the authenticated user",
)
async def list_next_of_kins(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[NextOfKinReadSchema]:
    try:
        next_of_kins = await get_user_next_of_kins(current_user.id, session)

        # return [NextOfKinReadSchema.model_validate(kin) for kin in next_of_kins]
        return list(NextOfKinReadSchema.model_validate(kin) for kin in next_of_kins)

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(
            f"Failed to retrieve next of kins for the user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to retrieve next of kins",
                "action": "Please try again later",
            },
        )
