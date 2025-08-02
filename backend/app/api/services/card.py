from uuid import UUID
import uuid
from datetime import datetime, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status
from decimal import Decimal

from backend.app.virtual_card.models import VirtualCard
from backend.app.bank_account.models import BankAccount
from backend.app.auth.models import User
from backend.app.transaction.models import Transaction
from backend.app.transaction.enums import (
    TransactionCategoryEnum,
    TransactionStatusEnum,
    TransactionTypeEnum,
)
from backend.app.virtual_card.enums import VirtualCardStatusEnum
from backend.app.bank_account.enums import BankAccountStatusEnum
from backend.app.auth.schema import RoleChoicesEnum
from backend.app.virtual_card.utils import (
    generate_visa_card_number,
    generate_cvv,
    generate_card_expiry_date,
)

from backend.app.core.logging import get_logger


logger = get_logger()


async def create_virtual_card(
    user_id: UUID,
    bank_account_id: UUID,
    card_data: dict,
    session: AsyncSession,
) -> tuple[VirtualCard, User, BankAccount]:
    try:
        statement = (
            select(BankAccount, User)
            .join(User)
            .where(
                BankAccount.id == bank_account_id,
                BankAccount.user_id == user_id,
            )
        )
        result = await session.exec(statement)

        account_user = result.first()

        if not account_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Bank account not found or does not belong to the user",
                },
            )

        bank_account, user = account_user

        if bank_account.account_status != BankAccountStatusEnum.Active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"status": "error", "message": "Bank account is not active"},
            )

        card_currency = card_data.get("currency")

        if card_currency != bank_account.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Card currency must match bank account currency",
                },
            )

        cleaned_data = card_data.copy()
        cleaned_data.pop("card_number", None)
        cleaned_data.pop("card_status", None)
        cleaned_data.pop("is_active", None)
        cleaned_data.pop("cvv_hash", None)
        cleaned_data.pop("available_balance", None)
        cleaned_data.pop("total_topped_up", None)
        cleaned_data.pop("card_metadata", None)

        card_number = generate_visa_card_number()

        if not cleaned_data.get("expiry_date"):
            expiry_date = generate_card_expiry_date()
            cleaned_data["expiry_date"] = expiry_date.date()

        card = VirtualCard(
            **cleaned_data,
            card_number=card_number,
            bank_account_id=bank_account_id,
            card_status=VirtualCardStatusEnum.Pending,
            is_active=True,
            available_balance=0.0,
            total_topped_up=0.0,
            last_top_up_date=datetime.now(timezone.utc),
            card_metadata={
                "created_by": str(user_id),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        session.add(card)
        await session.commit()
        await session.refresh(card)

        return card, user, bank_account

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to create virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to create virtual card",
            },
        )


async def block_virtual_card(
    card_id: UUID,
    block_data: dict,
    blocked_by: UUID,
    session: AsyncSession,
) -> tuple[VirtualCard, User]:
    try:
        statement = (
            select(VirtualCard, User)
            .select_from(VirtualCard)  # Ensuring correct order of joins
            .join(BankAccount)  # Connect Virtual Card to Bank Account table
            .join(User)  # Connects Bank Account to the User table
            .where(VirtualCard.id == card_id)
        )
        result = await session.exec(statement)
        card_data = result.first()

        if not card_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"status": "error", "message": "Virtual card not found"},
            )

        card, card_owner = card_data

        if card.card_status == VirtualCardStatusEnum.Blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Virtual card is already blocked",
                },
            )

        block_time = datetime.now(timezone.utc)
        card.card_status = VirtualCardStatusEnum.Blocked

        card.block_reason = block_data["block_reason"]
        card.block_reason_description = block_data["block_reason_description"]
        card.blocked_by = blocked_by
        card.blocked_at = block_time

        if not card.card_metadata:
            card.card_metadata = {}

        card.card_metadata.update(
            {
                "blocked_at": block_time.isoformat(),
                "blocked_by": blocked_by,
                "block_reason": block_data["block_reason"].value,
            }
        )

        session.add(card)
        await session.commit()
        await session.refresh(card)

        return card, card_owner

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to block virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to block virtual card",
            },
        )


