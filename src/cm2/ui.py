from __future__ import annotations

from rich.console import Console
from rich.table import Table

console = Console()

HEALTH_STYLE = {
    "running": "green",
    "port-down": "yellow",
    "dead": "red",
}


def success(message: str) -> None:
    console.print(f"[bold green]success!![/bold green] {message}")


def error(message: str) -> None:
    console.print(f"[bold red]error:[/bold red] {message}")


def info(message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")


def done(message: str) -> None:
    console.print(f"[bold green]DONE[/bold green] {message}")


def streams_table(rows: list[dict]) -> Table:
    table = Table(title="Running streams")
    table.add_column("ID")
    table.add_column("Camera")
    table.add_column("Protocol")
    table.add_column("Port")
    table.add_column("Status")
    table.add_column("URL")
    for row in rows:
        style = HEALTH_STYLE.get(row["status"], "white")
        table.add_row(
            row["id"], row["camera"], row["protocol"], str(row["port"]),
            f"[{style}]{row['status']}[/{style}]", row["url"],
        )
    return table
