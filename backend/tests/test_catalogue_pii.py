# backend/tests/test_catalogue_pii.py
"""
Guard that catalogue responses never carry personal data.

GET /activities/, GET /activities/search, GET /activities/{id}, and GET /programs/ take no
authentication dependency at all -- anything in their response models is world-readable. They
used to embed the full UserOut as `creator` and `leader`, which meant an unauthenticated caller
could enumerate every company's catalogue and read its guides' email, national_id,
passport_number, phone, birth_date, tax_id and entire fiscal_data blob (legal representative,
tax address, and the rest).

These tests walk the resolved Pydantic models rather than grepping source, so they also catch the
field arriving through a newly nested model somewhere further down the tree.

Scope: this asserts what the response SHAPE can contain. It says nothing about which rows are
returned -- the catalogue is still unscoped, and a guide from one company can still see another
company's private (is_shared=false) activities. That is tracked separately in
docs/DEMO_SETUP.md; the agreed target is that an unauthenticated visitor should only see
offerings that have a published, bookable schedule.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.schemas.activity import ActivityOut
from app.schemas.program import ProgramOut
from app.schemas.user import UserPublicOut

# Anything that identifies a person off-platform, or exposes their tax/legal records.
PII_FIELDS = {
    "email",
    "national_id",
    "passport_number",
    "phone",
    "birth_date",
    "tax_id",
    "fiscal_data",
    "profile",
}


def walk_fields(model: type[BaseModel], _seen: set | None = None) -> set[str]:
    """Every field name reachable from `model`, following nested Pydantic models."""
    _seen = _seen if _seen is not None else set()
    if model in _seen:
        return set()
    _seen.add(model)

    names: set[str] = set()
    for field_name, field in model.model_fields.items():
        names.add(field_name)
        annotation = field.annotation
        candidates = [annotation]
        # Unwrap Optional[...] / Union[...] / list[...] and friends.
        candidates.extend(getattr(annotation, "__args__", ()) or ())
        for candidate in candidates:
            if isinstance(candidate, type) and issubclass(candidate, BaseModel):
                names |= walk_fields(candidate, _seen)
    return names


@pytest.mark.parametrize("model", [ActivityOut, ProgramOut], ids=["ActivityOut", "ProgramOut"])
def test_catalogue_response_carries_no_pii(model: type[BaseModel]) -> None:
    leaked = walk_fields(model) & PII_FIELDS
    assert not leaked, (
        f"{model.__name__} exposes {sorted(leaked)}. This model is returned by an endpoint that "
        f"requires no authentication, so these fields would be readable by anyone. Embed "
        f"UserPublicOut rather than UserOut."
    )


def test_user_public_out_is_actually_minimal() -> None:
    """UserPublicOut is the safe embed. If someone widens it, every catalogue endpoint widens."""
    leaked = set(UserPublicOut.model_fields) & PII_FIELDS
    assert not leaked, f"UserPublicOut gained {sorted(leaked)}; it must stay free of personal data."


def test_catalogue_still_credits_the_author() -> None:
    """The strip must not go so far that a listing can no longer say who runs the trip -- that is
    the reason creator/leader are embedded at all."""
    for model in (ActivityOut, ProgramOut):
        names = walk_fields(model)
        assert "display_name" in names, f"{model.__name__} can no longer show the author's name"
