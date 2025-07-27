from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.core.logging import get_logger
from backend.app.core.db import get_session
from backend.app.api.routes.auth.dependencies import CurrentUser
from backend.app.api.services.next_of_kin import delete_next_of_kin
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger()

router = APIRouter(prefix="/next-of-kin", tags=["Next of Kin"])


@router.delete(
    "/{next_of_kin_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Delete a next of kin. Cannot delete if it's the only one remaining",
)
async def delete_next_of_kin_route(
    next_of_kin_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    try:
        await delete_next_of_kin(current_user.id, next_of_kin_id, session)

    except HTTPException as http_ex:
        logger.warning(
            f"Next of kin deletion failed for the user: {current_user.email}:{http_ex.detail}"
        )
        raise http_ex
    except Exception as e:
        logger.error(f"Failed to delete next of kin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to delete next of kin",
                "action": "Please try again later",
            },
        )
