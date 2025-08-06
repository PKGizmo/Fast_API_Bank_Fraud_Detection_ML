from fastapi import APIRouter
from backend.app.api.routes import home
from backend.app.api.routes.auth import (
    register,
    activate,
    login,
    password_reset,
    refresh,
    logout,
)

from backend.app.api.routes.profile import (
    create,
    update,
    upload,
    me,
    all_profiles,
)

from backend.app.api.routes.next_of_kin import (
    create as create_next_of_kin,
    all as get_all_next_of_kins,
    update as update_next_of_kin,
    delete as delete_next_of_kin,
)

from backend.app.api.routes.bank_account import (
    create as create_bank_account,
    activate as activate_bank_account,
    deposit,
    transfer,
    withdrawal,
    transaction_history,
)

from backend.app.api.routes.bank_account import statement

from backend.app.api.routes.card import (
    create as create_vcard,
    activate as activate_vcard,
    block as block_vcard,
    delete as delete_vcard,
    topup as topup_vcard,
)

from backend.app.api.routes.transaction import (
    fraud_review,
    risk_history,
)

api_router = APIRouter()

api_router.include_router(home.router)
api_router.include_router(register.router)
api_router.include_router(activate.router)
api_router.include_router(login.router)
api_router.include_router(password_reset.router)
api_router.include_router(refresh.router)
api_router.include_router(logout.router)
api_router.include_router(create.router)
api_router.include_router(update.router)
api_router.include_router(upload.router)
api_router.include_router(me.router)
api_router.include_router(all_profiles.router)
api_router.include_router(create_next_of_kin.router)
api_router.include_router(get_all_next_of_kins.router)
api_router.include_router(update_next_of_kin.router)
api_router.include_router(delete_next_of_kin.router)
api_router.include_router(create_bank_account.router)
api_router.include_router(activate_bank_account.router)
api_router.include_router(deposit.router)
api_router.include_router(transfer.router)
api_router.include_router(withdrawal.router)
api_router.include_router(transaction_history.router)
api_router.include_router(statement.router)
api_router.include_router(create_vcard.router)
api_router.include_router(activate_vcard.router)
api_router.include_router(block_vcard.router)
api_router.include_router(topup_vcard.router)
api_router.include_router(delete_vcard.router)
api_router.include_router(fraud_review.router)
api_router.include_router(risk_history.router)
