# tests/test_companies.py
"""Company creation, invitations and membership.

Predates tests/conftest.py and had therefore never run: every test errored at setup on missing
fixtures. It also built its own module-level TestClient, which bypasses the get_db override and
so could not see the test transaction -- every request 401'd. Both are fixed by taking `client`
as a fixture instead.
"""
import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.company import Company
from app.models.companymember import CompanyMember
from datetime import datetime, timedelta


def test_create_company_as_guide(client, auth_guide_token, db):
    """Test: Guide puede crear una empresa"""
    response = client.post(
        "/api/companies/",
        json={
            "name": "Test Tours",
            "legal_name": "Test Tours LLC",
            "trade_name": "Test Tours",
            "entity_type": "llc",
            "incorporation_date": "2020-01-01",
            "country": "US",
            "currency": "USD",
            "address": "123 Test St",
            "legal_representive": "John Doe",
            "legal_representive_text": "123456789",
            "legal_representive_phone": "+1234567890",
            "is_multinational": False
        },
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Tours"
    assert data["license_tier"] == "free"
    # company.max_guides was dropped by migration 0001 (spec 2.9: "limits live in plan_limits
    # configuration, not a database column, so pricing changes need no migration"). The licence
    # endpoint is what answers this now.
    licence = client.get(
        f"/api/companies/{data['id']}/license",
        headers={"Authorization": f"Bearer {auth_guide_token}"},
    )
    assert licence.status_code == 200
    assert licence.json()["max_guides"] == 5


def test_create_company_as_user_fails(client, auth_user_token):
    """Test: User no puede crear empresa"""
    response = client.post(
        "/api/companies/",
        json={
            "name": "Test Tours",
            "legal_name": "Test Tours LLC",
            "trade_name": "Test Tours",
            "entity_type": "llc",
            "incorporation_date": "2020-01-01",
            "country": "CL",
            "currency": "CLP",
            "address": "123 Test St",
            "legal_representive": "John Doe",
            "legal_representive_text": "123456789",
            "legal_representive_phone": "+1234567890",
            "is_multinational": False,
        },
        headers={"Authorization": f"Bearer {auth_user_token}"}
    )
    
    # A valid payload, so this asserts authorisation rather than schema validation.
    assert response.status_code == 403


def test_invite_guide_success(client, auth_guide_token, company_id, db):
    """Test: Admin puede invitar guías"""
    response = client.post(
        f"/api/companies/{company_id}/invitations",
        json={
            "invited_email": "newguide@test.com",
            "expires_in_days": 7
        },
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    # 200, not 201: the endpoint declares response_model but no status_code, so FastAPI uses its
    # default. Arguably it should be 201 for a resource-creating POST -- left alone here because
    # changing it is an API contract change, not a test fix. See docs/DEMO_SETUP.md.
    assert response.status_code == 200
    data = response.json()
    assert data["invited_email"] == "newguide@test.com"
    assert data["status"] == "pending"
    assert "code" in data


def test_invite_duplicate_fails(client, auth_guide_token, company_id):
    """Test: No se puede invitar dos veces al mismo email"""
    # Primera invitación
    client.post(
        f"/api/companies/{company_id}/invitations",
        json={"invited_email": "test@test.com", "expires_in_days": 7},
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    # Segunda invitación (debe fallar)
    response = client.post(
        f"/api/companies/{company_id}/invitations",
        json={"invited_email": "test@test.com", "expires_in_days": 7},
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    assert response.status_code == 400


def test_accept_invitation_success(client, db, invitation_code, outsider_guide_token, outsider_guide, company_id):
    """Test: Guía puede aceptar invitación.

    Accepted by an unaffiliated guide: auth_guide_token belongs to the company's own owner, who is
    already a member, so accepting their own invitation correctly fails with 400.
    """
    response = client.post(
        "/api/companies/invitations/accept",
        json={"code": invitation_code},
        headers={"Authorization": f"Bearer {outsider_guide_token}"}
    )
    
    assert response.status_code == 200, response.text
    data = response.json()
    # The endpoint returns a confirmation envelope, not the membership row, so `is_active` was
    # never in this response. Assert the outcome that actually matters instead: the invitee is now
    # an active member of that company.
    assert data["status"] == "success"
    assert data["company_id"] == company_id

    membership = (
        db.query(CompanyMember)
        .filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == outsider_guide.id,
        )
        .first()
    )
    assert membership is not None, "accepting an invitation must create a membership"
    assert membership.is_active is True


def test_license_limit_validation(client, company_and_team, company_id, auth_guide_token, db):
    """Test: No se puede exceder el límite de guías en free tier.

    The cap is on ACTIVE MEMBERS (LicenseManager.can_add_guide counts CompanyMember rows), not on
    outstanding invitations -- an invited person is not a guide until they accept. The original
    version of this test sent six invitations and expected the sixth to be refused, which never
    touched the limit, since none of them created a member.

    Worth noting the gap this leaves: a company at its cap can still issue invitations that are
    guaranteed to fail on acceptance. Recorded in docs/DEMO_SETUP.md.
    """
    from tests.conftest import add_member, make_user

    company, team = company_and_team
    # Owner already counts as 1; free tier allows 5.
    for _ in range(4):
        add_member(db, team=team, company=company, user=make_user(db, role="guide"))

    response = client.post(
        f"/api/companies/{company_id}/invitations",
        json={"invited_email": "guide6@test.com", "expires_in_days": 7},
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )

    assert response.status_code == 402, response.text  # Payment Required


def test_remove_member_success(client, company_id, member_id, auth_admin_token):
    """Test: Admin puede remover miembros"""
    response = client.delete(
        f"/api/companies/{company_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {auth_admin_token}"}
    )
    
    assert response.status_code == 204


def test_cannot_remove_owner(client, company_id, owner_id, auth_admin_token):
    """Test: No se puede remover al owner de la empresa"""
    response = client.delete(
        f"/api/companies/{company_id}/members/{owner_id}",
        headers={"Authorization": f"Bearer {auth_admin_token}"}
    )
    
    assert response.status_code == 400