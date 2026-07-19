# app/api/membership_requests.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team
from app.models.company import Company
from app.models.membership_request import MembershipRequest
from app.schemas.membership_request import (
    MembershipInviteCreate,
    MembershipApplyCreate,
    ConsentDecision,
    MembershipRequestOut,
    MembershipRequestsMineOut,
    DepartureStatusOut,
)
from app.services import membership_requests as svc
from app.services.team_departure import get_departure_block_reason, leave_team

router = APIRouter(prefix="/membership-requests", tags=["membership-requests"])


def _to_out(db: Session, req: MembershipRequest) -> MembershipRequestOut:
    team = db.query(Team).filter(Team.id == req.team_id).first()
    company = db.query(Company).filter(Company.id == req.company_id).first()
    target_user = (
        db.query(User).filter(User.id == req.target_user_id).first() if req.target_user_id else None
    )
    creator = db.query(User).filter(User.id == req.created_by).first()

    return MembershipRequestOut(
        id=req.id,
        direction=req.direction,
        team_id=req.team_id,
        company_id=req.company_id,
        target_user_id=req.target_user_id,
        target_email=req.target_email,
        offered_level=req.offered_level,
        created_by=req.created_by,
        on_behalf_of_company_id=req.on_behalf_of_company_id,
        target_consent=req.target_consent,
        message=req.message,
        status=req.status,
        expires_at=req.expires_at,
        responded_at=req.responded_at,
        created_at=req.created_at,
        team_name=team.name if team else None,
        company_name=company.name if company else None,
        target_display_name=(target_user.display_name or target_user.email) if target_user else req.target_email,
        created_by_display_name=(creator.display_name or creator.email) if creator else None,
    )


@router.post("/invite", response_model=MembershipRequestOut, status_code=status.HTTP_201_CREATED)
def invite(
    payload: MembershipInviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.create_invitation(
            db,
            team_id=payload.team_id,
            created_by=current_user,
            target_user_id=payload.target_user_id,
            target_email=payload.target_email,
            offered_level=payload.offered_level,
            message=payload.message,
            on_behalf_of_company_id=payload.on_behalf_of_company_id,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.post("/apply", response_model=MembershipRequestOut, status_code=status.HTTP_201_CREATED)
def apply(
    payload: MembershipApplyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.create_application(db, team_id=payload.team_id, applicant=current_user, message=payload.message)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.get("/mine", response_model=MembershipRequestsMineOut)
def mine(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incoming, outgoing, team_pending = svc.list_for_user(db, user=current_user)
    db.commit()
    return MembershipRequestsMineOut(
        incoming=[_to_out(db, r) for r in incoming],
        outgoing=[_to_out(db, r) for r in outgoing],
        team_pending=[_to_out(db, r) for r in team_pending],
    )


@router.post("/{request_id}/consent", response_model=MembershipRequestOut)
def respond_consent(
    request_id: UUID,
    payload: ConsentDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.consent(db, request_id=request_id, user=current_user, decision=payload.decision)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.post("/{request_id}/accept", response_model=MembershipRequestOut)
def accept(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.accept(db, request_id=request_id, actor=current_user)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.post("/{request_id}/reject", response_model=MembershipRequestOut)
def reject(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.reject(db, request_id=request_id, actor=current_user)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.post("/{request_id}/cancel", response_model=MembershipRequestOut)
def cancel(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = svc.cancel(db, request_id=request_id, actor=current_user)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(req)
    return _to_out(db, req)


@router.get("/departure-status", response_model=DepartureStatusOut)
def departure_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reason = get_departure_block_reason(db, current_user)
    return DepartureStatusOut(can_leave=reason is None, reason=reason)


@router.post("/leave-team", status_code=status.HTTP_204_NO_CONTENT)
def leave(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        leave_team(db, current_user)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    return None
