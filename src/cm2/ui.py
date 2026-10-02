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


def help_screen(commands: list[tuple[str, str]], examples: list[tuple[str, str]], data_dir: str) -> None:
    console.print("[bold]cm2[/bold] - scan, test and stream RTSP/ONVIF cameras and webcams (ffmpeg only)\n")
    table = Table(title="Commands", title_justify="left", show_header=False, box=None, padding=(0, 2))
    for name, text in commands:
        table.add_row(f"[bold cyan]cm2 {name}[/bold cyan]", text)
    console.print(table)
    console.print()
    table = Table(title="Examples", title_justify="left", show_header=False, box=None, padding=(0, 2))
    for cmd, text in examples:
        table.add_row(f"[green]{cmd}[/green]", text)
    console.print(table)
    console.print(
        "\nStream outputs: [bold]M3U8[/bold] (HLS, choose resolution + quality) "
        "or [bold]any http[/bold] (MJPEG, opens in a browser)."
    )
    console.print(f"Saved cameras and stream state: [dim]{data_dir}[/dim]")
    console.print("Add [bold]-h[/bold] or [bold]--help[/bold] to any command for its options.")
