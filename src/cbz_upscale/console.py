"""Rich console helpers and themed output for CBZ Upscale."""

from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.theme import Theme

# Custom theme for consistent, professional branding
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "step.pending": "dim white",
        "step.active": "cyan",
        "step.done": "green",
        "step.failed": "red",
        "panel.border": "cyan",
        "header.title": "bold white",
        "header.value": "cyan",
    }
)

# Global singleton console
console = Console(theme=custom_theme)

def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]✗ ERROR:[/error] {message}")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]! WARNING:[/warning] {message}")

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓[/success] {message}")

def create_header_panel(version: str, upscaler: str, scale: int, gpu_info: str) -> Panel:
    """Create a beautiful header panel for the CLI."""
    content = (
        f"[header.title]Backend:[/header.title] [header.value]{upscaler}[/header.value] │ "
        f"[header.title]Scale:[/header.title] [header.value]{scale}x[/header.value] │ "
        f"[header.title]GPU:[/header.title] [header.value]{gpu_info}[/header.value]"
    )
    return Panel(
        content,
        title=f"📦 CBZ Upscale v{version}",
        title_align="left",
        border_style="panel.border",
        padding=(0, 2),
    )

def create_progress() -> Progress:
    """Create a pre-configured Rich Progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True, # Remove progress bar when done
    )

@contextmanager
def step_status(description: str) -> Generator[None, None, None]:
    """Context manager for tracking the status of a specific pipeline step.
    
    Usage:
        with step_status("Extracting archive") as status:
            do_work()
    """
    console.print(f"  [step.pending]├─[/step.pending] {description}...", end="")
    try:
        yield
        console.print(f"\r  [step.done]├─ ✓[/step.done] {description}   ")
    except Exception as e:
        console.print(f"\r  [step.failed]├─ ✗[/step.failed] {description} (Error: {e})")
        raise

def print_summary(files_processed: int, total_time_sec: float) -> None:
    """Print the final completion summary."""
    mins, secs = divmod(int(total_time_sec), 60)
    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    
    console.print()
    console.print(
        f"[success]✅ Done![/success] Processed {files_processed} archive(s) "
        f"in {time_str}"
    )
