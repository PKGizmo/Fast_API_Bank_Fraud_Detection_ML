from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header
from datetime import timezone, timedelta, datetime
from decimal import Decimal
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.core.db import get_session
from backend.app.core.logging import get_logger

from backend.app.api.routes.auth.dependencies import CurrentUser
from backend.app.transaction.schema import WithdrawalRequestSchema


from backend.app.core.services.withdrawal_alert import send_withdrawal_alert
from backend.app.api.services.transaction import process_withdrawal
from backend.app.transaction.models import IdempotencyKey

from backend.app.api.routes.bank_account.utils import validate_uuid4

logger = get_logger()

router = APIRouter(prefix="/bank-account")


@router.post("/withdraw", status_code=status.HTTP_201_CREATED)
async def create_withdrawal(
    withdrawal_data: WithdrawalRequestSchema,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str = Header(
        description="Idempotency key for the withdrawal request"
    ),
):
    try:
        idempotency_key = validate_uuid4(idempotency_key)

        if not idempotency_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Idempotency-Key header is required",
                },
            )

        existing_key_result = await session.exec(
            select(IdempotencyKey).where(
                IdempotencyKey.key == idempotency_key,
                IdempotencyKey.endpoint == "/withdraw",
                IdempotencyKey.expires_at > datetime.now(timezone.utc),
            )
        )

        existing_key = existing_key_result.first()

        if existing_key:
            return {
                "status": "success",
                "message": "Retrieved from cache",
                "data": existing_key.response_body,
            }

        transaction, account, user = await process_withdrawal(
            account_number=withdrawal_data.account_number,
            amount=withdrawal_data.amount,
            username=withdrawal_data.username,
            description=withdrawal_data.description,
            session=session,
        )

        try:
            await send_withdrawal_alert(
                email=user.email,
                full_name=user.full_name,
                amount=transaction.amount,
                account_name=account.account_name,
                account_number=account.account_number or "Unknown",
                currency=account.currency.value,
                description=transaction.description,
                transaction_date=transaction.completed_at or transaction.created_at,
                reference=transaction.reference,
                balance=Decimal(str(account.account_balance)),
            )

        except Exception as e:
            logger.error(f"Failed to send withdrawal alert: {e}")

        response = {
            "status": "success",
            "message": "Withdrawal processed successfully",
            "data": {
                "transaction_id": str(transaction.id),
                "reference": transaction.reference,
                "amount": str(transaction.amount),
                "balance": str(transaction.balance_after),
                "status": transaction.transaction_status.value,
            },
        }

        idempotency_record = IdempotencyKey(
            key=idempotency_key,
            user_id=user.id,
            endpoint="/withdraw",
            response_code=status.HTTP_201_CREATED,
            response_body=response,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        session.add(idempotency_record)

        await session.commit()
        return response

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        logger.error(f"Failed to process withdrawal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to process withdrawal",
            },
        )
