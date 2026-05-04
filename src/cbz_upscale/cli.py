"""CLI interface for CBZ Upscale."""

import typer

app = typer.Typer(
    name="cbz-upscale",
    help="🖼️  CBZ Upscale — upscale CBZ comic book archives using AI upscalers.",
    no_args_is_help=True,
)
