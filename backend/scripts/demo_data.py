# backend/scripts/demo_data.py
"""
The literal content of the Outdaxius demo: tenants, people, places, activities and programs.

Kept separate from scripts/seed_demo.py so the *narrative* (which is what a salesperson tunes
before a call) is editable without touching the *mechanics* (transactions, ordering, idempotency).

Everything here is deliberately hand-written rather than Faker-generated. Faker produces
"Lorem Ipsum Kayaking" and a prospect notices immediately; a demo only survives scrutiny if the
activity names, prices and coordinates are ones a real Chilean operator would recognise. Faker is
used in seed_demo.py only for the long tail -- customer names and participant details -- where
volume matters more than plausibility.
"""
from __future__ import annotations

# Password shared by every seeded account. Deliberately obvious: it goes on the login screen.
DEMO_PASSWORD = "demo1234"

# --------------------------------------------------------------------------------------------
# Tenants
# --------------------------------------------------------------------------------------------
# Three companies, because multi-tenancy is a selling point and one company cannot demonstrate it.
# Each tier exists to show a different thing on a call:
#   pro        -> the hero tenant, fully populated, where the main tour happens
#   basic      -> deliberately parked near its plan limits, so the upgrade path can fire live
#   enterprise -> unlimited tier, and a second data shape so the platform doesn't look
#                 single-purpose
COMPANIES = [
    {
        "key": "andes",
        "name": "Andes Expeditions",
        "legal_name": "Andes Expeditions SpA",
        "trade_name": "Andes Expeditions",
        "description": (
            "High-altitude trekking, mountaineering and glacier travel across the central Andes. "
            "Operating out of Santiago since 2014."
        ),
        "tier": "pro",
        "country": "CL",
        "currency": "CLP",
        "address": "Av. Apoquindo 4501, Las Condes, Santiago",
        "entity_type": "spa",
        "incorporation_date": "2014-03-11",
        "legal_representive": "Matías Fuenzalida",
        "legal_representive_text": "13.442.918-K",
        "legal_representive_phone": "+56 2 2345 8890",
        "team_name": "Andes Guides",
    },
    {
        "key": "patagonia",
        "name": "Patagonia Kayak Co.",
        "legal_name": "Patagonia Kayak Company Ltda.",
        "trade_name": "Patagonia Kayak",
        "description": (
            "Sea kayaking and packrafting in the fjords and lakes of the Aysén region. "
            "Small groups, four guides, one very good coffee setup."
        ),
        "tier": "basic",
        "country": "CL",
        "currency": "CLP",
        "address": "Costanera 210, Puerto Río Tranquilo, Aysén",
        "entity_type": "ltda",
        "incorporation_date": "2019-09-02",
        "legal_representive": "Carolina Ithurbide",
        "legal_representive_text": "16.908.221-4",
        "legal_representive_phone": "+56 9 7788 1200",
        "team_name": "Patagonia Paddlers",
    },
    {
        "key": "cordillera",
        "name": "Cordillera Ski School",
        "legal_name": "Escuela de Esquí Cordillera SpA",
        "trade_name": "Cordillera Ski School",
        "description": (
            "Ski and splitboard instruction, avalanche courses and backcountry touring across the "
            "Tres Valles resorts. Certified to AAA and AIARE standards."
        ),
        "tier": "enterprise",
        "country": "CL",
        "currency": "CLP",
        "address": "Camino a Farellones km 38, Lo Barnechea, Santiago",
        "entity_type": "spa",
        "incorporation_date": "2011-06-20",
        "legal_representive": "Ignacio Prieto",
        "legal_representive_text": "11.220.775-2",
        "legal_representive_phone": "+56 2 2201 4477",
        "team_name": "Cordillera Instructors",
    },
]

