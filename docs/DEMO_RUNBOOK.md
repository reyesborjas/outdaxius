# Outdaxius — Demo Build Runbook

**Goal:** not a production-ready SaaS. A *complex, live, believable demo* that a prospective
customer can be walked through in 15 minutes and can then click around unaccompanied for a week.

**Audience for the artifact:** trekking / rafting / ski / expedition operators, and any acquirer
evaluating the asset.

**Estimated effort:** 60–80 hours across 7 phases. Phases 1–3 are the critical path; a demo
without them does not exist. Phases 4–7 are what make it *sell*.

---

## Phase 0 — Baseline: what is already built (do not rebuild it)

Before starting, know that the executive report understates the codebase. Verified as present:

| Capability | Status | Where |
| --- | --- | --- |
| Auth (JWT + refresh, single-flight refresh) | Built | `backend/app/api/auth.py`, `frontend/src/lib/api.js` |
| Companies, members, roles, invitations | Built | `app/api/company.py`, `companymember.py`, `membership_requests.py` |
| Activities, programs, schedules | Built | `app/api/activities.py`, `programs.py`, `*_schedules.py` |
| Bookings + cancellation fees + refunds | Built | `app/api/booking.py`, `app/services/cancellation.py` |
| Guide assignments + conflict detection | Built | `app/api/assignments.py`, `app/services/assignments.py` |
| Vendor reputation / cancellation-rate badge | Built | `app/services/vendor_reputation.py`, `CancellationRateBadge.jsx` |
| Plan tiers + hard limit enforcement | Built | `app/services/plan_limits.py`, `licensing.py`, `enforce_limits.py` |
| **Demo payment provider (no real money, no signup)** | **Built** | `app/services/payments/demo.py`, `DemoCheckout.jsx` |
| Maps / locations | Built | `LocationsMap.jsx`, `MapView.jsx` |
| Migrations | 7 revisions | `backend/alembic/versions/` |

**This is the single most important fact for planning:** `DemoProvider` already simulates the
full pay → confirm → refund cycle through the *same* code paths a real provider uses. The demo
can therefore show real money movement semantics without a Flow or Stripe account. You are not
building a demo mode — you are populating and exposing one that exists.

Verified gaps that block a demo:

- **No seed data whatsoever.** `faker` sits in `requirements-dev.txt` unused. An empty app
  demos as a broken app.
- **`Reports.jsx` is a 6-line placeholder** — literally `<p>This is where admins can view and
  manage reports.</p>`. This is the exact feature the $299 Professional tier is sold on.
- **Nothing is deployed.** `vercel.json` and `render.yaml` both exist and describe *different*
  topologies. One must win.
- **No `.github/`, no CI.**
- **One test file** (`backend/tests/test_companies.py`, 139 lines).
- **No `frontend/.env.example`**, so `VITE_API` is tribal knowledge.
- `app/api/payment_stripe.py` is intentionally unmounted dead code — leave it, but do not let a
  technical evaluator find it without explanation.

---

## Phase 1 — Demo data foundation — ✅ DONE

Delivered. See [DEMO_SETUP.md](./DEMO_SETUP.md) for the full setup path, demo logins, and the
issues this phase uncovered.

| Script | Purpose |
| --- | --- |
| `backend/scripts/bootstrap_schema.py` | Brings an empty database to Alembic head. Needed because `alembic upgrade head` alone does not work on a fresh database and `schema.sql` is not directly runnable. |
| `backend/scripts/demo_data.py` | The narrative — tenants, people, places, catalogue. Separated so a salesperson can tune content without touching mechanics. |
| `backend/scripts/seed_demo.py` | The seeder. Deterministic, idempotent, scoped, guarded. |
| `backend/scripts/verify_demo.py` | 27 checks asserting the demo is showable. Exits non-zero if not. |

Verified against a running server: all five logins authenticate, the customer/activities/programs/
bookings endpoints return populated data, and the full book → pay → confirm → cancel → refund
cycle completes through the demo provider.

**Findings** — details in DEMO_SETUP.md:

