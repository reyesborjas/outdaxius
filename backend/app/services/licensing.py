# app/services/licensing.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.company import Company
from app.models.companymember import CompanyMember
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID
from app.services.plan_limits import normalize_tier

def _normalize_tier(tier: str | None) -> str:
    t = (tier or "basic").strip().lower()
    if t in {"free", "freemium"}:
        return "basic"
    return t

class LicenseManager:
    """Manages company licensing and guide limits. Per spec 2.9, company.max_guides was dropped
    from the database -- "limits live in plan_limits configuration, not in a database column, so
    pricing changes need no migration." This table is that configuration."""

    TIER_MAX_GUIDES = {
        "basic": 5,
        "pro": 50,
        "enterprise": None,
    }

    @staticmethod
    def get_company_license_info(db: Session, company_id: UUID) -> Dict:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")

        current_count = db.query(func.count(CompanyMember.id)).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.is_active == True
        ).scalar()

        tier = normalize_tier(company.license_tier)
        max_guides = LicenseManager.TIER_MAX_GUIDES.get(tier, LicenseManager.TIER_MAX_GUIDES["basic"])

        return {
            "tier": tier,
            "max_guides": max_guides,
            "current_guides": current_count,
            "can_add_guides": (max_guides is None) or (current_count < max_guides),
            "is_active": company.is_active,
            "expires_at": company.subscription_expires_at,
        }

    @staticmethod
    def can_add_guide(db: Session, company_id: UUID) -> bool:
        info = LicenseManager.get_company_license_info(db, company_id)

        if not info["is_active"]:
            return False

        if info["expires_at"] and info["expires_at"] < datetime.now(timezone.utc):
            return False

        return bool(info["can_add_guides"])

    @staticmethod
    def validate_license(db: Session, company_id: UUID) -> None:
        if not LicenseManager.can_add_guide(db, company_id):
            info = LicenseManager.get_company_license_info(db, company_id)

            if not info["is_active"]:
                raise ValueError("Company license is inactive")

            if info["expires_at"] and info["expires_at"] < datetime.now(timezone.utc):
                raise ValueError("Company license has expired")

            raise ValueError(
                f"Company has reached maximum guides limit ({info['max_guides']}) "
                f"for {info['tier']} tier"
            )