async def top_up_virtual_card(
    card_id: UUID,
    account_number: str,
    amount: float,
    description: str,
    session: AsyncSession,
) -> tuple[VirtualCard, Transaction]:
    try:
        statement = (
            select(VirtualCard, BankAccount)
            .join(BankAccount)
            .where(
                VirtualCard.id == card_id,
                BankAccount.account_number == account_number,
            )
        )
        result = await session.exec(statement)

        card_account = result.first()

        if not card_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Virtual card or bank account not found",
                },
            )

        card, bank_account = card_account

        if card.card_status != VirtualCardStatusEnum.Active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Virtual card is not active",
                },
            )

        if bank_account.account_status != BankAccountStatusEnum.Active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Bank account is not active",
                },
            )

        if Decimal(str(bank_account.account_balance)) < Decimal(str(amount)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Insufficient balance in bank account",
                },
            )

        if card.currency != bank_account.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Currency mismatch between virtual card and bank account",
                },
            )

        reference = f"TOPUP{uuid.uuid4().hex[:8].upper()}"

        balance_before = Decimal(str(bank_account.account_balance))
        balance_after = balance_before - Decimal(str(amount))
        current_time = datetime.now(timezone.utc)

        transaction = Transaction(
            amount=Decimal(str(amount)),
            description=description,
            reference=reference,
            transaction_type=TransactionTypeEnum.Transfer,
            transaction_category=TransactionCategoryEnum.Debit,
            transaction_status=TransactionStatusEnum.Completed,
            balance_before=balance_before,
            balance_after=balance_after,
            sender_account_id=bank_account.id,
            sender_id=bank_account.user_id,
            completed_at=current_time,
            transaction_metadata={
                "top_up_type": "virtual_card",
                "card_id": str(card.id),
                "card_last_four": card.last_four_digits,
                "currency": card.currency.value,
            },
        )

        bank_account.account_balance = float(balance_after)
        card.available_balance += amount
        card.total_topped_up += amount

        card.last_top_up_date = current_time

        session.add(transaction)
        session.add(bank_account)
        session.add(card)
        await session.commit()
        await session.refresh(transaction)
        await session.refresh(card)

        return card, transaction

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to top up virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to process virtual card top-up",
            },
        )


async def activate_virtual_card(
    card_id: UUID,
    activated_by: UUID,
    session: AsyncSession,
) -> tuple[VirtualCard, User, str]:
    try:
        statement = (
            select(VirtualCard, BankAccount, User)
            .select_from(VirtualCard)
            .join(BankAccount)
            .join(User)
            .where(VirtualCard.id == card_id)
        )

        result = await session.exec(statement)
        card_data = result.first()

        if not card_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Virtual card not found",
                },
            )

        card, bank_account, card_owner = card_data

        executive = await session.get(User, activated_by)

        if not executive or executive.role != RoleChoicesEnum.ACCOUNT_EXECUTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status": "error",
                    "message": "Only account executives can activate virtual cards",
                },
            )

        if card.card_status == VirtualCardStatusEnum.Active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Virtual card is already active",
                },
            )

        new_cvv, cvv_hash = generate_cvv()

        card.card_status = VirtualCardStatusEnum.Active
        card.cvv_hash = cvv_hash

        if not card.card_metadata:
            card.card_metadata = {}

        card.card_metadata.update(
            {
                "activated_by": str(activated_by),
                "activated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        session.add(card)
        await session.commit()
        await session.refresh(card)

        return card, card_owner, new_cvv

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to activate virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to activate virtual card",
            },
        )


async def delete_virtual_card(
    card_id: UUID,
    user_id: UUID,
    session: AsyncSession,
) -> dict:
    try:
        statement = (
            select(VirtualCard, BankAccount)
            .join(BankAccount)
            .where(
                VirtualCard.id == card_id,
                BankAccount.user_id == user_id,
            )
        )
        result = await session.exec(statement)

        card_account = result.first()

        if not card_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "status": "error",
                    "message": "Virtual card not found or does not belong to the user",
                },
            )

        card, _ = card_account

        if card.physical_card_requested_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Cannot delete virtual card with physical card request",
                },
            )

        if card.available_balance > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "status": "error",
                    "message": "Cannot delete virtual card with remaining balance",
                    "action": "Please withdraw remaining balance first",
                },
            )

        deletion_time = datetime.now(timezone.utc)

        existing_metadata = card.card_metadata or {}

        new_metadata = {
            **existing_metadata,
            "deleted_at": deletion_time.isoformat(),
            "deletion_reason": "user_requested",
            "deleted_by": str(user_id),
            "card_status_before_deletion": card.card_status.value,
            "deletion_timestamp": deletion_time.timestamp(),
        }

        card.card_metadata = new_metadata

        card.card_status = VirtualCardStatusEnum.Inactive
        card.is_active = False

        session.add(card)
        await session.commit()
        await session.refresh(card)

        logger.info(f"Virtual card {card_id} soft deleted successfully")

        return {
            "status": "success",
            "message": "Virtual card deleted successfully",
            "deleted_at": deletion_time,
        }

    except HTTPException:
        await session.rollback()
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to delete virtual card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to delete virtual card",
            },
        )