1. ~~**Plan limits are only half-enforced.**~~ **Fixed.** `activities.py` imported
   `enforce_company_creation_limits` without calling it; `activity_schedules.py` never imported
   it. A `basic` tenant walked from 48 to 52 schedules against a cap of 50 with no error. Three
   call sites are now wired and verified against a running server — activities block at 20/20,
   standalone and child schedules at 50/50, unlimited tiers unaffected.
   `tests/test_plan_limit_wiring.py` guards the regression. **Phase 5 is unblocked.**
2. **The test suite does not run** — no `tests/conftest.py`, all 8 tests in `test_companies.py`
   error at setup. Phase 6. (The new wiring test needs no fixtures and does run.)

<details>
<summary>Original Phase 1 plan (≈16 h)</summary>

An empty database is the number one reason technical demos fail. Everything else is decoration.

### 1.1 Build the seeder

Create `backend/scripts/seed_demo.py`, idempotent, driven by a fixed random seed so every run
produces byte-identical data.

```
python -m scripts.seed_demo --reset
```

Requirements:

- Fixed `Faker` seed + fixed `random.seed()` → the demo looks the same every time you present it.
- Idempotent: re-running replaces the demo tenant, never duplicates it.
- Guard against catastrophe: refuse to run unless `APP_ENV=demo`, and scope every delete to the
  demo companies' IDs. Never a bare `TRUNCATE`.
- Dates generated **relative to `now()`**, not hardcoded. Stale "2025" dates in a 2026 demo are
  the fastest possible credibility loss.

### 1.2 What to seed

Three tenants, because multi-tenancy is a core selling point and one company cannot show it:

| Tenant | Tier | Purpose in the demo |
| --- | --- | --- |
| **Andes Expeditions** | `pro` | The hero. Fully populated, healthy, the main tour. |
| **Patagonia Kayak Co.** | `basic` | The freemium tenant, deliberately near its limits (Phase 5). |
| **Cordillera Ski School** | `enterprise` | Shows unlimited tier + a second data shape. |

For **Andes Expeditions** specifically, seed enough to survive scrutiny:

- 12–15 **guides** with real-looking names, certifications, availability.
- 8–10 **activities** across trekking / climbing / rafting, with real Chilean coordinates so
  the Leaflet map renders a convincing cluster rather than one lonely pin.
- 5–6 **multi-day programs**, each composed of several activities.
- **~90 days of schedules**: ~40 in the past (so reports have history), ~30 upcoming
  (so dashboards have something to do today).
- **150–200 bookings** across a realistic status mix: confirmed, pending, completed,
  cancelled-with-fee, refunded. Skew it to look like a real business — roughly 70% confirmed,
  8–12% cancelled. A 50/50 split looks synthetic.
- **Payments** on the demo provider in every terminal state, including a partial refund and a
  cancellation that actually charged a fee.
- **Assignments** with at least one deliberate near-conflict, so the conflict detector has
  something to catch on stage.
- 3–4 pending **membership requests** and 2 open **invitations**, so the admin inbox is not empty.

### 1.3 Demo accounts

Seed four logins with one shared, obvious password (`demo1234`) and put them **on the login
screen** (Phase 3.2):

| Email | Role | What the prospect sees |
| --- | --- | --- |
| `owner@andes.demo` | Company owner | Full admin: revenue, staffing, refunds, settings |
| `guide@andes.demo` | Guide | The staff view: my assignments, my schedule |
| `client@outdaxius.demo` | Customer | Search → book → pay → cancel, end to end |
| `admin@outdaxius.demo` | Super admin | Platform-level view across all three tenants |

The four-account structure *is* the demo. Each one is a different act in the story.

### 1.4 Wire the demo payment rail

For each seeded company, insert a `company_payment_account` row with `provider="demo"` and
charges enabled. `get_any_charges_enabled_account()` in `app/services/payment_accounts.py`
already resolves it, and `POST /bookings/{id}/pay` will route to `DemoProvider` with no further
code changes. Verify the redirect lands on `/demo-checkout/{ref}` and that
`POST /payments/demo/{ref}/complete` transitions the booking.

**Acceptance:** drop the DB, run `alembic upgrade head && python -m scripts.seed_demo --reset`,
log in as all four users, and every single page has content. No empty state, no spinner that
never resolves, no `[]`.

