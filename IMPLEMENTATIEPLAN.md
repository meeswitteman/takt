# Implementatieplan — Takt

**Datum**: 2026-05-23  
**Versie**: 0.1  

---

## Projectstructuur

```
D:\projects\python\takt\
├── takt-backend\          # FastAPI backend
│   ├── app\
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models\        # SQLAlchemy ORM modellen
│   │   ├── schemas\       # Pydantic request/response schemas
│   │   ├── routers\       # FastAPI routers per domein
│   │   └── services\      # Businesslogica
│   ├── alembic\           # Database migraties
│   ├── tests\
│   └── requirements.txt
├── takt-desktop\          # PyQt6 desktop app
│   ├── app\
│   │   ├── main.py
│   │   ├── client\        # httpx API-client
│   │   ├── views\         # PyQt6 vensters en widgets
│   │   └── components\    # Herbruikbare UI-componenten
│   └── requirements.txt
├── takt-cli\              # Typer CLI tool
│   ├── takt\
│   │   ├── main.py
│   │   └── client.py
│   └── requirements.txt
├── takt-migrate\          # Eenmalig migratie-script
│   ├── migrate.py
│   └── requirements.txt
└── SRD.md                 # (kopie vanuit medoto project)
```

---

## Fasering

### Fase 1 — Backend fundament
*Doel: werkende API met database, geen UI*

1. **Project opzetten**
   - Python 3.12 virtualenv per module
   - FastAPI + SQLAlchemy 2.x + Alembic installeren
   - SQLite database configureren via env var (`TAKT_DB_PATH`)

2. **Datamodel implementeren**
   - SQLAlchemy modellen: `Item`, `Context`, `ItemContext`, `VariationList`, `VariationEntry`, `TodoLog`
   - Alembic initiële migratie aanmaken en uitvoeren

3. **Item API**
   - `GET /api/v1/items` — boom ophalen
   - `GET /api/v1/items/{id}/children`
   - `POST /api/v1/items` — aanmaken
   - `PATCH /api/v1/items/{id}` — bijwerken (titel, beschrijving, src, start_note)
   - `PATCH /api/v1/items/{id}/move` — verplaatsen (inclusief volgorde)
   - `DELETE /api/v1/items/{id}` — verwijderen met cascade

4. **Context API**
   - `GET/POST/DELETE /api/v1/contexts`
   - Context-overerving implementeren in service-laag

5. **Todo API**
   - `PATCH /api/v1/items/{id}/todo` — als todo markeren
   - `GET /api/v1/todos?context=bass` — actieve todo's met context-filter
   - `POST /api/v1/todos/{id}/done` — afvinken

6. **Recurring logica**
   - Interval-berekening: direct, daily, weekly, weekday:N, monthly_first
   - Na afvinken: `last_done_at` bijwerken, item opnieuw actief maken

7. **Variatie API**
   - `GET/POST /api/v1/variations`
   - `PUT /api/v1/variations/{id}/entries`
   - Bij afvinken variatie-todo: volgende waarde selecteren (linear/random)

8. **Health endpoint**
   - `GET /api/v1/health`

**Klaar als**: alle endpoints werken en te testen zijn via Swagger UI (`/docs`)

---

### Fase 2 — Migratie
*Doel: bestaande Medo v1 data importeren*

1. **Migratie-script schrijven**
   - Parser voor `projects.txt` (tab-indentatie → boom)
   - Parser voor `<context>-TODO.txt` → todo-markering op items
   - Parser voor `DONE.txt` → `TodoLog` entries
   - Parser voor `variation-*.txt` → `VariationList` + `VariationEntry`
   - `medo-settings.properties` → contexten aanmaken

2. **Migratie uitvoeren en valideren**
   - Draaien tegen `C:\Users\meesw\.medo\`
   - Resultaat controleren via Swagger UI

**Klaar als**: alle bestaande data zichtbaar is via de API

---

### Fase 3 — CLI
*Doel: bruikbare command-line tool voor snel gebruik op Mac/Windows*

```bash
takt todos [--context bass]          # actieve todo's tonen
takt done <id> [--note "tekst"]      # afvinken
takt add <parent-id> <titel>         # item aanmaken
takt todo <id>                       # als todo markeren
```

1. Typer app opzetten met httpx client
2. Backend URL via env var (`TAKT_API_URL`, default `http://localhost:8080`)
3. Leesbare terminal output (rich library voor kleur/tabel)

**Klaar als**: `takt todos --context bass` werkt op de command line

---

### Fase 4 — Desktop app
*Doel: PyQt6 app met projectboom als centraal scherm*

**Sprint 4a — Projectboom**
- Hoofdvenster met twee tabbladen: Projecten / Todo's
- Projecten-tab: tree widget met lazy-load children
- Inline rename (F2), nieuw kind-item (Ctrl+N), verwijderen (Delete)
- Drag-and-drop verplaatsen
- Context-chips naast itemtitels (gekleurde labels)
- Klikbaar `src`-veld (opent browser of bestandsmanager)

**Sprint 4b — Todo's tab**
- Lijst van actieve todo's, filterbaar op context
- Recurring-icoon voor herhalende taken
- Variatie-waarde prominent weergegeven
- Afvinken-dialoog met optionele notitie
- Donker/licht thema

**Sprint 4c — Beheer**
- Context beheren (aanmaken, kleur, verwijderen)
- Variatielijsten beheren
- Instellingen (backend URL, thema, standaard context)

**Klaar als**: dagelijks gebruik is mogelijk via de desktop app

---

## Technische keuzes

| Keuze | Reden |
|-------|-------|
| FastAPI | Automatische Swagger docs, async support, snel te starten |
| SQLAlchemy 2.x | Type-safe ORM, goede Alembic integratie |
| Alembic | Schema-migraties zonder data verlies bij updates |
| PyQt6 | Rijkste widget-set voor Python desktop, native look |
| Typer | Elegante CLI met type-hints, goede help-output |
| httpx | Moderne async HTTP client, gedeeld tussen CLI en desktop |
| rich | Mooie terminal output voor de CLI |

---

## Volgorde van implementatie

```
Fase 1 (backend)  →  Fase 2 (migratie)  →  Fase 3 (CLI)  →  Fase 4 (desktop)
     ~1 week              ~1 dag               ~1 dag            ~2 weken
```

Backend eerst — zodat alle andere clients er direct tegenaan kunnen testen.  
Migratie vroeg — zodat je meteen met echte data werkt.  
CLI voor dagelijks gebruik terwijl de desktop app gebouwd wordt.

---

## Configuratie (env vars)

| Variabele | Default | Beschrijving |
|-----------|---------|-------------|
| `TAKT_DB_PATH` | `%APPDATA%/takt/takt.db` | SQLite bestandspad |
| `TAKT_PORT` | `8080` | Backend poort |
| `TAKT_API_URL` | `http://localhost:8080` | Voor CLI en desktop |
| `TAKT_CORS_ORIGINS` | `*` | CORS (voor VPS: domein instellen) |
