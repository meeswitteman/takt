# Takt

Persoonlijke taakmanager opgebouwd uit een lokale FastAPI-backend en een PyQt6-desktopapp.

## Architectuur

```
takt/
├── takt-backend/   FastAPI + SQLAlchemy + SQLite
├── takt-desktop/   PyQt6 desktopapp
├── takt-cli/       Optionele CLI-client
└── start-takt.ps1  Opstartscript (Windows)
```

## Functionaliteit

### Projecten
- Hiërarchische projectboom met onbeperkte nesting
- Items aanmaken, hernoemen, verwijderen
- Verplaatsen via Alt+↑/↓ (omhoog/omlaag), Tab (indenteren), Shift+Tab (uitdenten)
- Items markeren als **todo** (●) of **gedaan** ([v]) — markeert recursief alle subitems
- Herhaalbare items tonen het interval achter de naam (bijv. `Taak  - wekelijks`)
- Dubbelklik op een leaf-item opent de editor

### Item-editor (dubbelklik)
- Naam, omschrijving en starttip wijzigen
- Bron instellen (URL of bestandspad) — klikbaar in de todo-kaart
- Status: gedaan / todo
- Context toewijzen (meerdere mogelijk)
- Recurring instellen met interval
- Variatielijst koppelen

### Todo-lijst
- Toont alle actieve todo-items gesorteerd op langst-geleden-gedaan (nooit gedaan bovenaan)
- Breadcrumb toont het pad vanuit de projectboom (bijv. `Project › Subproject`)
- Herhaalbare items tonen het interval achter de naam (bijv. `Taak  - dagelijks`)
- Afvinken met optionele notitie; recurring items verschijnen direct weer onderaan
- Recurring items blijven in de projectboom als niet-gedaan staan
- Volgorde aanpassen via drag & drop of Alt+↑/↓

### Geschiedenis
- Chronologisch overzicht van alle afgevinkelde items (meest recent bovenaan)
- Toont breadcrumb, titel, variatiewaarde en notitie per afvinksessie
- Tijdstip zichtbaar rechts in elke kaart

### Globaal filter
- Filterbaar op een of meer contexten en/of rootprojecten
- Werkt tegelijk op de projectboom én de todo-lijst
- Filter wordt opgeslagen en na herstart hersteld
- Bij één actief rootproject worden de directe subitems automatisch uitgeklapt

### Contexten
- Contexten aanmaken met naam en kleur
- Naam en kleur achteraf wijzigen
- Per item een of meer contexten toewijzen (ook via de editor)

### Variaties
- Variatielijsten beheren (meerdere waarden per lijst)
- Keuzemethode: lineair (volgorde) of willekeurig
- Actieve variatie wordt getoond in de todo-kaart en de geschiedenis

### Instellingen
- Lettertype en -grootte
- Regelafstand in de projectboom
- Licht / donker thema
- Backend URL
- Database kiezen of aanmaken (`.db`-bestand); naam wordt in de titelbalk getoond

## Vereisten

- Python 3.11+
- Windows (opstartscript is PowerShell; de app zelf werkt ook op Linux/macOS)

## Installatie

### Backend

```bash
cd takt-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Desktop

```bash
cd takt-desktop
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Starten

```powershell
.\start-takt.ps1
```

Het script:
1. Leest de gekozen database uit `%APPDATA%\takt\settings.json` (indien aanwezig)
2. Start de backend op poort 8080 in een apart venster
3. Start de desktopapp

### Handmatig starten

```bash
# Backend
cd takt-backend
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Desktop (apart terminal)
cd takt-desktop
python -m app.main
```

### Backend stoppen

Sluit het aparte backend-venster, of via PowerShell:

```powershell
Stop-Process -Name python
```

## Configuratie

Instellingen worden opgeslagen in `%APPDATA%\takt\settings.json`:

| Sleutel | Standaard | Omschrijving |
|---|---|---|
| `api_url` | `http://127.0.0.1:8080` | Backend URL |
| `theme` | `dark` | `dark` of `light` |
| `font_family` | `Segoe UI` | Lettertype |
| `font_size` | `10` | Lettergrootte in pt |
| `item_spacing` | `12` | Regelafstand projectboom in px |
| `db_path` | *(backend standaard)* | Pad naar SQLite-database |
| `filter_context_ids` | `[]` | Opgeslagen contextfilter |
| `filter_root_ids` | `[]` | Opgeslagen projectfilter |

De backend gebruikt standaard `%APPDATA%\takt\takt.db`. Een alternatieve database stel je in via **Bestand → Database kiezen...** of via de omgevingsvariabele `TAKT_DB_PATH`.

## Recurring intervallen

| Waarde | Betekenis |
|---|---|
| `direct` | Verschijnt direct weer na afvinken |
| `daily` | Eenmaal per dag |
| `weekly` | Eenmaal per 7 dagen |
| `weekday:0` t/m `weekday:6` | Specifieke weekdag (0 = maandag) |
| `monthly_first` | Eerste van elke maand |

## Navigatie (menubar)

| Menu-item | Weergave |
|---|---|
| Project | Projectboom |
| Todo | Todo-lijst |
| Filter | Globaal filter |
| Geschiedenis | Afvinkhistorie |

## Sneltoetsen (projectboom)

| Toets | Actie |
|---|---|
| Alt+↑ / Alt+↓ | Item omhoog / omlaag |
| Tab | Item indenteren (kind van vorige sibling) |
| Shift+Tab | Item uitdenten |
| Ctrl+N | Nieuw sub-item |
| F2 | Hernoemen |
| Del | Verwijderen |
| Dubbelklik | Editor openen (alleen leaf-items) |

## Sneltoetsen (todo-lijst)

| Toets | Actie |
|---|---|
| Alt+↑ / Alt+↓ | Item omhoog / omlaag |
| Drag & drop | Vrij herordenen |
