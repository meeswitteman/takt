import typer
import httpx
from typing import Optional
from takt import client, output

app = typer.Typer(
    name="takt",
    help="Takt — persoonlijke taakmanager",
    no_args_is_help=True,
)


def _handle_error(e: Exception) -> None:
    if isinstance(e, httpx.ConnectError):
        output.console.print("[red]Kan geen verbinding maken met de backend. Draait uvicorn?[/red]")
    elif isinstance(e, httpx.HTTPStatusError):
        output.console.print(f"[red]API fout {e.response.status_code}: {e.response.text}[/red]")
    else:
        output.console.print(f"[red]{e}[/red]")
    raise typer.Exit(1)


@app.command("todos")
def todos(
    context: Optional[str] = typer.Option(None, "--context", "-c", help="Filter op context (bijv. bass)"),
):
    """Toon actieve todo's."""
    try:
        items = client.get_todos(context)
        output.print_todos(items)
    except Exception as e:
        _handle_error(e)


@app.command("done")
def done(
    item_id: int = typer.Argument(..., help="ID van het todo-item"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Optionele notitie"),
):
    """Vink een todo af."""
    try:
        item = client.mark_done(item_id, note)
        status = "↺ opnieuw in de lijst" if item["is_todo"] else "✓ afgevinkt"
        output.console.print(f"[green]{status}:[/green] {item['title']}")
    except Exception as e:
        _handle_error(e)


@app.command("add")
def add(
    title: str = typer.Argument(..., help="Titel van het nieuwe item"),
    parent: Optional[int] = typer.Option(None, "--parent", "-p", help="ID van het ouder-item"),
):
    """Voeg een nieuw item toe aan de projectboom."""
    try:
        item = client.create_item(parent, title)
        output.console.print(f"[green]Aangemaakt:[/green] {item['title']}  [dim]#{item['id']}[/dim]")
    except Exception as e:
        _handle_error(e)


@app.command("todo")
def mark_todo(
    item_id: int = typer.Argument(..., help="ID van het item"),
    off: bool = typer.Option(False, "--off", help="Verwijder todo-markering"),
):
    """Markeer een item als todo (of verwijder de markering met --off)."""
    try:
        item = client.set_todo(item_id, not off)
        status = "todo" if item["is_todo"] else "niet meer als todo gemarkeerd"
        output.console.print(f"[green]{status}:[/green] {item['title']}")
    except Exception as e:
        _handle_error(e)


@app.command("show")
def show(
    item_id: int = typer.Argument(..., help="ID van het item"),
):
    """Toon details van een item."""
    try:
        item = client.get_item(item_id)
        output.print_item(item)
    except Exception as e:
        _handle_error(e)


@app.command("history")
def history(
    item_id: int = typer.Argument(..., help="ID van het item"),
):
    """Toon afvink-geschiedenis van een item."""
    try:
        item = client.get_item(item_id)
        logs = client.get_history(item_id)
        output.print_history(logs, item["title"])
    except Exception as e:
        _handle_error(e)


@app.command("ls")
def ls(
    item_id: Optional[int] = typer.Argument(None, help="ID van het item (leeg = root)"),
):
    """Toon de projectboom (of kinderen van een item)."""
    try:
        if item_id is None:
            items = client.get_roots()
        else:
            items = client.get_children(item_id)
        output.print_tree(items)
    except Exception as e:
        _handle_error(e)


@app.command("contexts")
def contexts():
    """Toon alle contexten."""
    try:
        ctxs = client.get_contexts()
        for ctx in ctxs:
            output.console.print(f"  [dim]{ctx['id']:>3}[/dim]  [bold on {ctx['color']}] {ctx['name']} [/bold on {ctx['color']}]")
    except Exception as e:
        _handle_error(e)


@app.command("health")
def health():
    """Controleer of de backend bereikbaar is."""
    try:
        result = client.health()
        output.console.print(f"[green]Backend online[/green]  {result}")
    except Exception as e:
        _handle_error(e)


def main():
    app()


if __name__ == "__main__":
    main()
