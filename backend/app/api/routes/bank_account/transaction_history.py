from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.api.routes.auth.dependencies import CurrentUser
from backend.app.transaction.schema import (
    PaginatedTransactionResponseSchema,
    TransactionHistoryResponseSchema,
    TransactionFilterParamsSchema,
)

from backend.app.core.logging import get_logger
from backend.app.core.db import get_session
from backend.app.api.services.transaction import get_user_transactions

logger = get_logger()

router = APIRouter(prefix="/transactions")


@router.get(
    "/history",
    response_model=PaginatedTransactionResponseSchema,
    status_code=status.HTTP_200_OK,
    description="Get paginated transaction history for the authenticated user",
)
async def get_transaction_history(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    filters: TransactionFilterParamsSchema = Depends(),
) -> PaginatedTransactionResponseSchema:
    try:
        if (
            filters.start_date
            and filters.end_date
            and filters.start_date > filters.end_date
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Start date must be before end date",
                },
            )

        transactions, total_count = await get_user_transactions(
            user_id=current_user.id,
            session=session,
            skip=skip,
            limit=limit,
            start_date=filters.start_date,
            end_date=filters.end_date,
            transaction_type=filters.transaction_type,
            transaction_category=filters.transaction_category,
            transaction_status=filters.status,
            min_amount=filters.min_amount,
            max_amount=filters.max_amount,
        )

        transaction_responses = []

        for trn in transactions:
            metadata = trn.transaction_metadata or {}

            response = TransactionHistoryResponseSchema(
                id=trn.id,
                reference=trn.reference,
                amount=trn.amount,
                description=trn.description,
                transaction_type=trn.transaction_type,
                transaction_category=trn.transaction_category,
                transaction_status=trn.transaction_status,
                created_at=trn.created_at,
                completed_at=trn.completed_at,
                balance_after=trn.balance_after,
                currency=metadata.get("currency"),
                converted_amount=metadata.get("converted_amount"),
                from_currency=metadata.get("from_currency"),
                to_currency=metadata.get("to_currency"),
                counterparty_name=metadata.get("counterparty_name"),
                counterparty_account=metadata.get("counterparty_account"),
            )

            transaction_responses.append(response)

        return PaginatedTransactionResponseSchema(
            total=total_count,
            skip=skip,
            limit=limit,
            transactions=transaction_responses,
        )

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Error retrieving transaction history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to retrieve transaction history",
                "action": "Please try again later",
            },
        )
