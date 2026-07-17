# tests/test_companies.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.company import Company
from app.models.companymember import CompanyMember
from datetime import datetime, timedelta

client = TestClient(app)


def test_create_company_as_guide(auth_guide_token, db):
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
    assert data["max_guides"] == 5


def test_create_company_as_user_fails(auth_user_token):
    """Test: User no puede crear empresa"""
    response = client.post(
        "/api/companies/",
        json={"name": "Test", "legal_name": "Test"},
        headers={"Authorization": f"Bearer {auth_user_token}"}
    )
    
    assert response.status_code == 403


def test_invite_guide_success(auth_guide_token, company_id, db):
    """Test: Admin puede invitar guías"""
    response = client.post(
        f"/api/companies/{company_id}/invitations",
        json={
            "invited_email": "newguide@test.com",
            "expires_in_days": 7
        },
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["invited_email"] == "newguide@test.com"
    assert data["status"] == "pending"
    assert "code" in data


def test_invite_duplicate_fails(auth_guide_token, company_id):
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


def test_accept_invitation_success(invitation_code, auth_guide_token):
    """Test: Guía puede aceptar invitación"""
    response = client.post(
        "/api/companies/invitations/accept",
        json={"code": invitation_code},
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] == True


def test_license_limit_validation(company_id, auth_guide_token, db):
    """Test: No se puede exceder el límite de guías en free tier"""
    # Crear 5 miembros (límite free tier)
    for i in range(5):
        client.post(
            f"/api/companies/{company_id}/invitations",
            json={"invited_email": f"guide{i}@test.com", "expires_in_days": 7},
            headers={"Authorization": f"Bearer {auth_guide_token}"}
        )
    
    # Intentar invitar el 6to (debe fallar)
    response = client.post(
        f"/api/companies/{company_id}/invitations",
        json={"invited_email": "guide6@test.com", "expires_in_days": 7},
        headers={"Authorization": f"Bearer {auth_guide_token}"}
    )
    
    assert response.status_code == 402  # Payment Required


def test_remove_member_success(company_id, member_id, auth_admin_token):
    """Test: Admin puede remover miembros"""
    response = client.delete(
        f"/api/companies/{company_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {auth_admin_token}"}
    )
    
    assert response.status_code == 204


def test_cannot_remove_owner(company_id, owner_id, auth_admin_token):
    """Test: No se puede remover al owner de la empresa"""
    response = client.delete(
        f"/api/companies/{company_id}/members/{owner_id}",
        headers={"Authorization": f"Bearer {auth_admin_token}"}
    )
    
    assert response.status_code == 400