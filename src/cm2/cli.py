from __future__ import annotations

import click

from . import menu, storage, ui

CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}

EXAMPLES = [
    ("cm2", "open the interactive menu (Scan / Status / Stop a stream / Help / Exit)"),
    ("cm2 scan", "find cameras, test one, pick M3U8 (resolution + quality) or HTTP, and a port"),
    ("cm2 status", "list running streams with their URL, quality and health"),
    ("cm2 stop", "choose a running stream to stop"),
    ("cm2 stop <id>", "stop one stream by its ID (shown by cm2 status)"),
    ("cm2 help stop", "details for one command"),
]


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
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


@main.command("help")
@click.argument("command", required=False)
@click.pass_context
def help_(ctx: click.Context, command: str | None) -> None:
    """Show all commands, or details for one: cm2 help stop"""
    group_ctx = ctx.parent
    if command:
        cmd = main.get_command(group_ctx, command)
        if cmd is None:
            ui.error(f"no command '{command}'. Run 'cm2 help' to see them all.")
            ctx.exit(2)
        click.echo(cmd.get_help(click.Context(cmd, info_name=command, parent=group_ctx)))
        return
    commands = [
        (name, main.commands[name].get_short_help_str(limit=80))
        for name in main.list_commands(group_ctx)
    ]
    ui.help_screen(commands, EXAMPLES, str(storage.BASE_DIR))


if __name__ == "__main__":
    main()
