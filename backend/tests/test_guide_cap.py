# backend/tests/test_guide_cap.py
"""
The guide cap holds against the invitation path.

Two separate holes existed here.

The serious one: accept_invitation never checked the cap at all. Only invitation *creation*
called validate_license, and that counted active members. So a company under its cap could issue
any number of invitations and every one of them would be accepted, taking the company well past
the limit -- the cap was bypassable, not merely leaky.

The second: invitations were not counted as reserved seats, so a company with two seats left
could issue fifty invitations. Even with acceptance now enforced, that turns the last seats into
a race between invitees and leaves the rest with an invitation that cannot be honoured.

The free/basic tier allows 5 guides (LicenseManager.TIER_MAX_GUIDES); the company owner is
already one of them.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.companymember import CompanyMember
from app.models.invitation import InvitationCode
from app.services.licensing import LicenseManager
from tests.conftest import TEST_PASSWORD, add_member, auth, make_company, make_user

FREE_TIER_MAX = 5


@pytest.fixture()
def company_at(db, guide_user):
    """A free-tier company, with a helper to fill it to a given number of members."""
    company, team = make_company(db, owner=guide_user, name="Capped Co", tier="free")

    def fill_to(total_members: int):
        current = (
            db.query(CompanyMember)
            .filter(CompanyMember.companyid == company.id, CompanyMember.is_active.is_(True))
            .count()
        )
        for _ in range(total_members - current):
            add_member(db, team=team, company=company, user=make_user(db, role="guide"))
        # commit, not flush: the endpoints under test call db.rollback() when they refuse a
        # request, and that unwinds to the test's savepoint. Committing here releases the
        # savepoint so the setup survives; the fixture's outer transaction still rolls the whole
        # test back afterwards.
        db.commit()
        return company

    return company, team, fill_to


def invite(client, company_id, owner_token, email):
    return client.post(
        f"/api/companies/{company_id}/invitations",
        json={"invited_email": email, "expires_in_days": 7},
        headers={"Authorization": f"Bearer {owner_token}"},
    )


def make_invitation_row(db, company, creator, email, *, days_valid=7):
    invite_row = InvitationCode(
        code=f"CAP-{email.split('@')[0].upper()}",
        company_id=company.id,
        created_by=creator.id,
        invited_email=email,
        status="pending",
        used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days_valid),
    )
    db.add(invite_row)
    db.commit()   # see fill_to -- must survive the endpoint's rollback
    return invite_row


def accept(client, code, user):
    return client.post("/api/companies/invitations/accept", json={"code": code}, headers=auth(user))


# --- acceptance is where the cap must actually hold -------------------------------------------
def test_accepting_an_invitation_cannot_push_a_company_past_its_cap(
    client, db, company_at, guide_user
):
    """The bypass: issue invitations while under the cap, then accept them all."""
    company, team, fill_to = company_at
    fill_to(FREE_TIER_MAX)  # owner + 4 = 5, the company is now full

    invitee = make_user(db, role="guide", email="hopeful@example.cl")
    row = make_invitation_row(db, company, guide_user, invitee.email)

    response = accept(client, row.code, invitee)
    assert response.status_code == 402, response.text

    members = (
        db.query(CompanyMember)
        .filter(CompanyMember.companyid == company.id, CompanyMember.is_active.is_(True))
        .count()
    )
    assert members == FREE_TIER_MAX, "the cap must hold at acceptance, not just at invitation"


def test_several_outstanding_invitations_cannot_all_be_accepted_past_the_cap(
    client, db, company_at, guide_user
):
    """The original bypass, end to end: under the cap, invite many, then everyone accepts."""
    company, team, fill_to = company_at
    fill_to(4)  # one seat left

    invitees = [make_user(db, role="guide", email=f"queue{i}@example.cl") for i in range(4)]
    rows = [make_invitation_row(db, company, guide_user, u.email) for u in invitees]

    results = [accept(client, row.code, user).status_code for row, user in zip(rows, invitees)]

    assert results.count(200) == 1, f"exactly one seat was available, got {results}"
    assert all(code == 402 for code in results if code != 200), results

    members = (
        db.query(CompanyMember)
        .filter(CompanyMember.companyid == company.id, CompanyMember.is_active.is_(True))
        .count()
    )
    assert members == FREE_TIER_MAX


def test_a_rejected_acceptance_leaves_the_invitation_usable(client, db, company_at, guide_user):
    """A 402 must not burn the invitation -- the company may upgrade, and the invitee retry."""
    company, team, fill_to = company_at
    fill_to(FREE_TIER_MAX)

    invitee = make_user(db, role="guide", email="patient@example.cl")
    row = make_invitation_row(db, company, guide_user, invitee.email)

    assert accept(client, row.code, invitee).status_code == 402
    db.refresh(row)
    assert row.status == "pending", "the invitation should still be usable"
    assert row.used is False

    company.license_tier = "pro"
    db.commit()
    assert accept(client, row.code, invitee).status_code == 200


# --- invitations reserve a seat ---------------------------------------------------------------
def test_outstanding_invitations_count_against_the_cap(client, db, company_at, auth_guide_token):
    """Two seats left means two invitations, not fifty."""
    company, team, fill_to = company_at
    fill_to(3)  # 3 members, cap 5 -> 2 seats

    assert invite(client, str(company.id), auth_guide_token, "a@example.cl").status_code == 200
    assert invite(client, str(company.id), auth_guide_token, "b@example.cl").status_code == 200

    third = invite(client, str(company.id), auth_guide_token, "c@example.cl")
    assert third.status_code == 402, third.text
    assert "invitation" in third.json()["detail"].lower() or "limit" in third.json()["detail"].lower()


def test_an_expired_invitation_releases_its_seat(client, db, company_at, guide_user, auth_guide_token):
    company, team, fill_to = company_at
    fill_to(4)  # one seat

    stale = make_invitation_row(db, company, guide_user, "ghost@example.cl")
    stale.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.flush()

    fresh = invite(client, str(company.id), auth_guide_token, "live@example.cl")
    assert fresh.status_code == 200, "an expired invitation must not hold a seat forever"


def test_licence_info_reports_reserved_seats(db, company_at, guide_user):
    company, team, fill_to = company_at
    fill_to(3)
    make_invitation_row(db, company, guide_user, "pending@example.cl")

    info = LicenseManager.get_company_license_info(db, company.id)
    assert info["current_guides"] == 3
    assert info["pending_invitations"] == 1
    assert info["seats_taken"] == 4
    assert info["can_add_guides"] is True      # a member could still be added directly
    assert info["can_invite_guides"] is True   # and one more invitation fits

    make_invitation_row(db, company, guide_user, "pending2@example.cl")
    info = LicenseManager.get_company_license_info(db, company.id)
    assert info["seats_taken"] == 5
    assert info["can_invite_guides"] is False


def test_enterprise_tier_is_unlimited(client, db, guide_user, auth_guide_token):
    company, team = make_company(db, owner=guide_user, name="Big Co", tier="enterprise")
    for i in range(8):
        assert invite(client, str(company.id), auth_guide_token, f"e{i}@example.cl").status_code == 200


# --- the licence endpoint ---------------------------------------------------------------------
def test_license_endpoint_reports_seats(client, db, company_at, guide_user):
    company, team, fill_to = company_at
    fill_to(3)
    make_invitation_row(db, company, guide_user, "reserved@example.cl")

    r = client.get(f"/api/companies/{company.id}/license", headers=auth(guide_user))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_guides"] == FREE_TIER_MAX
    assert body["current_guides"] == 3
    assert body["pending_invitations"] == 1
    assert body["seats_taken"] == 4


def test_license_endpoint_works_for_the_unlimited_tier(client, db, guide_user):
    """max_guides was declared as a plain int, so this endpoint failed response validation for
    every enterprise company -- the schema could not express "no limit"."""
    company, team = make_company(db, owner=guide_user, name="Unlimited Co", tier="enterprise")
    db.commit()

    r = client.get(f"/api/companies/{company.id}/license", headers=auth(guide_user))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["max_guides"] is None
    assert body["can_add_guides"] is True
    assert body["can_invite_guides"] is True