# --------------------------------------------------------------------------------------------
# Named accounts -- the four logins that go on the demo login screen
# --------------------------------------------------------------------------------------------
# The four-account structure IS the demo: each is a different act in the story. Everyone else
# seeded below is supporting cast.
DEMO_LOGINS = [
    {
        "key": "owner",
        "email": "owner@andes.demo",
        "first_name": "Matías",
        "last_name": "Fuenzalida",
        "display_name": "Matías Fuenzalida",
        "role": "guide",
        "company": "andes",
        "role_level": 1,       # master -- full company control
        "position": "Founder & Operations Director",
        "is_admin": True,
        "blurb": "Company owner: revenue, staffing, refunds, settings",
    },
    {
        "key": "guide",
        "email": "guide@andes.demo",
        "first_name": "Javiera",
        "last_name": "Rojas",
        "display_name": "Javiera Rojas",
        "role": "guide",
        "company": "andes",
        "role_level": 4,       # field guide -- sees their own assignments only
        "position": "Lead Mountain Guide",
        "is_admin": False,
        "blurb": "Field guide: my assignments, my schedule",
    },
    {
        "key": "client",
        "email": "client@outdaxius.demo",
        "first_name": "Tomás",
        "last_name": "Vergara",
        "display_name": "Tomás Vergara",
        "role": "client",
        "company": None,
        "role_level": None,
        "position": None,
        "is_admin": False,
        "blurb": "Customer: search, book, pay, cancel",
    },
    {
        # The Phase 5 plan-limit demo needs a login that can actually administer the basic-tier
        # tenant. GET /companies only returns companies the caller is a member of, so
        # owner@andes.demo cannot see Patagonia at all -- correct multi-tenant scoping, but it
        # leaves the upgrade-path moment unrunnable without this account.
        "key": "patagonia_owner",
        "email": "owner@patagonia.demo",
        "first_name": "Carolina",
        "last_name": "Ithurbide",
        "display_name": "Carolina Ithurbide",
        "role": "guide",
        "company": "patagonia",
        "role_level": 1,
        "position": "Owner & Head Guide",
        "is_admin": True,
        "blurb": "Freemium owner: usage meters, plan limits, upgrade path",
    },
    {
        "key": "admin",
        "email": "admin@outdaxius.demo",
        "first_name": "Paula",
        "last_name": "Sandoval",
        "display_name": "Paula Sandoval",
        "role": "admin",
        "company": None,
        "role_level": None,
        "position": None,
        "is_admin": False,
        "blurb": "Platform admin: cross-tenant view",
    },
]

# --------------------------------------------------------------------------------------------
# Supporting guides, per tenant
# --------------------------------------------------------------------------------------------
# Andes gets 12 more (14 total with owner + Javiera) so guide utilization charts and the
# assignment conflict detector have a real roster to work against. role_level follows the
# cascading hierarchy in app.models.team: 1 master, 2 planner, 3 coordinator, 4 field guide.
GUIDES = {
    "andes": [
        ("Cristóbal", "Ovalle", 2, "Head of Programs"),
        ("Antonia", "Lagos", 2, "Logistics Manager"),
        ("Sebastián", "Muñoz", 3, "Senior Guide — Alta Montaña"),
        ("Fernanda", "Cortés", 3, "Senior Guide — Glaciar"),
        ("Rodrigo", "Peña", 4, "Mountain Guide"),
        ("Camila", "Bustos", 4, "Mountain Guide"),
        ("Diego", "Alarcón", 4, "Mountain Guide"),
        ("Valentina", "Soto", 4, "Mountain Guide"),
        ("Nicolás", "Herrera", 4, "Trekking Guide"),
        ("Josefa", "Miranda", 4, "Trekking Guide"),
        ("Andrés", "Cáceres", 4, "Trekking Guide"),
        ("Catalina", "Reyes", 4, "Apprentice Guide"),
    ],
    "patagonia": [
        # Carolina Ithurbide is intentionally absent here -- she is a named login in DEMO_LOGINS
        # above, and listing her in both would seed her twice.
        ("Gaspar", "Villalobos", 3, "Sea Kayak Guide"),
        ("Emilia", "Kusanovic", 4, "Sea Kayak Guide"),
        ("Martín", "Oyarzún", 4, "Packraft Guide"),
    ],
    "cordillera": [
        ("Ignacio", "Prieto", 1, "Director"),
        ("Trinidad", "Valdés", 2, "Head of Instruction"),
        ("Felipe", "Undurraga", 3, "Senior Instructor"),
        ("Isidora", "Echeverría", 3, "Avalanche Course Lead"),
        ("Benjamín", "Ruiz-Tagle", 4, "Ski Instructor"),
        ("Magdalena", "Correa", 4, "Ski Instructor"),
        ("Vicente", "Larraín", 4, "Splitboard Instructor"),
    ],
}

