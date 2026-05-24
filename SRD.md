# Software Requirements Document — Takt

**Versie**: 0.2  
**Datum**: 2026-05-23  
**Status**: Concept  

---

## 1. Visie

Takt is een persoonlijke productiviteitsapplicatie waarbij de hiërarchische projectboom centraal staat. Taken (todo's) en terugkerende taken zijn afgeleide weergaven van die projectboom — geen aparte entiteiten. De applicatie is beschikbaar via een Python desktop-app en een command-line tool, ondersteund door een lokale FastAPI-backend die eenvoudig naar een VPS te verplaatsen is.

---

## 2. Probleemstelling

De huidige versie (Medo v1, file-based Java app) heeft de volgende tekortkomingen:

- De projectboom en todo-lijsten zijn opgeslagen in losse tekstbestanden per context — geen echte database
- De UI (Java Swing) is beperkt qua look-and-feel en moderne interactie
- De Projects-tab en Todo-tab zijn conceptueel losgekoppeld
- Geen multi-client toegang (één desktop app, geen API)
- Het variatie-systeem (cycling exercises) is impliciet in bestandsnamen/attributen, niet als eersteklas concept

---

## 3. Scope

### In scope (v2)
- FastAPI backend met SQLite database
- Python desktop applicatie (PyQt6)
- Python command-line tool
- Projecthiërarchie als centrale datastructuur
- Todo's als afgeleide weergave van projectitems
- Recurring todo items met instelbaar interval
- Variatie-systeem voor cyclische oefeningen (linear/random)
- Migratie van bestaande `.medo` tekstbestanden
- Multi-client architectuur (één backend, meerdere clients)

### Buiten scope (toekomstige versies)
- Authenticatie / multi-user
- Web frontend (mobiel)
- Text-to-speech client
- Synchronisatie met externe diensten

---

## 4. Gebruikers

| Rol | Beschrijving |
|-----|-------------|
| Eindgebruiker | Één persoon, benadert de app via desktop (Windows/Mac) en CLI |

---

## 5. Bestaand Bestandsformaat (v1 — voor migratie)

De huidige data bevindt zich in `C:\Users\meesw\.medo\` als tekstbestanden.

### projects.txt — projectboom
Tab-ingesprongen regels, één item per regel. Diepte = aantal tabs.

```
Muziek
    Barteketet :: bass
        setlijst gbdb zomer editie
    Jazz
        Standards
bass
    play along bass
        sledgehammer | src=https://... | start=2e couplet loopje
        the real thing | src="D:\..." | start=tempo mag omhoog
    relative chords study 7/9
        Db7/9 | src=https://... | var=rel_ch_79 | varm=random | varidx=5 | start=...
```

**Item-attributen** (pipe-separated na titel):
| Attribuut | Beschrijving |
|-----------|-------------|
| `:: <context>` | Koppelt item aan een context/label |
| `src=<url\|pad>` | Bronverwijzing (URL of bestandspad) |
| `start=<tekst>` | Startnoot: waar te beginnen bij dit todo-item |
| `var=<naam>` | Verwijst naar een variatie-bestand |
| `varm=linear\|random` | Variatiekeuze-methode |
| `varidx=<n>` | Huidige index in de variatielijst |

### \<context\>-TODO.txt — actieve todo's per context
Elke regel is één actief todo-item, beschreven als pad + titel:
```
bass arpeggios - 7       1  3   5 b7 | src=... | var=arpeggios | varm=random | varidx=9
Muziek  Barteketet - setlijst gbdb zomer editie | src=https://...
```

### DONE.txt — afgevinkte items
```
2025-10-03 21:54:02 - play along bass - boogie w / it stone
2025-10-05 18:46:09 - play along bass - songs FC | src=https://...
```

### variation-\<naam\>.txt — variatielijsten
Eén waarde per regel. Geïndexeerd op `varidx`:
```
MAJ7    1  3   5  7
min7    1 b3   5 b7
7       1  3   5 b7
```

### medo-settings.properties
Configuratie: contexts, thema, UI-staat, data-locatie.

---

## 6. Functionele Eisen

### 6.1 Projectboom (kern)

| ID | Eis |
|----|-----|
| F-01 | De gebruiker kan items aanmaken in een onbeperkt diepe hiërarchie |
| F-02 | Elk item heeft een titel en een optionele beschrijving |
| F-03 | Items kunnen worden verplaatst naar een andere ouder of positie |
| F-04 | Items kunnen worden hernoemd |
| F-05 | Items kunnen worden verwijderd (inclusief alle afstammelingen) |
| F-06 | De volgorde van items binnen een niveau is handmatig instelbaar |
| F-07 | Items kunnen worden samengeklapt/uitgevouwen in de boomweergave |
| F-08 | Een item kan een bronverwijzing hebben (`src`): URL of bestandspad |
| F-09 | Een item kan een startnoot hebben (`start`): vrije tekst als hint |

### 6.2 Contexten / Labels

| ID | Eis |
|----|-----|
| F-10 | De gebruiker kan contexten aanmaken met naam en kleur |
| F-11 | Een item kan aan nul of meer contexten worden gekoppeld |
| F-12 | Kinditems erven de contexten van hun voorouders (context-overerving) |
| F-13 | Contexten worden visueel zichtbaar naast het item in de boom |

### 6.3 Todo's

| ID | Eis |
|----|-----|
| F-14 | Elk item in de projectboom kan als todo worden aangemerkt |
| F-15 | De todo-weergave toont alle actieve todo's, filterbaar op context |
| F-16 | Een todo kan worden afgevinkt (done), met optionele notitie en timestamp |
| F-17 | Afgevinkte todo's verdwijnen uit de actieve lijst |
| F-18 | De geschiedenis van afgevinkte todo's is raadpleegbaar per item |
| F-19 | Todo's hebben geen deadline; ze zijn zichtbaar tot ze worden afgevinkt |

### 6.4 Recurring Todo's

| ID | Eis |
|----|-----|
| F-20 | Een todo-item kan worden gemarkeerd als recurring |
| F-21 | Bij recurring items stelt de gebruiker een interval in |
| F-22 | Ondersteunde intervallen: direct, dagelijks, wekelijks, specifieke weekdag (ma/di/…), eerste van de maand |
| F-23 | Na afvinken verschijnt een recurring item automatisch opnieuw op het ingestelde interval |
| F-24 | Het systeem houdt bij wanneer een recurring todo voor het laatst is afgevinkt |

### 6.5 Variatie-systeem

| ID | Eis |
|----|-----|
| F-25 | Een item kan worden gekoppeld aan een variatielijst (lijst van waarden) |
| F-26 | De variatiekeuze is instelbaar: lineair (volgende in lijst) of random |
| F-27 | Bij het afvinken van een variatie-todo wordt automatisch de volgende waarde geselecteerd |
| F-28 | De huidige variatie wordt getoond in de todo-weergave als context/hint |
| F-29 | Variatielijsten zijn beheersbaar (aanmaken, bewerken, verwijderen van lijsten en waarden) |

### 6.6 Command-line tool

| ID | Eis |
|----|-----|
| F-30 | De CLI toont actieve todo's, filterbaar op context |
| F-31 | De CLI kan een todo afvinken |
| F-32 | De CLI kan een nieuw item aanmaken als kind van een opgegeven ouder |
| F-33 | De CLI kan items als todo markeren |

### 6.7 Migratie (vanuit Medo v1)

| ID | Eis |
|----|-----|
| F-34 | Een migratie-script importeert `projects.txt` naar de SQLite database |
| F-35 | Het script importeert `<context>-TODO.txt` bestanden en koppelt ze aan bestaande items |
| F-36 | Het script importeert `DONE.txt` als historische log-entries |
| F-37 | Variatielijsten (`variation-*.txt`) worden geïmporteerd als VariationList entiteiten |
| F-38 | `medo-settings.properties` levert de initiële context-definities |

---

## 7. Niet-Functionele Eisen

| ID | Eis |
|----|-----|
| NF-01 | De backend draait lokaal op Windows en is zonder codewijzigingen op een Linux VPS te deployen |
| NF-02 | De desktop-app heeft een moderne, strakke look-and-feel (PyQt6) |
| NF-03 | De API is RESTful en versioned (`/api/v1/...`) |
| NF-04 | De SQLite database is een enkel bestand, eenvoudig te back-uppen |
| NF-05 | De backend start in onder 3 seconden |
| NF-06 | Geen externe cloud-afhankelijkheden (no internet required voor core functie) |
| NF-07 | De backend is voorbereid op authenticatie (configuratie-optie, nu disabled) |

---

## 8. Architectuur

```
┌─────────────────┐    ┌─────────────────┐
│  PyQt6 Desktop  │    │   Python CLI    │
│   (Windows /    │    │  (werk-Mac /    │
│    thuis-pc)    │    │   thuis-pc)     │
└────────┬────────┘    └────────┬────────┘
         │  HTTP REST           │  HTTP REST
         └──────────┬───────────┘
                    ▼
         ┌──────────────────────┐
         │   FastAPI Backend    │
         │   (Python 3.12+)     │
         │                      │
         │  ┌────────────────┐  │
         │  │  SQLite (DB)   │  │
         │  └────────────────┘  │
         └──────────────────────┘
```

### Toekomstige uitbreiding (VPS)
```
         ┌──────────────────────┐
         │   FastAPI op VPS     │
         │   (Docker container) │
         │   + Nginx proxy      │
         └──────────────────────┘
              ▲         ▲
     Web app (mobiel)   TTS client
```

---

## 9. Datamodel

### Item
| Veld | Type | Omschrijving |
|------|------|-------------|
| id | INTEGER PK | Auto-increment |
| parent_id | INTEGER FK | Null = root item |
| title | TEXT | Verplicht |
| description | TEXT | Optioneel |
| order_index | INTEGER | Volgorde binnen ouder |
| is_todo | BOOLEAN | Aangemerkt als todo |
| is_recurring | BOOLEAN | Terugkerend todo-item |
| recurring_interval | TEXT | `direct`, `daily`, `weekly`, `weekday:1` (ma), `monthly_first` |
| last_done_at | DATETIME | Laatste afvinktijdstip (voor recurring) |
| src | TEXT | Bronverwijzing (URL of pad), optioneel |
| start_note | TEXT | Startnoot/hint voor uitvoering, optioneel |
| variation_list_id | INTEGER FK | Koppeling aan variatielijst, optioneel |
| variation_mode | TEXT | `linear` of `random` |
| variation_index | INTEGER | Huidige index in variatielijst |
| created_at | DATETIME | Aanmaakdatum |
| updated_at | DATETIME | Laatste wijziging |

### Context
| Veld | Type | Omschrijving |
|------|------|-------------|
| id | INTEGER PK | |
| name | TEXT UNIQUE | Naam van de context |
| color | TEXT | Hex kleurcode |

### ItemContext (koppeltabel)
| Veld | Type |
|------|------|
| item_id | INTEGER FK |
| context_id | INTEGER FK |

### VariationList
| Veld | Type | Omschrijving |
|------|------|-------------|
| id | INTEGER PK | |
| name | TEXT UNIQUE | Naam (bijv. `arpeggios`) |

### VariationEntry
| Veld | Type | Omschrijving |
|------|------|-------------|
| id | INTEGER PK | |
| list_id | INTEGER FK | |
| position | INTEGER | Volgorde in de lijst |
| value | TEXT | De variatie-waarde (bijv. `MAJ7  1 3 5 7`) |

### TodoLog
| Veld | Type | Omschrijving |
|------|------|-------------|
| id | INTEGER PK | |
| item_id | INTEGER FK | |
| action | TEXT | `DONE` of `UNDONE` |
| note | TEXT | Optionele notitie |
| variation_value | TEXT | Geselecteerde variatie op moment van afvinken |
| completed_at | DATETIME | Tijdstip |

---

## 10. API Overzicht (FastAPI)

### Items
| Methode | Pad | Omschrijving |
|---------|-----|-------------|
| GET | `/api/v1/items` | Boom ophalen (root + children) |
| GET | `/api/v1/items/{id}` | Enkel item |
| GET | `/api/v1/items/{id}/children` | Directe kinderen |
| POST | `/api/v1/items` | Nieuw item aanmaken |
| PATCH | `/api/v1/items/{id}` | Item bijwerken |
| PATCH | `/api/v1/items/{id}/move` | Item verplaatsen |
| PATCH | `/api/v1/items/{id}/todo` | Als todo markeren/demarken |
| PATCH | `/api/v1/items/{id}/recurring` | Recurring instellen |
| DELETE | `/api/v1/items/{id}` | Item + afstammelingen verwijderen |

### Todo's
| Methode | Pad | Omschrijving |
|---------|-----|-------------|
| GET | `/api/v1/todos` | Actieve todo's (filter: `?context=bass`) |
| POST | `/api/v1/todos/{id}/done` | Afvinken (met optionele notitie) |
| GET | `/api/v1/todos/{id}/history` | Geschiedenis van een item |

### Contexten
| Methode | Pad | Omschrijving |
|---------|-----|-------------|
| GET | `/api/v1/contexts` | Alle contexten |
| POST | `/api/v1/contexts` | Nieuwe context |
| DELETE | `/api/v1/contexts/{id}` | Context verwijderen |

### Variatielijsten
| Methode | Pad | Omschrijving |
|---------|-----|-------------|
| GET | `/api/v1/variations` | Alle variatielijsten |
| GET | `/api/v1/variations/{id}` | Lijst met entries |
| POST | `/api/v1/variations` | Nieuwe lijst aanmaken |
| PUT | `/api/v1/variations/{id}/entries` | Entries vervangen |

### Beheer
| Methode | Pad | Omschrijving |
|---------|-----|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/migrate` | Migratie starten vanuit `.medo` directory |

---

## 11. UI/UX Eisen (Desktop)

| ID | Eis |
|----|-----|
| UI-01 | Hoofdvenster heeft twee tabbladen: **Projecten** en **Todo's** |
| UI-02 | Projecten-tab toont de volledige boom; klikken klapt in/uit |
| UI-03 | Items kunnen via drag-and-drop worden verplaatst in de boom |
| UI-04 | Contexten worden als gekleurde chips weergegeven naast itemtitels |
| UI-05 | Dubbel-klikken op een item opent inline-edit voor de titel |
| UI-06 | F2 = hernoemen, Delete = verwijderen, Ctrl+N = nieuw kind-item |
| UI-07 | Todo-tab toont een gefilterde lijst van actieve todo's per context |
| UI-08 | Recurring todo's zijn visueel onderscheidbaar (bijv. herhaal-icoon) |
| UI-09 | Variatie-todo's tonen de huidige variatie-waarde prominent |
| UI-10 | Een todo afvinken toont een dialoog voor een optionele notitie |
| UI-11 | Het UI-thema is donker of licht instelbaar |
| UI-12 | Klikken op `src`-link opent de URL in browser of het bestand in de default app |

---

## 12. Deployment

### Lokaal (Windows)
- Backend: `uvicorn main:app --host 0.0.0.0 --port 8080`
- SQLite bestand: `%APPDATA%\medoto\medoto.db` (configureerbaar via env var)
- Desktop-app: Python script of standalone executable (PyInstaller)

### VPS (toekomst)
- Docker container met FastAPI + Gunicorn
- SQLite als volume of migratie naar PostgreSQL
- Nginx reverse proxy + HTTPS via Let's Encrypt

---

## 13. Technologiestack

| Component | Technologie |
|-----------|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic |
| Database | SQLite |
| Desktop UI | Python 3.12, PyQt6 |
| CLI | Python 3.12, Typer |
| Gedeelde API-client | Python httpx |
| Migratie-script | Python (standalone) |
| Containerisatie (toekomst) | Docker |
