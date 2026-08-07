# backend/tests/test_plan_limit_wiring.py
"""
Guard that every resource-creating route actually CALLS the plan-limit enforcer.

This exists because of a specific, silent failure: app/api/activities.py imported
enforce_company_creation_limits and took the get_current_company_id dependency, but never called
the function. app/api/activity_schedules.py did not reference it at all. The result was a limit
that GET /companies/{id}/limits reported and nothing enforced -- a basic-tier company walked from
48 to 52 schedules against a cap of 50 without an error.

Nothing about that failure is visible in review: the import is present, the dependency is wired,
and the module reads as if it enforces. So these tests parse the route modules and assert the
call is really there.

Scope, stated honestly: this checks WIRING, not behaviour. It cannot tell whether the right
company id or the right metric is passed, only that the enforcer is invoked on the path at all.
Behavioural coverage needs a database fixture, which this suite does not yet have -- see
tests/conftest.py (absent) and docs/DEMO_SETUP.md.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

API_DIR = pathlib.Path(__file__).resolve().parents[1] / "app" / "api"

ENFORCER = "enforce_company_creation_limits"

# (module, metric) pairs that must be enforced somewhere in the module.
EXPECTED = [
    ("activities.py", "activities"),
    ("programs.py", "programs"),
    ("activity_schedules.py", "schedules_total"),
    ("program_schedules.py", "schedules_total"),
]


def _calls_in(module_path: pathlib.Path, func_name: str) -> list[ast.Call]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        name = (
            target.id
            if isinstance(target, ast.Name)
            else target.attr
            if isinstance(target, ast.Attribute)
            else None
        )
        if name == func_name:
            found.append(node)
    return found


def _metrics_passed(calls: list[ast.Call]) -> set[str]:
    metrics: set[str] = set()
    for call in calls:
        for kw in call.keywords:
            if kw.arg == "metric" and isinstance(kw.value, ast.Constant):
                metrics.add(kw.value.value)
        # Also accept it positionally, in case a caller drops the keyword.
        for arg in call.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                metrics.add(arg.value)
    return metrics


@pytest.mark.parametrize("module_name,metric", EXPECTED)
def test_creation_route_enforces_plan_limit(module_name: str, metric: str) -> None:
    module_path = API_DIR / module_name
    assert module_path.exists(), f"{module_name} not found"

    calls = _calls_in(module_path, ENFORCER)
    assert calls, (
        f"{module_name} never calls {ENFORCER}. Creating this resource would bypass the "
        f"{metric!r} plan limit entirely, while GET /companies/{{id}}/limits keeps reporting it."
    )

    metrics = _metrics_passed(calls)
    assert metric in metrics, (
        f"{module_name} calls {ENFORCER} but not with metric={metric!r} "
        f"(found {sorted(metrics) or 'no string arguments'})."
    )


def test_no_route_imports_the_enforcer_without_calling_it() -> None:
    """The original bug in one assertion: an import with no matching call.

    An unused import of the enforcer is never intentional -- it means someone wired the limit up
    halfway and the module now reads as protected while behaving as unprotected.
    """
    offenders = []
    for module_path in sorted(API_DIR.glob("*.py")):
        source = module_path.read_text(encoding="utf-8")
        if ENFORCER not in source:
            continue

        tree = ast.parse(source)
        imported = any(
            isinstance(node, ast.ImportFrom)
            and any(alias.name == ENFORCER for alias in node.names)
            for node in ast.walk(tree)
        )
        if imported and not _calls_in(module_path, ENFORCER):
            offenders.append(module_path.name)

    assert not offenders, (
        f"These modules import {ENFORCER} but never call it: {offenders}. "
        "Either call it on the creation path or drop the import."
    )
