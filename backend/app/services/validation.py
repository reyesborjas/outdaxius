# app/services/validation.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.companymember import CompanyMember
from app.models.invitation import InvitationCode
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID


class ValidationError(Exception):
    """Custom validation error"""
    pass


class CompanyValidations:
    """Validaciones de negocio para empresas"""
    
    @staticmethod
    def validate_unique_active_membership(
        db: Session,
        user_id: UUID,
        company_id: UUID
    ) -> None:
        """Valida que el usuario no sea ya miembro activo"""
        existing = db.query(CompanyMember).filter(
            CompanyMember.userid == user_id,
            CompanyMember.companyid == company_id,
            CompanyMember.is_active == True
        ).first()
        
        if existing:
            raise ValidationError("User is already an active member of this company")
    
    @staticmethod
    def validate_no_pending_invitation(
        db: Session,
        email: str,
        company_id: UUID
    ) -> None:
        """Valida que no exista una invitación pendiente para este email"""
        existing = db.query(InvitationCode).filter(
            InvitationCode.company_id == company_id,
            InvitationCode.invited_email == email.lower(),
            InvitationCode.status == 'pending',
            InvitationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if existing:
            raise ValidationError(
                f"A pending invitation already exists for {email}"
            )
    
    @staticmethod
    def validate_guides_limit(
        db: Session,
        company_id: UUID,
        max_guides: int
    ) -> None:
        """Valida que no se exceda el límite de guías"""
        current_count = db.query(func.count(CompanyMember.id)).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.is_active == True
        ).scalar()
        
        if current_count >= max_guides:
            raise ValidationError(
                f"Company has reached maximum guides limit ({max_guides})"
            )
    
    @staticmethod
    def validate_invitation_code(
        db: Session,
        code: str
    ) -> InvitationCode:
        """Valida que el código de invitación sea válido"""
        invitation = db.query(InvitationCode).filter(
            InvitationCode.code == code
        ).first()
        
        if not invitation:
            raise ValidationError("Invalid invitation code")
        
        if invitation.status != 'pending':
            raise ValidationError(f"Invitation is {invitation.status}")
        
        if invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = 'expired'
            db.flush()
            raise ValidationError("Invitation has expired")
        
        if invitation.used:
            raise ValidationError("Invitation has already been used")
        
        return invitation
    
    @staticmethod
    def validate_email_match(
        invitation: InvitationCode,
        user_email: str
    ) -> None:
        """Valida que el email del usuario coincida con la invitación"""
        if invitation.invited_email:
            if user_email.lower() != invitation.invited_email.lower():
                raise ValidationError(
                    "This invitation is for a different email address"
                )