</details>

**What changed against the plan.** Three things the plan did not anticipate:

- The bootstrap step (`bootstrap_schema.py`) had to be written first — `alembic upgrade head`
  does not work on an empty database, so the acceptance criterion above was not runnable as
  stated.
- A **fifth** demo login was needed. `GET /companies` only returns companies the caller belongs
  to, so `owner@andes.demo` cannot see the freemium tenant at all. Phase 5's plan-limit demo
  needs `owner@patagonia.demo`.
- The freemium tenant is parked near the **schedules** cap rather than the activities cap.
  Schedules carry no hand-written content, so reaching 48 of 50 needs no invented activity names
  — whereas padding to 19 of 20 activities would have meant fabricating filler that a prospect
  would notice immediately.

---

## Phase 2 — Get it live (≈10 h)

A demo on `localhost` over a screenshare is a prototype. A demo at a URL the prospect can open
on their phone the next morning is a product.

### 2.1 Pick one deployment target and delete the other config

`vercel.json` and `render.yaml` currently contradict each other. **Recommendation: Render.**
Reasons — `render.yaml` already declares the env vars correctly, the FastAPI app is a long-lived
ASGI process rather than a serverless handler, and `alembic upgrade head` needs somewhere to run.
Vercel serverless adds a cold-start tax and a filesystem model this app does not want.

Concretely:
- Backend + Postgres on Render (free tier is adequate for a demo).
- Frontend static build on Render or Cloudflare Pages.
- Keep `vercel.json` only if you commit to maintaining it. Otherwise delete it — a stale deploy
  config is a finding in a technical review.

### 2.2 Deploy checklist

1. Provision Postgres (Neon or Render Postgres). Copy the connection string.
2. Set backend env: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM=HS256`,
   `ACCESS_TOKEN_EXPIRE_MINUTES`, `CREDENTIALS_ENCRYPTION_KEY`, `APP_ENV=demo`,
   and `CORS_ORIGINS` set to the **exact** frontend origin (no trailing slash — `main.py`
   splits on comma and does not strip).
3. Run `alembic upgrade head`, then the seeder.
4. Build the frontend with `VITE_API=https://<backend-host>/api`.
5. Confirm `GET /health` returns `{"status":"ok"}` and `healthCheckPath` passes.
6. Add `frontend/.env.example` documenting `VITE_API`. Its absence is a real onboarding gap.

### 2.3 Cold-start mitigation

Render free tier sleeps after inactivity, and a 40-second wake-up during a sales call is fatal.
Either upgrade the backend to the paid instance for demo season, or add an external uptime ping
every 10 minutes. Decide this *before* the first booked call, not during it.

### 2.4 Nightly reset

Add a scheduled job (Render cron, or a GitHub Actions schedule) running the seeder at 04:00.
This means prospects can click anything — cancel bookings, delete activities, break things — and
the demo is pristine the next morning. Say so out loud on the call: it converts "don't touch
that" into "go ahead, break it." That single sentence is worth more than most features.

**Acceptance:** a URL you can text to someone, that works on a phone, from a cold browser, with
no explanation attached.

---

## Phase 3 — The demo narrative surfaces (≈14 h)

This is the phase that converts "a working app" into "a demo that sells." Three things.

### 3.1 Landing page

`frontend/src/pages/Home.jsx` is 106 lines and is currently the first thing a prospect sees.
Rebuild it as a real landing page:

- One-line positioning: what Outdaxius does, for whom, in plain language.
- 4–6 capability cards drawn from what actually exists — bookings, guide assignment with
  conflict detection, cancellation policy + automated refunds, multi-tenant companies, maps,
  plan limits. **Do not advertise anything not seeded and clickable.** A demo that promises
  more than it shows is worse than a smaller honest one.
- A prominent **"Try the live demo"** button → `/login` with credentials pre-filled.
- Screenshots or a 60-second loop of the real dashboard.

### 3.2 One-click role entry

On `Login.jsx`, add four buttons — **Enter as Owner / Guide / Customer / Platform Admin** — that
fill and submit the seeded credentials. Zero typing. Every second a prospect spends typing a
password is a second they are not looking at the product.

