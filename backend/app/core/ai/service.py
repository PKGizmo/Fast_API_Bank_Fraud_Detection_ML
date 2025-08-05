from uuid import UUID
from datetime import datetime, timezone
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.core.ai.models import TransactionRiskScore
from backend.app.core.ai.enums import AIReviewStatusEnum
from backend.app.core.ai.config import ai_settings
from backend.app.core.ai.transaction_analyzer import TransactionAnalyzer
from backend.app.transaction.models import Transaction
from backend.app.core.logging import get_logger
from backend.app.transaction.utils import mark_transaction_failed
from backend.app.transaction.enums import TransactionFailureReason

logger = get_logger()


class TransactionAIService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.analyzer = TransactionAnalyzer()

    async def analyze_transaction(
        self,
        transaction: Transaction,
        user_id: UUID,
    ) -> dict:
        try:
            risk_score, risk_factors = await self.analyzer.analyze_transaction(
                transaction,
                user_id,
                self.session,
            )

            risk_score_record = TransactionRiskScore(
                transaction_id=transaction.id,
                risk_score=risk_score,
                risk_factors=risk_factors,
                ai_model_version=ai_settings.MODEL_VERSION,
            )

            self.session.add(risk_score_record)

            needs_review = risk_score >= ai_settings.RISK_SCORE_TRESHOLD

            transaction.ai_review_status = (
                AIReviewStatusEnum.FLAGGED
                if needs_review
                else AIReviewStatusEnum.CLEARED
            )

            await self.session.commit()
            await self.session.refresh(risk_score_record)

            response = {
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "needs_review": needs_review,
                "recommendation": "block" if needs_review else "allow",
                "model_version": ai_settings.MODEL_VERSION,
                "score_id": risk_score_record.id,
            }

            if needs_review:
                logger.warning(
                    f"High risk transaction detected: {transaction.id}, "
                    f"Score: {risk_score}, Factors: {risk_factors}"
                )
            return response

        except Exception as e:
            logger.error(f"Error analyzing transaction: {e}")

            return {
                "risk_score": 0.8,  # High, just to be safe
                "risk_factors": {"error": str(e)},
                "needs_review": True,
                "recommendation": "block",
                "model_version": ai_settings.MODEL_VERSION,
                "error": str(e),
            }

    async def handle_flagged_transacion(
        self,
        transaction: Transaction,
        risk_analysis: dict,
    ) -> None:
        try:
            await mark_transaction_failed(
                transaction=transaction,
                reason=TransactionFailureReason.SUSPICIOUS_ACTIVITY,
                details={
                    "risk_score": risk_analysis["risk_score"],
                    "risk_factors": risk_analysis["risk_factors"],
                    "ai_model_version": risk_analysis["model_version"],
                },
                session=self.session,
                error_message="This transaction has been flagged as potentially fraudulent. An account executive will review the transaction, before it's either approved or rejected.",
            )

            transaction.ai_review_status = AIReviewStatusEnum.FLAGGED

            await self.session.commit()

        except Exception as e:
            logger.error(f"Error handling flagged transaction: {str(e)}")
            raise

    async def get_transaction_risk_history(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_risk_score: float | None = None,
    ) -> list[TransactionRiskScore]:
        try:
            query = (
                select(TransactionRiskScore)
                .join(Transaction)
                .where(Transaction.sender_id == user_id)
            )

            if start_date:
                query = query.where(TransactionRiskScore.created_at >= start_date)

            if end_date:
                query = query.where(TransactionRiskScore.created_at <= end_date)

            if min_risk_score:
                query = query.where(TransactionRiskScore.risk_score >= min_risk_score)

            result = await self.session.exec(query)

            return list(result)

        except Exception as e:
            logger.error(f"Error fetching risk history: {str(e)}")
            raise

    async def mark_confirmed_fraud(
        self,
        transaction_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> TransactionRiskScore:
        try:
            query = (
                select(Transaction, TransactionRiskScore)
                .join(TransactionRiskScore)
                .where(Transaction.id == transaction_id)
            )

            result = await self.session.exec(query)
            transaction_data = result.first()

            if not transaction_data:
                raise ValueError(
                    f"No risk score found for transaction {transaction_id}"
                )

            transaction, risk_score = transaction_data

            risk_score.is_confirmed_fraud = True
            risk_score.reviewed_by = reviewer_id

            if transaction:
                transaction.ai_review_status = AIReviewStatusEnum.CONFIRMED_FRAUD

                if not transaction.transaction_metadata:
                    transaction.transaction_metadata = {}

                transaction.transaction_metadata["fraud_review"] = {
                    "confirmed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": str(reviewer_id),
                    "notes": notes,
                }

            await self.session.commit()
            await self.session.refresh(risk_score)

            return risk_score

        except Exception as e:
            logger.error(f"Error marking confirmed fraud: {str(e)}")
            raise
