import sys
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text

console = Console(highlight=False)


def _context_chips(contexts: list) -> Text:
    text = Text()
    for i, ctx in enumerate(contexts):
        if i:
            text.append(" ")
        text.append(f" {ctx['name']} ", style=f"bold on {ctx['color']}")
    return text


def _variation_hint(item: dict) -> str:
    v = item.get("current_variation")
    return f"  [dim]→ {v}[/dim]" if v else ""


def print_todos(items: list) -> None:
    if not items:
        console.print("[dim]Geen actieve todo's.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=5, justify="right")
    table.add_column("Titel")
    table.add_column("Variatie", style="cyan")
    table.add_column("Contexten")
    table.add_column("Start", style="yellow")

    for item in items:
        recurring = " ↺" if item.get("is_recurring") else ""
        table.add_row(
            str(item["id"]),
            item["title"] + recurring,
            item.get("current_variation") or "",
            _context_chips(item.get("contexts", [])),
            item.get("start_note") or "",
        )

    console.print(table)


def print_tree(items: list, depth: int = 0) -> None:
    for item in items:
        prefix = "  " * depth + ("- " if depth else "")
        todo_marker = " [green]*[/green]" if item.get("is_todo") else ""
        console.print(f"[dim]{item['id']:>4}[/dim]  {prefix}{item['title']}{todo_marker}")


def print_item(item: dict) -> None:
    console.print(f"\n[bold]{item['title']}[/bold]  [dim]#{item['id']}[/dim]")
    if item.get("description"):
        console.print(f"  {item['description']}")
    if item.get("src"):
        console.print(f"  [blue underline]{item['src']}[/blue underline]")
    if item.get("start_note"):
        console.print(f"  [yellow]→ {item['start_note']}[/yellow]")
    if item.get("current_variation"):
        console.print(f"  [cyan]variatie: {item['current_variation']}[/cyan]")
    contexts = item.get("contexts", [])
    if contexts:
        console.print("  ", end="")
        console.print(_context_chips(contexts))
    console.print()


def print_history(logs: list, item_title: str) -> None:
    if not logs:
        console.print("[dim]Geen geschiedenis.[/dim]")
        return
    console.print(f"\n[bold]Geschiedenis: {item_title}[/bold]\n")
    for log in logs:
        ts = log["completed_at"][:16].replace("T", " ")
        note = f"  [dim]{log['note']}[/dim]" if log.get("note") else ""
        var = f"  [cyan]{log['variation_value']}[/cyan]" if log.get("variation_value") else ""
        console.print(f"  [green]{ts}[/green]{var}{note}")
    console.print()
