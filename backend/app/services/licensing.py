# app/services/licensing.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.company import Company
from app.models.companymember import CompanyMember
from app.models.invitation import InvitationCode
from datetime import datetime, timezone
from typing import Dict
from uuid import UUID
from app.services.plan_limits import normalize_tier

def _normalize_tier(tier: str | None) -> str:
    t = (tier or "basic").strip().lower()
    if t in {"free", "freemium"}:
        return "basic"
    return t

class LicenseLimitError(ValueError):
    """A licence/seat-limit refusal, as opposed to a plain validation failure.

    Subclasses ValueError so existing `except ValueError` handlers keep working, while callers
    that care can answer 402 Payment Required rather than 400 Bad Request -- the difference
    between "you did something wrong" and "you need a bigger plan".
    """


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

        # An outstanding invitation reserves a seat. Without this a company with two seats left
        # could issue fifty invitations, turning the last places into a race and leaving everyone
        # else holding an invitation that can never be honoured. Expired invitations release
        # their seat, so an unanswered invite cannot hold one forever.
        pending_invitations = db.query(func.count(InvitationCode.id)).filter(
            InvitationCode.company_id == company_id,
            InvitationCode.status == "pending",
            InvitationCode.used == False,  # noqa: E712
            InvitationCode.expires_at > datetime.now(timezone.utc),
        ).scalar()

        tier = normalize_tier(company.license_tier)
        max_guides = LicenseManager.TIER_MAX_GUIDES.get(tier, LicenseManager.TIER_MAX_GUIDES["basic"])
        seats_taken = current_count + pending_invitations

        return {
            "tier": tier,
            "max_guides": max_guides,
            "current_guides": current_count,
            "pending_invitations": pending_invitations,
            "seats_taken": seats_taken,
            # Two distinct questions, deliberately not the same number:
            #   can_add_guides    -- may one more person BECOME a member right now? Counts members
            #                        only, because the invitation being accepted is still pending
            #                        and would otherwise count against itself.
            #   can_invite_guides -- may another invitation be ISSUED? Counts reserved seats too.
            "can_add_guides": (max_guides is None) or (current_count < max_guides),
            "can_invite_guides": (max_guides is None) or (seats_taken < max_guides),
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
    def can_invite_guide(db: Session, company_id: UUID) -> bool:
        """Whether another invitation may be issued -- members plus reserved seats."""
        info = LicenseManager.get_company_license_info(db, company_id)

        if not info["is_active"]:
            return False

        if info["expires_at"] and info["expires_at"] < datetime.now(timezone.utc):
            return False

        return bool(info["can_invite_guides"])

    @staticmethod
    def _raise_for(info: Dict, *, reason: str) -> None:
        if not info["is_active"]:
            raise LicenseLimitError("Company license is inactive")

        if info["expires_at"] and info["expires_at"] < datetime.now(timezone.utc):
            raise LicenseLimitError("Company license has expired")

        raise LicenseLimitError(reason)

    @staticmethod
    def validate_license(db: Session, company_id: UUID) -> None:
        """Gate on ISSUING an invitation."""
        if not LicenseManager.can_invite_guide(db, company_id):
            info = LicenseManager.get_company_license_info(db, company_id)
            LicenseManager._raise_for(
                info,
                reason=(
                    f"Company has reached maximum guides limit ({info['max_guides']}) for "
                    f"{info['tier']} tier: {info['current_guides']} member(s) plus "
                    f"{info['pending_invitations']} outstanding invitation(s)."
                ),
            )

    @staticmethod
    def validate_can_add_member(db: Session, company_id: UUID) -> None:
        """Gate on somebody actually BECOMING a member.

        This is the authoritative check. Validating only at invitation time left the cap
        bypassable outright: a company under its limit could issue any number of invitations and
        every one of them would be accepted.
        """
        if not LicenseManager.can_add_guide(db, company_id):
            info = LicenseManager.get_company_license_info(db, company_id)
            LicenseManager._raise_for(
                info,
                reason=(
                    f"Company has reached maximum guides limit ({info['max_guides']}) for "
                    f"{info['tier']} tier."
                ),
            )
