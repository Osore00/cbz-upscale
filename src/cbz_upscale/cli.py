"""CLI interface for CBZ Upscale."""

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from cbz_upscale import __version__
from cbz_upscale.config import build_config, generate_default_config
from cbz_upscale.console import console, create_header_panel, print_error, print_success
from cbz_upscale.pipeline import UpscalePipeline
from cbz_upscale.upscalers import UpscalerRegistry

app = typer.Typer(
    name="cbz-upscale",
    help="CBZ Upscale -- upscale CBZ comic book archives using AI upscalers.",
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print the version and exit."""
    if value:
        typer.echo(f"CBZ Upscale v{__version__}")
        raise typer.Exit()


def init_config_callback(value: bool) -> None:
    """Generate a default config.yaml and exit."""
    if value:
        config_path = Path("config.yaml")
        if config_path.exists():
            print_error("config.yaml already exists in the current directory.")
            raise typer.Exit(code=1)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(generate_default_config())

        print_success("Created config.yaml with default settings.")
        raise typer.Exit()


def list_upscalers_callback(value: bool) -> None:
    """Print a list of available upscaler backends and exit."""
    if value:
        table = Table(title="Available Upscaler Backends", border_style="cyan")
        table.add_column("Name", style="bold green")
        table.add_column("Description")

        backends = UpscalerRegistry.get_all()
        for name, cls in backends.items():
            doc = cls.__doc__.split("\n")[0] if cls.__doc__ else "No description"
            table.add_row(name, doc)

        console.print(table)
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show the application version and exit.",
        ),
    ] = None,
    init_config: Annotated[
        bool | None,
        typer.Option(
            "--init-config",
            callback=init_config_callback,
            is_eager=True,
            help="Generate a default config.yaml in the current directory.",
        ),
    ] = None,
    list_upscalers: Annotated[
        bool | None,
        typer.Option(
            "--list-upscalers",
            callback=list_upscalers_callback,
            is_eager=True,
            help="List all available upscaler backends.",
        ),
    ] = None,
) -> None:
    """Global options and callbacks."""
    pass


# -----------------------------------------------------------------------------
# Common options shared across subcommands
# -----------------------------------------------------------------------------

InputArg = Annotated[
    Path,
    typer.Argument(
        help="Path to a .cbz file or a directory containing .cbz files.",
        exists=True,
    ),
]

ConfigOpt = Annotated[
    Path | None,
    typer.Option(
        "--config",
        "-c",
        help="Path to a YAML configuration file.",
        exists=True,
        dir_okay=False,
    ),
]

OutputOpt = Annotated[
    Path | None,
    typer.Option(
        "--output",
        "-o",
        help="Output file or directory. If not specified, saves next to the input.",
    ),
]

SuffixOpt = Annotated[
    str | None,
    typer.Option(
        "--suffix",
        help="Suffix to append to the output filename (if output is not a specific file).",
    ),
]

KeepTempOpt = Annotated[
    bool | None,
    typer.Option(
        "--keep-temp",
        help="Keep the temporary extraction directory after processing.",
    ),
]

VerboseOpt = Annotated[
    bool | None,
    typer.Option(
        "--verbose",
        "-v",
        help="Enable verbose error output.",
    ),
]


@app.command(name="auto")
def auto_cmd(
    input_path: InputArg,
    config: ConfigOpt = None,
    output: OutputOpt = None,
    suffix: SuffixOpt = None,
    keep_temp: KeepTempOpt = None,
    verbose: VerboseOpt = None,
) -> None:
    """Upscale CBZ archives using the backend specified in config.yaml."""
    try:
        # Build application config. It will read `upscaler` from YAML or default.
        app_config = build_config(
            yaml_path=config,
            input=input_path,
            output=output,
            suffix=suffix,
            keep_temp=keep_temp,
            verbose=verbose,
        )

        # Show header
        s = app_config.get_upscaler_settings()
        gpu_info = str(getattr(s, "gpu_id", "")) if hasattr(s, "gpu_id") and s.gpu_id else "auto"
        scale_info = getattr(s, "scale", "?")
        console.print(create_header_panel(__version__, app_config.upscaler, scale_info, gpu_info))

        # Run pipeline
        pipeline = UpscalePipeline(app_config)
        pipeline.process_batch(input_path)

    except Exception as e:
        print_error(str(e))
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command(name="realesrgan")
def realesrgan_cmd(
    input_path: InputArg,
    config: ConfigOpt = None,
    output: OutputOpt = None,
    suffix: SuffixOpt = None,
    keep_temp: KeepTempOpt = None,
    verbose: VerboseOpt = None,
    # Real-ESRGAN specific options
    scale: Annotated[
        int | None, typer.Option("--scale", "-s", help="Upscale ratio (2, 3, or 4).")
    ] = None,
    model: Annotated[str | None, typer.Option("--model", "-n", help="Model name.")] = None,
    exe_path: Annotated[
        str | None, typer.Option("--exe-path", help="Path to realesrgan-ncnn-vulkan executable.")
    ] = None,
    gpu_id: Annotated[
        str | None,
        typer.Option("--gpu-id", "-g", help="GPU ID(s) to use, comma-separated (e.g., '0,1')."),
    ] = None,
    tile_size: Annotated[
        str | None,
        typer.Option(
            "--tile-size", "-t", help="Tile size, 0 for auto. Comma-separated for multi-GPU."
        ),
    ] = None,
    threads: Annotated[
        str | None, typer.Option("--threads", "-j", help="Thread configuration (e.g., '1:2:2').")
    ] = None,
    tta: Annotated[
        bool | None, typer.Option("--tta", "-x", help="Enable TTA (Test-Time Augmentation) mode.")
    ] = None,
    format: Annotated[
        str | None, typer.Option("--format", "-f", help="Output image format (e.g., 'png', 'jpg').")
    ] = None,
) -> None:
    """Upscale CBZ archives using the Real-ESRGAN backend."""
    try:
        # Map CLI arguments to the nested realesrgan config structure
        realesrgan_overrides = {}
        if scale is not None:
            realesrgan_overrides["scale"] = scale
        if model is not None:
            realesrgan_overrides["model"] = model
        if exe_path is not None:
            realesrgan_overrides["exe_path"] = exe_path
        if gpu_id is not None:
            realesrgan_overrides["gpu_id"] = [int(g) for g in gpu_id.split(",")]
        if tile_size is not None:
            parts = tile_size.split(",")
            realesrgan_overrides["tile_size"] = (
                [int(t) for t in parts] if len(parts) > 1 else int(parts[0])
            )
        if threads is not None:
            realesrgan_overrides["threads"] = threads
        if tta is not None:
            realesrgan_overrides["tta_mode"] = tta
        if format is not None:
            realesrgan_overrides["output_format"] = format

        # Build application config
        app_config = build_config(
            yaml_path=config,
            input=input_path,
            output=output,
            upscaler="realesrgan",
            suffix=suffix,
            keep_temp=keep_temp,
            verbose=verbose,
            realesrgan=realesrgan_overrides if realesrgan_overrides else None,
        )

        # Show header
        s = app_config.get_upscaler_settings()
        gpu_info = str(s.gpu_id) if hasattr(s, "gpu_id") and s.gpu_id else "auto"
        console.print(
            create_header_panel(__version__, "realesrgan", getattr(s, "scale", "?"), gpu_info)
        )

        # Run pipeline
        pipeline = UpscalePipeline(app_config)
        pipeline.process_batch(input_path)

    except Exception as e:
        print_error(str(e))
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command(name="dummy")
def dummy_cmd(
    input_path: InputArg,
    config: ConfigOpt = None,
    output: OutputOpt = None,
    suffix: SuffixOpt = None,
    keep_temp: KeepTempOpt = None,
    verbose: VerboseOpt = None,
    # Dummy specific options
    prefix: Annotated[str | None, typer.Option("--prefix", "-p", help="Filename prefix.")] = None,
    start_number: Annotated[
        int | None, typer.Option("--start", help="Starting number for sequence.")
    ] = None,
    padding: Annotated[int | None, typer.Option("--padding", help="Zero padding length.")] = None,
    format: Annotated[
        str | None, typer.Option("--format", "-f", help="Output image format.")
    ] = None,
) -> None:
    """Test the pipeline using the Dummy backend (copies images without upscaling)."""
    try:
        # Map CLI arguments to the nested dummy config structure
        dummy_overrides = {}
        if prefix is not None:
            dummy_overrides["prefix"] = prefix
        if start_number is not None:
            dummy_overrides["start_number"] = start_number
        if padding is not None:
            dummy_overrides["zero_padding"] = padding
        if format is not None:
            dummy_overrides["output_format"] = format

        # Build application config
        app_config = build_config(
            yaml_path=config,
            input=input_path,
            output=output,
            upscaler="dummy",
            suffix=suffix,
            keep_temp=keep_temp,
            verbose=verbose,
            dummy=dummy_overrides if dummy_overrides else None,
        )

        # Show header
        console.print(create_header_panel(__version__, "dummy", 1, "none"))

        # Run pipeline
        pipeline = UpscalePipeline(app_config)
        pipeline.process_batch(input_path)

    except Exception as e:
        print_error(str(e))
        if verbose:
            console.print_exception()
        sys.exit(1)


# Allow executing the CLI directly during development
if __name__ == "__main__":
    app()
