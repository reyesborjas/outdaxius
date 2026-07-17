# backend/app/services/company_usage.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

def month_window_utc(now: Optional[datetime] = None):
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # next month (no dateutil dependency)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end

SQL_HISTORICAL_ACTIVITIES = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
)
SELECT COUNT(a.id) AS total_activities_historical
FROM activities a
JOIN company_users cu ON a.created_by = cu.userid;
""")

SQL_HISTORICAL_PROGRAMS = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
)
SELECT COUNT(p.id) AS total_programs_historical
FROM programs p
JOIN company_users cu ON p.created_by = cu.userid;
""")

SQL_HISTORICAL_PROGRAM_SCHEDULES = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
),
company_programs AS (
  SELECT p.id
  FROM programs p
  JOIN company_users cu ON p.created_by = cu.userid
)
SELECT COUNT(ps.id) AS total_program_schedules_historical
FROM program_schedules ps
JOIN company_programs cp ON ps.program_id = cp.id;
""")

SQL_HISTORICAL_ACTIVITY_SCHEDULES = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
),
company_activities AS (
  SELECT a.id
  FROM activities a
  JOIN company_users cu ON a.created_by = cu.userid
)
SELECT COUNT(asch.id) AS total_activity_schedules_historical
FROM activity_schedules asch
JOIN company_activities ca ON asch.activity_id = ca.id;
""")

SQL_HISTORICAL_BOOKINGS = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
),
company_program_schedules AS (
  SELECT ps.id
  FROM programs p
  JOIN company_users cu ON p.created_by = cu.userid
  JOIN program_schedules ps ON ps.program_id = p.id
),
company_activity_schedules AS (
  SELECT asch.id
  FROM activities a
  JOIN company_users cu ON a.created_by = cu.userid
  JOIN activity_schedules asch ON asch.activity_id = a.id
)
SELECT COUNT(b.id) AS total_bookings_historical
FROM bookings b
LEFT JOIN company_program_schedules cps ON b.program_schedule_id = cps.id
LEFT JOIN company_activity_schedules cas ON b.activity_schedule_id = cas.id
WHERE cps.id IS NOT NULL OR cas.id IS NOT NULL;
""")

SQL_HISTORICAL_PARTICIPANTS = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
),
company_program_schedules AS (
  SELECT ps.id
  FROM programs p
  JOIN company_users cu ON p.created_by = cu.userid
  JOIN program_schedules ps ON ps.program_id = p.id
),
company_activity_schedules AS (
  SELECT asch.id
  FROM activities a
  JOIN company_users cu ON a.created_by = cu.userid
  JOIN activity_schedules asch ON asch.activity_id = a.id
)
SELECT COALESCE(SUM(b.participants_count), 0) AS total_participants_historical
FROM bookings b
LEFT JOIN company_program_schedules cps ON b.program_schedule_id = cps.id
LEFT JOIN company_activity_schedules cas ON b.activity_schedule_id = cas.id
WHERE cps.id IS NOT NULL OR cas.id IS NOT NULL;
""")

SQL_MONTHLY_BOOKINGS_PARTICIPANTS = text("""
WITH company_users AS (
  SELECT DISTINCT cm.userid
  FROM company_members cm
  WHERE cm.companyid = :company_id
),
company_program_schedules AS (
  SELECT ps.id
  FROM programs p
  JOIN company_users cu ON p.created_by = cu.userid
  JOIN program_schedules ps ON ps.program_id = p.id
),
company_activity_schedules AS (
  SELECT asch.id
  FROM activities a
  JOIN company_users cu ON a.created_by = cu.userid
  JOIN activity_schedules asch ON asch.activity_id = a.id
),
company_bookings AS (
  SELECT b.*
  FROM bookings b
  LEFT JOIN company_program_schedules cps ON b.program_schedule_id = cps.id
  LEFT JOIN company_activity_schedules cas ON b.activity_schedule_id = cas.id
  WHERE cps.id IS NOT NULL OR cas.id IS NOT NULL
)
SELECT
  COUNT(id) AS bookings,
  COALESCE(SUM(participants_count), 0) AS participants
FROM company_bookings
WHERE created_at >= :from_date
  AND created_at <  :to_date;
""")

def historical_usage(db: Session, company_id: UUID) -> Dict[str, int]:
    params = {"company_id": company_id}
    activities = int(db.execute(SQL_HISTORICAL_ACTIVITIES, params).scalar() or 0)
    programs = int(db.execute(SQL_HISTORICAL_PROGRAMS, params).scalar() or 0)
    prog_schedules = int(db.execute(SQL_HISTORICAL_PROGRAM_SCHEDULES, params).scalar() or 0)
    act_schedules = int(db.execute(SQL_HISTORICAL_ACTIVITY_SCHEDULES, params).scalar() or 0)
    bookings = int(db.execute(SQL_HISTORICAL_BOOKINGS, params).scalar() or 0)
    participants = int(db.execute(SQL_HISTORICAL_PARTICIPANTS, params).scalar() or 0)

    return {
        "activities": activities,
        "programs": programs,
        "program_schedules": prog_schedules,
        "activity_schedules": act_schedules,
        "schedules_total": prog_schedules + act_schedules,
        "bookings": bookings,
        "participants": participants,
    }

def monthly_usage(db: Session, company_id: UUID, from_date: datetime, to_date: datetime) -> Dict[str, int]:
    row = db.execute(
        SQL_MONTHLY_BOOKINGS_PARTICIPANTS,
        {"company_id": company_id, "from_date": from_date, "to_date": to_date},
    ).first()
    if not row:
        return {"bookings": 0, "participants": 0}
    return {"bookings": int(row.bookings or 0), "participants": int(row.participants or 0)}

# Ownership helpers (used for booking enforcement):
SQL_COMPANIES_FOR_PROGRAM_SCHEDULE = text("""
SELECT DISTINCT cm.companyid
FROM program_schedules ps
JOIN programs p ON p.id = ps.program_id
JOIN company_members cm ON cm.userid = p.created_by
WHERE ps.id = :program_schedule_id;
""")

SQL_COMPANIES_FOR_ACTIVITY_SCHEDULE = text("""
SELECT DISTINCT cm.companyid
FROM activity_schedules a_s
JOIN activities a ON a.id = a_s.activity_id
JOIN company_members cm ON cm.userid = a.created_by
WHERE a_s.id = :activity_schedule_id;
""")

def companies_for_program_schedule(db: Session, program_schedule_id: UUID) -> List[UUID]:
    rows = db.execute(SQL_COMPANIES_FOR_PROGRAM_SCHEDULE, {"program_schedule_id": program_schedule_id}).all()
    return [r[0] for r in rows]

def companies_for_activity_schedule(db: Session, activity_schedule_id: UUID) -> List[UUID]:
    rows = db.execute(SQL_COMPANIES_FOR_ACTIVITY_SCHEDULE, {"activity_schedule_id": activity_schedule_id}).all()
    return [r[0] for r in rows]
