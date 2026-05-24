"""
Medo v1 → Takt migratie-script

Leest bestanden uit ~/.medo/ en importeert ze in de Takt SQLite database.

Gebruik:
    python migrate.py [--medo-dir <pad>] [--db <pad>]
"""

import re
import sys
import random
import argparse
from datetime import datetime
from pathlib import Path

# Voeg backend toe aan path zodat we de modellen kunnen hergebruiken
sys.path.insert(0, str(Path(__file__).parent.parent / "takt-backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, selectinload
from app.database import Base
from app.models.item import Item, ItemContext, TodoLog
from app.models.context import Context
from app.models.variation import VariationList, VariationEntry


# ---------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------

def parse_attributes(raw: str) -> dict:
    """Verwerk 'key=value | key=value' naar dict. Waarden mogen spaties bevatten."""
    attrs = {}
    for part in raw.split("|"):
        part = part.strip()
        if "=" in part:
            key, _, value = part.partition("=")
            attrs[key.strip()] = value.strip().strip('"')
    return attrs


def parse_item_line(line: str) -> tuple[str, str | None, dict]:
    """
    Geeft terug: (title, context_name_or_None, attrs_dict)
    Formaat: 'titel :: context | key=val | key=val'
    """
    context_name = None
    attrs = {}

    # Splits op eerste '|'
    if "|" in line:
        title_part, _, attr_part = line.partition("|")
        attrs = parse_attributes(attr_part)
    else:
        title_part = line

    # Splits op '::' voor context
    if "::" in title_part:
        title_part, _, ctx = title_part.partition("::")
        context_name = ctx.strip()

    return title_part.strip(), context_name, attrs


def parse_projects(path: Path) -> list[dict]:
    """
    Leest projects.txt en geeft een platte lijst van items terug met:
      depth, title, context_name, attrs
    """
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        stripped = line.lstrip("\t")
        depth = len(line) - len(stripped)
        title, context_name, attrs = parse_item_line(stripped)
        items.append({"depth": depth, "title": title, "context_name": context_name, "attrs": attrs})
    return items


def parse_todo_file(path: Path) -> list[dict]:
    """
    Leest een <context>-TODO.txt en geeft per regel:
      leaf_title, full_line, attrs
    """
    todos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue

        if "|" in line:
            title_part, _, attr_part = line.partition("|")
            attrs = parse_attributes(attr_part)
        else:
            title_part = line
            attrs = {}

        title_part = title_part.strip()

        # Extraheer leaf title uit pad-notatie: 'Root  Parent - Leaf'
        # Dubbele spatie geldt alleen als padseparator als het prefix een enkel woord is
        is_path = False
        if "  " in title_part:
            prefix = title_part[:title_part.index("  ")]
            if " " not in prefix:
                is_path = True

        if is_path:
            _, _, rest = title_part.partition("  ")
            if " - " in rest:
                leaf = rest.rsplit(" - ", 1)[-1].strip()
            else:
                leaf = rest.strip()
        elif " - " in title_part:
            leaf = title_part.rsplit(" - ", 1)[-1].strip()
        else:
            leaf = title_part

        todos.append({"leaf_title": leaf, "full_line": title_part, "attrs": attrs})
    return todos


def parse_done_file(path: Path) -> list[dict]:
    """
    Leest DONE.txt: '2025-09-28 11:50:26 - beschrijving'
    """
    entries = []
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - (.+)$")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            description = m.group(2).strip()
            entries.append({"completed_at": ts, "description": description})
    return entries


def parse_variation_file(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_settings(path: Path) -> dict:
    settings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


# ---------------------------------------------------------------------------
# Import functies
# ---------------------------------------------------------------------------

def import_contexts(session: Session, context_names: list[str], default_colors: dict) -> dict[str, Context]:
    """Maak contexts aan, geef mapping name→Context terug."""
    colors = {
        "bass": "#ff6600", "AI": "#00aaff", "exercise": "#00cc44",
        "jam4life": "#cc00cc", "dev": "#ffcc00", "NOTDO": "#888888",
        "test": "#ff0000",
    }
    colors.update(default_colors)

    result = {}
    for name in context_names:
        existing = session.query(Context).filter(Context.name == name).first()
        if existing:
            result[name] = existing
        else:
            ctx = Context(name=name, color=colors.get(name, "#888888"))
            session.add(ctx)
            session.flush()
            result[name] = ctx
    return result


def import_variation_lists(session: Session, medo_dir: Path) -> dict[str, VariationList]:
    """Importeer alle variation-*.txt bestanden."""
    result = {}
    for path in sorted(medo_dir.glob("variation-*.txt")):
        name = path.stem.replace("variation-", "")
        values = parse_variation_file(path)
        if not values:
            continue

        existing = session.query(VariationList).filter(VariationList.name == name).first()
        if existing:
            vl = existing
        else:
            vl = VariationList(name=name)
            session.add(vl)
            session.flush()
            for i, value in enumerate(values):
                session.add(VariationEntry(list_id=vl.id, position=i, value=value))

        result[name] = vl
        print(f"  Variatielijst '{name}': {len(values)} entries")

    return result


def import_project_tree(
    session: Session,
    raw_items: list[dict],
    context_map: dict[str, Context],
    variation_map: dict[str, VariationList],
) -> list[Item]:
    """Bouw de projectboom op in de database."""
    stack: list[tuple[int, Item]] = []  # (depth, item)
    all_items: list[Item] = []

    for raw in raw_items:
        depth = raw["depth"]
        title = raw["title"]
        ctx_name = raw["context_name"]
        attrs = raw["attrs"]

        # Bepaal ouder
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent_id = stack[-1][1].id if stack else None

        # Volgorde binnen ouder
        sibling_count = session.query(Item).filter(Item.parent_id == parent_id).count()

        # Variatielijst koppelen
        vl_id = None
        vl_mode = None
        vl_index = 0
        if "var" in attrs and attrs["var"] in variation_map:
            vl = variation_map[attrs["var"]]
            vl_id = vl.id
            vl_mode = attrs.get("varm", "linear")
            vl_index = int(attrs.get("varidx", 0))

        item = Item(
            parent_id=parent_id,
            title=title,
            order_index=sibling_count,
            src=attrs.get("src"),
            start_note=attrs.get("start"),
            variation_list_id=vl_id,
            variation_mode=vl_mode,
            variation_index=vl_index,
        )
        session.add(item)
        session.flush()

        # Context koppelen
        if ctx_name and ctx_name in context_map:
            session.add(ItemContext(item_id=item.id, context_id=context_map[ctx_name].id))

        stack.append((depth, item))
        all_items.append(item)

    return all_items


def build_title_index(session: Session) -> dict[str, list[Item]]:
    """Bouw een lowercase-titel → [Item] index voor snel opzoeken."""
    index: dict[str, list[Item]] = {}
    for item in session.query(Item).all():
        key = item.title.lower().strip()
        index.setdefault(key, []).append(item)
    return index


def apply_todos(
    session: Session,
    medo_dir: Path,
    context_map: dict[str, Context],
    variation_map: dict[str, VariationList],
    title_index: dict[str, list[Item]],
) -> None:
    """Markeer items als todo op basis van <context>-TODO.txt bestanden."""
    for path in sorted(medo_dir.glob("*-TODO.txt")):
        context_name = path.stem.replace("-TODO", "")
        todos = parse_todo_file(path)
        print(f"  {path.name}: {len(todos)} todo(s)")

        for todo in todos:
            leaf = todo["leaf_title"].lower().strip()
            attrs = todo["attrs"]
            matched = title_index.get(leaf)
            item = matched[0] if matched else None

            if item is None:
                # Nieuw standalone item aanmaken — volledige titel bewaren
                full_title = todo["full_line"]
                sibling_count = session.query(Item).filter(Item.parent_id == None).count()
                vl_id = None
                vl_mode = None
                vl_index = 0
                if "var" in attrs and attrs["var"] in variation_map:
                    vl = variation_map[attrs["var"]]
                    vl_id = vl.id
                    vl_mode = attrs.get("varm", "linear")
                    vl_index = int(attrs.get("varidx", 0))

                item = Item(
                    parent_id=None,
                    title=full_title,
                    order_index=sibling_count,
                    src=attrs.get("src"),
                    start_note=attrs.get("start"),
                    variation_list_id=vl_id,
                    variation_mode=vl_mode,
                    variation_index=vl_index,
                )
                session.add(item)
                session.flush()
                # Titel-index bijwerken zodat duplicaten in andere TODO-files matchen
                key = item.title.lower().strip()
                title_index.setdefault(key, []).append(item)
                print(f"    + nieuw item aangemaakt: '{item.title}'")
            else:
                # Attributen uit TODO-bestand zijn actueler — overschrijven
                if attrs.get("src"):
                    item.src = attrs["src"]
                if attrs.get("start"):
                    item.start_note = attrs["start"]
                if "var" in attrs and attrs["var"] in variation_map:
                    vl = variation_map[attrs["var"]]
                    item.variation_list_id = vl.id
                    item.variation_mode = attrs.get("varm", "linear")
                    item.variation_index = int(attrs.get("varidx", 0))

            item.is_todo = True

            # Context koppelen als nog niet gedaan
            if context_name in context_map:
                ctx = context_map[context_name]
                exists = session.query(ItemContext).filter(
                    ItemContext.item_id == item.id,
                    ItemContext.context_id == ctx.id,
                ).first()
                if not exists:
                    session.add(ItemContext(item_id=item.id, context_id=ctx.id))


def import_done_log(session: Session, medo_dir: Path) -> None:
    """Importeer DONE.txt als historische TodoLog entries (zonder item-koppeling)."""
    done_path = medo_dir / "DONE.txt"
    if not done_path.exists():
        return

    entries = parse_done_file(done_path)
    print(f"  DONE.txt: {len(entries)} historische entries")

    # Maak een speciaal historisch item aan als anker voor de log
    archive = session.query(Item).filter(Item.title == "[Medo v1 archief]").first()
    if not archive:
        count = session.query(Item).filter(Item.parent_id == None).count()
        archive = Item(title="[Medo v1 archief]", order_index=count, is_todo=False)
        session.add(archive)
        session.flush()

    for entry in entries:
        log = TodoLog(
            item_id=archive.id,
            action="DONE",
            note=entry["description"],
            completed_at=entry["completed_at"],
        )
        session.add(log)


# ---------------------------------------------------------------------------
# Hoofdroutine
# ---------------------------------------------------------------------------

def migrate(medo_dir: Path, db_path: Path) -> None:
    print(f"\nMigratie starten")
    print(f"  Bron : {medo_dir}")
    print(f"  Doel : {db_path}\n")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        # 1. Settings → contextnamen
        settings_path = medo_dir / "medo-settings.properties"
        context_names = []
        if settings_path.exists():
            settings = parse_settings(settings_path)
            raw = settings.get("contexts", "")
            context_names = [c.strip() for c in raw.split(",") if c.strip()]
        print(f"Stap 1 — Contexten: {context_names}")
        context_map = import_contexts(session, context_names, {})
        session.commit()

        # 2. Variatielijsten
        print("Stap 2 — Variatielijsten:")
        variation_map = import_variation_lists(session, medo_dir)
        session.commit()

        # 3. Projectboom
        projects_path = medo_dir / "projects.txt"
        raw_items = parse_projects(projects_path)
        print(f"Stap 3 — Projectboom: {len(raw_items)} items")
        import_project_tree(session, raw_items, context_map, variation_map)
        session.commit()

        # 4. Todo-bestanden
        print("Stap 4 — Todo's:")
        title_index = build_title_index(session)
        apply_todos(session, medo_dir, context_map, variation_map, title_index)
        session.commit()

        # 5. DONE.txt
        print("Stap 5 — Geschiedenis:")
        import_done_log(session, medo_dir)
        session.commit()

        # Samenvatting
        total_items = session.query(Item).count()
        total_todos = session.query(Item).filter(Item.is_todo == True).count()
        total_contexts = session.query(Context).count()
        total_vlists = session.query(VariationList).count()
        total_logs = session.query(TodoLog).count()

        print(f"\nKlaar!")
        print(f"  Items      : {total_items}")
        print(f"  Todo's     : {total_todos}")
        print(f"  Contexten  : {total_contexts}")
        print(f"  Variaties  : {total_vlists}")
        print(f"  Log entries: {total_logs}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Medo v1 → Takt migratie")
    parser.add_argument(
        "--medo-dir",
        default=str(Path.home() / ".medo"),
        help="Pad naar de .medo directory (default: ~/.medo)",
    )
    parser.add_argument(
        "--db",
        default=str(Path.home() / "AppData" / "Roaming" / "takt" / "takt.db"),
        help="Pad naar de Takt SQLite database",
    )
    args = parser.parse_args()
    migrate(Path(args.medo_dir), Path(args.db))