Gate these buttons on `APP_ENV=demo` (expose it via a small `/api/config` endpoint or a build-time
`VITE_DEMO_MODE` flag) so they cannot ship to a real tenant later.

### 3.3 Guided tour overlay

Add a lightweight tour (`driver.js` or ~150 lines of hand-rolled overlay — do not pull in a heavy
dependency) that runs on first login per role, 5–7 steps each, dismissible, restartable from a "?"
in the header. This is what makes the demo survive *unaccompanied* use after the call ends, which
is when the actual buying decision gets made internally.

Also add a persistent **"DEMO — data resets nightly"** banner. It sets expectations, removes fear
of breaking things, and quietly explains any weirdness.

**Acceptance:** hand the URL to someone who has never seen Outdaxius, say nothing, and watch. If
they reach a booked-and-paid reservation without asking you a question, this phase is done.

---

## Phase 4 — Build the thing you are actually selling (≈12 h)

`Reports.jsx` is a placeholder. The Professional tier at $299/month is sold on "analytics
dashboard." **Right now the demo cannot show the feature the price is attached to.** This is the
highest-leverage work in the entire plan.

Build a real reports page against the seeded 90 days of history:

- **Revenue over time** — line chart, monthly, with a period-over-period delta.
- **Bookings funnel** — created → confirmed → completed, plus cancellation rate (the
  `vendor_reputation` service already computes this; surface it).
- **Top activities and programs** by revenue and by fill rate.
- **Guide utilization** — assigned days per guide, from the assignments data.
- **Capacity / fill rate** per schedule — the metric operators actually care about.
- **Refunds and cancellation fees collected** — closes the loop on the Phase 6 fee work.

Add the backing aggregate endpoints under `app/api/` (a new `reports.py` router). Keep the
aggregation in SQL, not in Python loops over ORM objects — a technical evaluator will look, and
this is where they will look.

Use a single small charting library. Ship 4–6 charts that are correct and legible rather than a
dozen that are noisy.

**Acceptance:** the owner login opens to a dashboard where every number is derived from seeded
data and cross-checks against the underlying tables.

---

## Phase 5 — Make the pricing model visible (≈6 h)

The tiers exist in code (`plan_limits.py`: basic / pro / enterprise) but a prospect cannot see
them, and — worth noting — the code's tier names do not match the report's commercial names
(Freemium / Professional / Enterprise). Reconcile the labels so the pricing conversation and the
product use the same words.

Then make the limits *visible*, because a limit a customer cannot see cannot motivate an upgrade:

- Usage meters in company settings: "84 / 100 bookings this month", "18 / 20 activities".
  `app/services/company_usage.py` already computes these.
- A friendly upgrade prompt when `enforce_limits` blocks an action, instead of a raw error.
- A `/pricing` page listing the three tiers.

Seed **Patagonia Kayak Co.** deliberately close to its `basic` limits so you can log in during
the call, try to add one more activity, and let the prospect watch the upgrade path fire live.
That moment sells the freemium model far better than a slide does.

**Ready to demo now.** Phase 1 seeds Patagonia at 48 of 50 schedules and the enforcement gap is
fixed, so the sequence works today: log in as `owner@patagonia.demo`, add two departures, and the
third returns `402 Plan limit reached for schedules_total: 50/50`. What remains in this phase is
presentation — turning that raw 402 into a friendly upgrade prompt, and surfacing the usage meters
that `GET /companies/{id}/limits` already returns.

---

## Phase 6 — Technical credibility (≈10 h)

For the acquirer audience specifically. The report scores Documentation 5.0/10 and flags no CI,
no observability — all three are real and all three are cheap to fix.

1. **CI.** Add `.github/workflows/ci.yml`: install, `pytest`, `npm run build`, and a lint pass.
   Green badge in the README. This directly answers "no visible CI/CD pipeline."
2. **Tests.** From 1 file to meaningful coverage on the three flows that hold the money:
   booking creation, cancellation-fee calculation, and plan-limit enforcement. Target the
   business logic, not controllers. 20–30 focused tests beat a coverage percentage.