# --------------------------------------------------------------------------------------------
# Locations -- real coordinates
# --------------------------------------------------------------------------------------------
# Real Chilean coordinates matter more than they sound: the Leaflet map on the activities page
# renders these directly. Fake or clustered-at-(0,0) points produce a map that visibly lies, which
# is the single fastest way to lose a room.
LOCATIONS = [
    ("Cerro El Plomo, Región Metropolitana", -33.2317, -70.2136),
    ("Cajón del Maipo, San José de Maipo", -33.7350, -70.3500),
    ("Glaciar El Morado, Monumento Natural", -33.7833, -70.0500),
    ("Volcán Villarrica, Pucón", -39.4200, -71.9390),
    ("Termas de Chillán, Ñuble", -36.9050, -71.4060),
    ("Torres del Paine, Magallanes", -50.9423, -73.4068),
    ("Laguna San Rafael, Aysén", -46.6833, -73.8500),
    ("Lago General Carrera, Río Tranquilo", -46.6270, -72.6740),
    ("Fiordo Queulat, Aysén", -44.4980, -72.5620),
    ("Río Futaleufú, Los Lagos", -43.1830, -71.8660),
    ("Valle Nevado, Lo Barnechea", -33.3560, -70.2510),
    ("La Parva, Lo Barnechea", -33.3290, -70.2870),
    ("El Colorado, Farellones", -33.3480, -70.2900),
    ("Nevados de Chillán, Ñuble", -36.8640, -71.3770),
]

# --------------------------------------------------------------------------------------------
# Activity / program types
# --------------------------------------------------------------------------------------------
# experience_type follows app/api/types.py: 'activity', 'program', or 'both'.
TYPES = [
    ("Trekking", "both"),
    ("Mountaineering", "both"),
    ("Glacier Travel", "activity"),
    ("Rock Climbing", "activity"),
    ("Sea Kayaking", "both"),
    ("Packrafting", "activity"),
    ("Whitewater Rafting", "activity"),
    ("Ski Touring", "both"),
    ("Avalanche Safety", "activity"),
    ("Splitboarding", "activity"),
    ("Expedition", "program"),
    ("Multi-day Course", "program"),
]

# --------------------------------------------------------------------------------------------
# Activities
# --------------------------------------------------------------------------------------------
# (title, type_name, location_index, price_clp, min_participants, max_participants, description)
# Prices are realistic CLP. A demo whose numbers are off by 10x reads as unfinished to anyone who
# actually works in the industry.
ACTIVITIES = {
    "andes": [
        ("Ascenso Cerro El Plomo (5.424 m)", "Mountaineering", 0, 285000, 2, 8,
         "Three-day acclimatised ascent of the classic Santiago summit. Includes high camp at "
         "Federación, technical gear and full guide ratio of 1:4."),
        ("Trekking Glaciar El Morado", "Trekking", 2, 68000, 2, 14,
         "Full-day approach to the El Morado glacier lagoon. Moderate, 17 km round trip, no "
         "technical experience required."),
        ("Curso de Glaciar — Nivel I", "Glacier Travel", 2, 145000, 3, 10,
         "Two-day introduction to rope teams, crevasse rescue and self-arrest on real ice."),
        ("Escalada en Roca — Cajón del Maipo", "Rock Climbing", 1, 52000, 2, 8,
         "Single-pitch sport climbing day at Las Chilcas. All hardware provided, grades 5.7 to 5.11."),
        ("Travesía Cajón del Maipo", "Trekking", 1, 95000, 4, 12,
         "Two-day traverse with one night in refuge. The most-booked trip in our catalogue."),
        ("Ascenso Volcán Villarrica", "Mountaineering", 3, 175000, 2, 10,
         "Guided summit day on an active volcano, with crampons, ice axe and gas mask supplied."),
        ("Trekking Torres del Paine — Base Torres", "Trekking", 5, 120000, 4, 16,
         "The iconic day hike to the base of the towers. Early start, 22 km, 1.100 m of gain."),
        ("Expedición Fotográfica Alta Montaña", "Trekking", 0, 88000, 2, 8,
         "Sunrise photography ascent to 3.200 m with a working mountain photographer."),
    ],
    "patagonia": [
        ("Kayak Capillas de Mármol", "Sea Kayaking", 7, 78000, 2, 8,
         "Three hours paddling the marble caves of Lago General Carrera. The trip everyone comes for."),
        ("Kayak Fiordo Queulat", "Sea Kayaking", 8, 92000, 2, 6,
         "Full day in the fjord beneath the hanging glacier. Cold water rescue certified guides."),
        ("Packraft Río Futaleufú — Tramo Bajo", "Packrafting", 9, 110000, 3, 6,
         "Introductory packrafting on the lower Futaleufú. Class II-III with safety kayaker."),
        ("Travesía Laguna San Rafael", "Sea Kayaking", 6, 240000, 4, 8,
         "Two-day expedition paddle to the San Rafael glacier face. Camping on the beach."),
    ],
    "cordillera": [
        ("Clase Particular de Esquí", "Ski Touring", 10, 95000, 1, 4,
         "Private instruction at Valle Nevado, all levels, 3 hours on snow."),
        ("Curso AIARE Nivel 1", "Avalanche Safety", 11, 320000, 4, 12,
         "Three-day internationally certified avalanche course. Classroom plus two field days."),
        ("Ski Touring La Parva — Día Completo", "Ski Touring", 11, 135000, 2, 8,
         "Backcountry touring day above the resort boundary. Skins, beacon and airbag provided."),
        ("Splitboard Backcountry — El Colorado", "Splitboarding", 12, 140000, 2, 6,
         "Splitboard-specific touring day with transitions coaching."),
        ("Travesía Nevados de Chillán", "Ski Touring", 13, 260000, 3, 8,
         "Two-day hut-to-hut ski traverse with thermal springs at the finish."),
        ("Rescate en Grietas — Taller", "Avalanche Safety", 10, 78000, 3, 10,
         "Half-day crevasse and companion rescue refresher for returning students."),
    ],
}

