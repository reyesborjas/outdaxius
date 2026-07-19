# backend/app/api/routes/__init__.py
from fastapi import APIRouter

from app.api.locations import router as locations_router
from app.api.activities import router as activities_router
from app.api.users import router as users_router
from app.api.programs import router as programs_router
from app.api.roles import router as roles_router
from app.api.company import router as company_router  # ✅ CRÍTICO: Verificar esta línea
from app.api import auth
from app.api import program_schedules, activity_schedules
from app.api import booking
from app.api import types
from app.api import companymember
from app.api import company_payments, payments_flow
from app.api import membership_requests
# NOTE: app.api.payment_stripe is intentionally NOT registered and remains unmounted dead code.
# It targeted a Stripe-Connect marketplace architecture (destination charges,
# company.stripe_account_id) that the spec rejects in favor of per-company merchant-of-record +
# Flow-first. The real replacement is company_payments.py + payments_flow.py, below (Phase 4).

router = APIRouter()

# Core routers
router.include_router(locations_router, prefix="/locations", tags=["locations"])
router.include_router(activities_router, prefix="/activities", tags=["activities"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(programs_router, prefix="/programs", tags=["programs"])
router.include_router(types.router, prefix="/types", tags=["types"]) 

# ✅ CRÍTICO: Esta línea debe estar presente
router.include_router(company_router)
router.include_router(companymember.router)
router.include_router(company_payments.router)
router.include_router(payments_flow.router)
router.include_router(membership_requests.router)

# New schedule structure
router.include_router(program_schedules.router, prefix="/program-schedules", tags=["program-schedules"])
router.include_router(activity_schedules.router, prefix="/activity-schedules", tags=["activity-schedules"])

# Other modules
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(booking.router, prefix="/bookings", tags=["bookings"])
router.include_router(roles_router, prefix="/roles", tags=["roles"])