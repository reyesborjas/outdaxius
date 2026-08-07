# backend/tests/test_catalogue_scoping.py
"""
Who may see which activities and programs.

These are request-level tests against a real database, because the thing under test is *which
rows come back* -- a static or schema-level check cannot tell you that. They exist because the
catalogue endpoints previously returned every row on the platform, private content included, to
any caller including an anonymous one.

The fixture world is two unrelated tenants:

    Andes      -- has a public trek (upcoming departure, charges enabled)
                  and a private draft (no departures at all)
    Patagonia  -- a competitor; its guide must not see Andes's private draft

See app.services.catalogue for the rules being asserted.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.models.booking import Booking
from app.models.program_schedule import ProgramSchedule
from app.models.programactivity import ProgramActivity
from app.models.programs import Program
from app.services.cancellation import build_policy_snapshot
from tests.conftest import add_member, auth, make_company, make_user


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture()
def world(db, activity_type, location):
    """Two tenants, four activities, one program. Returns a dict of everything tests need."""
    andes_owner = make_user(db, role="guide", email="owner@andes.test.cl")
    andes_guide = make_user(db, role="guide", email="guide@andes.test.cl")
    rival_owner = make_user(db, role="guide", email="owner@patagonia.test.cl")
    traveller = make_user(db, role="client", email="traveller@example.cl")

    andes, andes_team = make_company(db, owner=andes_owner, name="Andes Expeditions")
    add_member(db, team=andes_team, company=andes, user=andes_guide, role_level=4)
    patagonia, patagonia_team = make_company(db, owner=rival_owner, name="Patagonia Kayak")

    def new_activity(title, team, *, shared=False, creator=None):
        a = Activity(
            title=title,
            description=f"{title} description",
            activity_type=activity_type.id,
            created_by=(creator or andes_owner).id,
            location_id=location.id,
            team_id=team.id,
            is_shared=shared,
            gallery=[],
        )
        db.add(a)
        db.flush()
        return a

    def new_schedule(activity, company, *, days_ahead=14, status="confirmed"):
        start = _now() + timedelta(days=days_ahead)
        s = ActivitySchedule(
            activity_id=activity.id,
            start_time=start,
            end_time=start + timedelta(hours=6),
            price=50000,
            status=status,
            min_participants=1,
            max_participants=10,
            selling_company_id=company.id,
        )
        db.add(s)
        db.flush()
        return s

    public_trek = new_activity("Public Trek", andes_team)
    public_sched = new_schedule(public_trek, andes)

    private_draft = new_activity("Private Draft", andes_team)          # no departures at all
    past_only = new_activity("Past Only", andes_team)
    new_schedule(past_only, andes, days_ahead=-10)                      # departure already gone

    shared_activity = new_activity("Shared Climb", andes_team, shared=True)

    rival_activity = new_activity(
        "Patagonia Kayak Trip", patagonia_team, creator=rival_owner
    )
    new_schedule(rival_activity, patagonia)

    program = Program(
        title="Public Program",
        description="d",
        program_type=activity_type.id,
        created_by=andes_owner.id,
        team_id=andes_team.id,
        is_shared=False,
        gallery=[],
        min_activities=2,
    )
    db.add(program)
    db.flush()
    db.add(ProgramActivity(program_id=program.id, activity_id=public_trek.id))
    p_start = _now() + timedelta(days=20)
    db.add(
        ProgramSchedule(
            program_id=program.id,
            start_time=p_start,
            end_time=p_start + timedelta(days=3),
            price=200000,
            status="confirmed",
            min_participants=1,
            max_participants=10,
            selling_company_id=andes.id,
        )
    )

    private_program = Program(
        title="Private Program",
        description="d",
        program_type=activity_type.id,
        created_by=andes_owner.id,
        team_id=andes_team.id,
        is_shared=False,
        gallery=[],
        min_activities=2,
    )
    db.add(private_program)
    db.flush()

    return {
        "andes_owner": andes_owner,
        "andes_guide": andes_guide,
        "rival_owner": rival_owner,
        "traveller": traveller,
        "andes": andes,
        "patagonia": patagonia,
        "public_trek": public_trek,
        "public_sched": public_sched,
        "private_draft": private_draft,
        "past_only": past_only,
        "shared_activity": shared_activity,
        "rival_activity": rival_activity,
        "program": program,
        "private_program": private_program,
    }


def titles(response):
    assert response.status_code == 200, response.text
    return {row["title"] for row in response.json()}


# --- the public catalogue -------------------------------------------------------------------
def test_anonymous_sees_only_offerings_with_a_bookable_departure(client, world):
    seen = titles(client.get("/api/activities/"))
    assert "Public Trek" in seen
    assert "Patagonia Kayak Trip" in seen          # a real offering from another company
    assert "Private Draft" not in seen             # never scheduled
    assert "Past Only" not in seen                 # departure already happened
    assert "Shared Climb" not in seen              # shared, but nothing to book


def test_anonymous_cannot_open_a_private_activity_by_id(client, world):
    r = client.get(f"/api/activities/{world['private_draft'].id}")
    assert r.status_code == 404, "a private draft must not be readable by URL"


def test_anonymous_can_open_a_public_activity_by_id(client, world):
    r = client.get(f"/api/activities/{world['public_trek'].id}")
    assert r.status_code == 200
    assert r.json()["title"] == "Public Trek"


def test_search_does_not_bypass_the_public_filter(client, world):
    # "r" appears in both "Public Trek" and "Private Draft", so the query itself matches both and
    # the only thing separating them in the result is the visibility filter.
    seen = titles(client.get("/api/activities/search", params={"q": "r"}))
    assert "Public Trek" in seen
    assert "Private Draft" not in seen


def test_programs_follow_the_same_rule(client, world):
    seen = titles(client.get("/api/programs/"))
    assert "Public Program" in seen
    assert "Private Program" not in seen


def test_program_activities_are_gated_on_the_program(client, world):
    ok = client.get(f"/api/programs/{world['program'].id}/activities")
    assert ok.status_code == 200
    hidden = client.get(f"/api/programs/{world['private_program'].id}/activities")
    assert hidden.status_code == 404


def test_a_cancelled_departure_does_not_make_an_activity_public(client, db, world):
    world["public_sched"].status = "canceled"
    db.flush()
    assert "Public Trek" not in titles(client.get("/api/activities/"))


def test_an_activity_is_hidden_when_its_company_cannot_take_money(client, db, world):
    from app.models.company_payment_account import CompanyPaymentAccount

    account = (
        db.query(CompanyPaymentAccount)
        .filter(CompanyPaymentAccount.company_id == world["andes"].id)
        .first()
    )
    account.charges_enabled = False
    db.flush()
    seen = titles(client.get("/api/activities/"))
    assert "Public Trek" not in seen
    assert "Patagonia Kayak Trip" in seen, "only the affected company should disappear"


# --- the competitor, which is what prompted this --------------------------------------------
def test_a_rival_guide_cannot_see_another_companys_private_catalogue(client, world):
    seen = titles(
        client.get("/api/activities/", params={"mine_only": True}, headers=auth(world["rival_owner"]))
    )
    assert "Private Draft" not in seen
    assert "Public Trek" not in seen, "Andes's own non-shared activity is not theirs to schedule"
    assert "Shared Climb" in seen, "explicitly shared activities remain reusable"
    assert "Patagonia Kayak Trip" in seen, "their own catalogue is still there"


def test_the_internal_list_matches_what_the_write_path_allows(client, db, world):
    """The bug behind this work: the list offered things the API would then refuse with 403.

    Whatever mine_only returns must be schedulable, and whatever it hides must not be.
    """
    rival = world["rival_owner"]
    listed = titles(client.get("/api/activities/", params={"mine_only": True}, headers=auth(rival)))
    assert "Private Draft" not in listed

    start = _now() + timedelta(days=45)
    payload = {
        "activity_id": str(world["private_draft"].id),
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=5)).isoformat(),
        "price": 1000,
        "min_participants": 1,
        "max_participants": 5,
    }
    refused = client.post("/api/activity-schedules/", json=payload, headers=auth(rival))
    assert refused.status_code == 403, refused.text


# --- own company ----------------------------------------------------------------------------
def test_own_guide_sees_the_whole_company_catalogue_including_drafts(client, world):
    seen = titles(
        client.get("/api/activities/", params={"mine_only": True}, headers=auth(world["andes_guide"]))
    )
    for title in ("Public Trek", "Private Draft", "Past Only", "Shared Climb"):
        assert title in seen, f"{title} missing from the owning company's own view"
    assert "Patagonia Kayak Trip" not in seen


def test_mine_only_requires_authentication(client, world):
    assert client.get("/api/activities/", params={"mine_only": True}).status_code == 401
    assert client.get("/api/programs/", params={"mine_only": True}).status_code == 401


# --- travellers keep their own history ------------------------------------------------------
def test_a_traveller_still_sees_an_activity_they_booked_after_it_stops_selling(client, db, world):
    """Otherwise "My bookings" would lose the titles of past trips."""
    traveller = world["traveller"]
    past = world["past_only"]
    sched = (
        db.query(ActivitySchedule).filter(ActivitySchedule.activity_id == past.id).first()
    )
    db.add(
        Booking(
            user_id=traveller.id,
            activity_schedule_id=sched.id,
            status="confirmed",
            participants_count=1,
            participants=[],
            attendance_status="attended",
            policy_snapshot=build_policy_snapshot(),
        )
    )
    db.flush()

    seen = titles(client.get("/api/activities/", headers=auth(traveller)))
    assert "Past Only" in seen, "a booked trip must stay resolvable for its own traveller"
    assert "Private Draft" not in seen, "but that must not open up the rest of the catalogue"


# --- admin ----------------------------------------------------------------------------------
def test_platform_admin_sees_everything(client, db, world):
    admin = make_user(db, role="admin", email="admin@outdaxius.test.cl")
    seen = titles(client.get("/api/activities/", headers=auth(admin)))
    for title in ("Public Trek", "Private Draft", "Past Only", "Patagonia Kayak Trip"):
        assert title in seen
