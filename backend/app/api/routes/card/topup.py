from uuid import UUID
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from backend.app.core.logging import get_logger
from backend.app.core.db import get_session
from backend.app.api.routes.bank_account.utils import validate_uuid4

from backend.app.api.routes.auth.dependencies import CurrentUser

from backend.app.api.services.card import top_up_virtual_card
from backend.app.virtual_card.schema import (
    CardTopupResponseSchema,
    CardTopUpSchema,
)
from backend.app.transaction.models import IdempotencyKey


logger = get_logger()

router = APIRouter(prefix="/virtual-card")


@router.post(
    "/{card_id}/top-up",
    response_model=CardTopupResponseSchema,
    status_code=status.HTTP_200_OK,
    description="Top up a virtual card from a bank account. Card must be active.",
)
async def top_up_card(
    card_id: UUID,
    top_up_data: CardTopUpSchema,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str = Header(
        description="Idempotency key for the top-up request.",
    ),
) -> CardTopupResponseSchema:
    try:
        idempotency_key = validate_uuid4(idempotency_key)

        if not idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Idempotency key header is requiered",
                },
            )
        existing_key_result = await session.exec(
            select(IdempotencyKey).where(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.user_id == current_user.id,
                IdempotencyKey.endpoint == "/virtual-card/top-up",
                IdempotencyKey.expires_at > datetime.now(timezone.utc),
            )
        )

        existing_key = existing_key_result.first()

        if existing_key:
            return CardTopupResponseSchema(
                status="success",
                message="Retrieved from cache",
                data=existing_key.response_body,
            )

        card, transaction = await top_up_virtual_card(
            card_id=card_id,
            account_number=top_up_data.account_number,
            amount=top_up_data.amount,
            description=top_up_data.description,
            session=session,
        )

        response = CardTopupResponseSchema(
            status="success",
            message="Card topped-up successfully",
            data={
                "card_id": str(card.id),
                "transaction_id": str(transaction.id),
                "amount": str(transaction.amount),
                "new_balance": str(card.available_balance),
                "reference": transaction.reference,
            },
        )

        idempotency_record = IdempotencyKey(
            key=idempotency_key,
            user_id=current_user.id,
            endpoint="/virtual-card/top-up",
            response_code=status.HTTP_200_OK,
            response_body=response.model_dump(),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        session.add(idempotency_record)
        await session.commit()

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to top up virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to top up virtual card",
            },
        )