3. **README.** Replace the 20-line stub with: architecture diagram, local setup, env var table,
   migration commands, seeding, deployment. `backend/COMPANY_SYSTEM.md` already shows you can
   write good internal docs — extend that standard outward.
4. **Explain the dead code.** `app/api/payment_stripe.py` is unmounted intentionally and the
   `routes/__init__.py` comment says why. Move that rationale into an `ARCHITECTURE_DECISIONS.md`
   so an evaluator reads it as a deliberate decision rather than finding abandoned code.
5. **Structured logging + error tracking.** Sentry free tier on both ends, request IDs in
   FastAPI. Two hours of work that removes an entire audit finding.
6. **Housekeeping.** `backend_callgraph.png` (3.2 MB), `.svg`, `.dot`, `frontend/1.txt` and the
   `collect_*.py` scratch scripts are committed at the repo root. Move them to `docs/` or remove
   them. First impressions of a repo are formed in the root directory listing.

---

## Phase 7 — Sales assets (≈8 h)

The demo is the product. These are what carry it into rooms you are not in.

1. **The 12-minute script** (below). Rehearse until it needs no notes.
2. **A 3-minute recorded walkthrough.** Most prospects will not book a live call. Loom or OBS,
   real data, no slides.
3. **A one-page PDF**: what it does, who it is for, three pricing tiers, the demo URL.
4. **A follow-up email template** containing the demo URL and the four logins, sent within an
   hour of every call.

### The 12-minute demo script

| Min | Act | What you show |
| --- | --- | --- |
| 0–1 | Frame | "This runs a whole outdoor operator — bookings, guides, money — in one place." |
| 1–3 | **Customer** | Log in as customer. Browse activities on the map, open a program, book it. |
| 3–5 | **Payment** | Pay through demo checkout. Booking flips to confirmed. Say plainly: *simulated rail, same code path as the real one.* |
| 5–7 | **Owner** | Switch to owner. The booking is already there. Assign a guide — trigger the conflict detector on purpose. |
| 7–9 | **Money** | Cancel a booking. Show the fee calculated by policy, the refund issued, the cancellation-rate badge moving. |
| 9–11 | **Reports** | Open the analytics dashboard. Revenue, fill rate, guide utilization. *This is the $299 slide.* |
| 11–12 | **Close** | Hit the plan limit as the freemium tenant. Show the upgrade path. Hand over the URL and logins. |

Two rules: **never** show an empty screen, and **never** apologize for the demo provider — state
once that it is simulated and move on. Confidence about a deliberate choice reads as competence;
hedging about it reads as an unfinished product.

---

## Sequencing and honest scope

```
Phase 1 (seed) ──► Phase 2 (deploy) ──► Phase 3 (narrative) ──► DEMO IS SHOWABLE
                                             │
                                             ├──► Phase 4 (reports)   ← highest sales leverage
                                             ├──► Phase 5 (pricing)
                                             ├──► Phase 6 (credibility) ← for acquirers
                                             └──► Phase 7 (assets)
```

If you only have two weeks: **Phases 1, 2, 3, 4.** That is a demo that closes pilot customers.
Phases 5–7 raise the price you can ask; they do not make the demo exist.

### Deliberately out of scope

Stated explicitly so nobody drifts into them:

- Real payment integration (Flow/Stripe live keys) — the demo provider is strictly better here.
- Docker / Kubernetes / infrastructure-as-code — a demo has one environment.
- Email delivery, SSO, mobile apps, i18n.
- Performance work, load testing, horizontal scaling.
- Backups and disaster recovery — the nightly reset *is* the recovery story.

Every one of these belongs in the post-pilot roadmap. None of them wins a first customer, and
each one is a plausible-sounding way to spend three weeks not having a demo.

### The risk worth naming

The report's own conclusion applies to this plan too: the constraint is not engineering. This
runbook produces a demo. A demo does not produce customers — outreach does. Book two discovery
calls with real operators *before* Phase 1 is finished. What they ask for in those calls should
change what you build in Phases 4 and 5. Building all seven phases in isolation and then starting
outreach is the single most likely way for this effort to be wasted.
