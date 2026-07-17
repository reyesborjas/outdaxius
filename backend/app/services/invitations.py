# app/services/invitations.py
from sqlalchemy.orm import Session
from app.models.invitation import InvitationCode
from app.models.user import User
from app.models.companymember import CompanyMember
from app.models.company import Company
from datetime import datetime, timedelta, timezone
from uuid import UUID
import secrets
import string


class InvitationManager:
    """Manages company guide invitations"""
    
    @staticmethod
    def generate_code(length: int = 12) -> str:
        """Generate secure invitation code"""
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def create_invitation(
        db: Session,
        company_id: UUID,
        invited_email: str,
        created_by: UUID,
        expires_in_days: int = 7
    ) -> InvitationCode:
        """
        Create invitation for guide to join company
        
        Args:
            db: Database session
            company_id: Target company UUID
            invited_email: Email of guide to invite
            created_by: UUID of admin creating invitation
            expires_in_days: Validity period (default 7)
        
        Returns:
            InvitationCode object
        
        Raises:
            ValueError: If validation fails
        """
        
        # 1. Validate company
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError("Company not found")
        if not company.is_active:
            raise ValueError("Company is inactive")
        
        # 2. Check for duplicate active invitation
        existing = db.query(InvitationCode).filter(
            InvitationCode.company_id == company_id,
            InvitationCode.invited_email == invited_email.lower(),
            InvitationCode.status == 'pending',
            InvitationCode.expires_at > datetime.now(timezone.utc)
        ).first()
        
        if existing:
            raise ValueError(f"Active invitation exists for {invited_email}")
        
        # 3. Check if already a member
        user = db.query(User).filter(User.email == invited_email.lower()).first()
        if user:
            member = db.query(CompanyMember).filter(
                CompanyMember.companyid == company_id,
                CompanyMember.userid == user.id,
                CompanyMember.is_active == True
            ).first()
            
            if member:
                raise ValueError(f"{invited_email} is already a member")
        
        # 4. Generate unique code
        max_attempts = 10
        for _ in range(max_attempts):
            code = InvitationManager.generate_code()
            if not db.query(InvitationCode).filter(InvitationCode.code == code).first():
                break
        else:
            raise ValueError("Failed to generate unique code")
        
        # 5. Create invitation
        invitation = InvitationCode(
            code=code,
            company_id=company_id,
            invited_email=invited_email.lower(),
            created_by=created_by,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            status='pending'
        )
        
        db.add(invitation)
        db.flush()
        
        return invitation
    
    @staticmethod
    def accept_invitation(
        db: Session,
        code: str,
        user_id: UUID
    ) -> CompanyMember:
        """
        Accept invitation and create company membership
        
        Args:
            db: Database session
            code: Invitation code
            user_id: UUID of accepting user
        
        Returns:
            CompanyMember object
        
        Raises:
            ValueError: If validation fails
        """
        
        # 1. Find invitation
        invitation = db.query(InvitationCode).filter(
            InvitationCode.code == code
        ).first()
        
        if not invitation:
            raise ValueError("Invalid invitation code")
        
        if invitation.status != 'pending':
            raise ValueError(f"Invitation is {invitation.status}")
        
        if invitation.expires_at < datetime.now(timezone.utc):
            invitation.status = 'expired'
            db.flush()
            raise ValueError("Invitation has expired")
        
        # 2. Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        if user.role != "guide":
            raise ValueError("Only guides can accept company invitations")
        
        if user.email.lower() != invitation.invited_email.lower():
            raise ValueError("Email mismatch")
        
        # 3. Validate company
        company = db.query(Company).filter(Company.id == invitation.company_id).first()
        if not company or not company.is_active:
            raise ValueError("Company is not active")
        
        # 4. Check existing membership
        existing = db.query(CompanyMember).filter(
            CompanyMember.companyid == invitation.company_id,
            CompanyMember.userid == user_id
        ).first()
        
        if existing:
            if existing.is_active:
                raise ValueError("Already a member")
            else:
                # Reactivate
                existing.is_active = True
                existing.joinedat = datetime.now(timezone.utc).date()
                member = existing
        else:
            # Create membership
            member = CompanyMember(
                companyid=invitation.company_id,
                userid=user_id,
                position="Guide",
                is_admin=False,
                is_active=True,
                joinedat=datetime.now(timezone.utc).date()
            )
            db.add(member)
        
        # 5. Mark invitation as used
        invitation.status = 'accepted'
        invitation.used = True
        invitation.used_by = user_id
        invitation.used_at = datetime.now(timezone.utc)
        
        db.flush()
        return member