# --------------------------------------------------------------------------------------------
# Programs (multi-activity packages)
# --------------------------------------------------------------------------------------------
# (title, type_name, [activity indices into ACTIVITIES[company]], price_clp, min_p, max_p, description)
PROGRAMS = {
    "andes": [
        ("Programa Aconcagua — Preparación 6 semanas", "Expedition", [0, 2, 4], 890000, 4, 10,
         "Six-week structured preparation for a 6.000 m expedition: technique, glacier skills and "
         "two progressive altitude ascents."),
        ("Semana Andina — Todo Incluido", "Expedition", [1, 4, 7], 420000, 4, 12,
         "Seven days combining our three best-loved day trips, with lodging in Cajón del Maipo."),
        ("Curso Montañismo Integral", "Multi-day Course", [2, 3, 0], 640000, 3, 8,
         "Our flagship course. Rock, ice and altitude across four weekends, with certification."),
        ("Patagonia Clásica", "Expedition", [6, 1], 780000, 4, 16,
         "Eight days in Torres del Paine and the southern icefield fringe."),
        ("Fin de Semana en la Montaña", "Multi-day Course", [4, 3], 165000, 2, 12,
         "Entry-level weekend for people who have never slept above 2.000 m."),
    ],
    "patagonia": [
        ("Expedición Aysén — 5 Días", "Expedition", [0, 1, 3], 620000, 4, 8,
         "Five days paddling the marble caves, Queulat fjord and the San Rafael glacier."),
        ("Fin de Semana Kayak + Packraft", "Multi-day Course", [0, 2], 195000, 3, 6,
         "Two days sampling both disciplines, for paddlers deciding which to pursue."),
    ],
    "cordillera": [
        ("Temporada Completa — Ski Touring", "Expedition", [2, 3, 4], 720000, 4, 10,
         "A full winter progression from resort-boundary touring to a two-day traverse."),
        ("Seguridad en Montaña Invernal", "Multi-day Course", [1, 5], 380000, 4, 12,
         "AIARE 1 plus the crevasse rescue workshop, run as one continuous block."),
        ("Iniciación al Esquí — 4 Clases", "Multi-day Course", [0], 340000, 1, 4,
         "Four private lessons for a complete beginner, booked as one package."),
    ],
}

# --------------------------------------------------------------------------------------------
# Booking status mix
# --------------------------------------------------------------------------------------------
# Weights chosen to look like a real business rather than a test fixture. A 50/50 split of
# confirmed/cancelled is the tell that data was generated rather than earned.
#
# Past schedules resolve to completed/attended or a cancellation; upcoming ones are live demand.
PAST_STATUS_WEIGHTS = [
    ("confirmed", 74),   # ran, attended
    ("cancelled", 11),   # client cancelled -- some with a fee, per policy tier
    ("confirmed", 9),    # ran, but marked no_show
    ("cancelled", 6),    # vendor cancelled -- full refund, drives the reputation badge
]

UPCOMING_STATUS_WEIGHTS = [
    ("confirmed", 68),
    ("pending", 24),     # booked, not yet paid -- gives the owner an inbox to work
    ("cancelled", 8),
]
