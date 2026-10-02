from __future__ import annotations

import click

from . import menu, storage


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """cm2: scan, test, and stream RTSP/ONVIF cameras and webcams, ffmpeg-only."""
    storage.ensure_base_dir()
    if ctx.invoked_subcommand is None:
        menu.main_menu()


@main.command()
def scan() -> None:
    """Scan for cameras and set up a stream."""
    menu.scan_flow()


@main.command()
def status() -> None:
    """Show currently running streams."""
    menu.status_flow()


@main.command()
@click.argument("stream_id", required=False)
def stop(stream_id: str | None) -> None:
    """Stop a running stream (prompts for one if STREAM_ID is omitted)."""
    menu.stop_flow(stream_id)


if __name__ == "__main__":
    main()
