"""
Rich UI components for beautiful CLI output
"""

import os
import getpass
from llm_gardian import __version__
from llm_gardian.stats import SessionStats

# Rich library imports
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None


def get_username():
    """Get the current username"""
    try:
        return getpass.getuser().capitalize()
    except Exception:
        return "User"


def get_short_path(path, max_length=45):
    """Shorten path for display, using ~ for home directory"""
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) > max_length:
        parts = path.split(os.sep)
        if len(parts) > 3:
            path = os.path.join(parts[0], "...", *parts[-2:])
    return path


def print_banner(show_full: bool = True):
    """Display clean and minimal welcome banner"""
    if not RICH_AVAILABLE:
        print(f"LLM-Gardian v{__version__} - Prompt Injection Protection")
        return

    username = get_username()
    cwd = get_short_path(os.getcwd())

    if show_full:
        # Create a clean, centered layout with character logo
        content_lines = [
            "",
            f"              [bold white]Welcome back, {username}[/bold white]",
            "",
            "",
            "                      [bold green]▄▀▀▀▀▀▀▀▄[/bold green]",
            "                     [bold green]█[/bold green] [yellow]◉[/yellow]   [yellow]◉[/yellow] [bold green]█[/bold green]",
            "                     [bold green]█[/bold green]  [yellow]▂▂▂[/yellow]  [bold green]█[/bold green]",
            "                      [bold green]▀▄▄▄▄▄▄▄▀[/bold green]",
            "",
            "",
            f"              [cyan]LLM-Gardian[/cyan] [dim]·[/dim] [dim]v{__version__}[/dim]",
            f"              [dim]{cwd}[/dim]",
            "",
            "",
            "[bold yellow]Quick Start:[/bold yellow]",
            "",
            "  [cyan]llm-gardian[/cyan] [dim]\"your prompt here\"[/dim]     [dim]# Check a single prompt[/dim]",
            "  [cyan]llm-gardian -i[/cyan]                      [dim]# Interactive mode[/dim]",
            "  [cyan]llm-gardian -f[/cyan] [dim]prompts.txt[/dim]         [dim]# Batch check from file[/dim]",
            "  [cyan]llm-gardian -v[/cyan] [dim]\"prompt\"[/dim]            [dim]# Verbose output[/dim]",
            "  [cyan]llm-gardian -t 0.7[/cyan] [dim]\"prompt\"[/dim]       [dim]# Custom threshold[/dim]",
            "",
        ]

        content_text = "\n".join(content_lines)
        content_panel = Text.from_markup(content_text)

        # Simple, elegant panel
        main_panel = Panel(
            content_panel,
            title="[bold cyan]LLM-Gardian[/bold cyan] [dim]Prompt Injection Detection[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    else:
        # Minimal compact banner
        compact_lines = [
            "",
            f"         [bold white]Welcome back, {username}[/bold white]",
            "",
            "",
            "                [bold green]▄▀▀▀▀▀▀▀▄[/bold green]",
            "               [bold green]█[/bold green] [yellow]◉[/yellow]   [yellow]◉[/yellow] [bold green]█[/bold green]",
            "               [bold green]█[/bold green]  [yellow]▂▂▂[/yellow]  [bold green]█[/bold green]",
            "                [bold green]▀▄▄▄▄▄▄▄▀[/bold green]",
            "",
            "",
            f"         [cyan]LLM-Gardian[/cyan] [dim]v{__version__}[/dim]",
            f"         [dim]{cwd}[/dim]",
            "",
        ]

        compact_text = "\n".join(compact_lines)
        compact_panel = Text.from_markup(compact_text)

        main_panel = Panel(
            compact_panel,
            title="[bold cyan]LLM-Gardian[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )

    console.print(main_panel)


def print_interactive_help():
    """Display help for interactive mode commands"""
    if not RICH_AVAILABLE:
        print("\nCommands:")
        print("  exit, quit, q  - Exit interactive mode")
        print("  help, h, ?     - Show this help")
        print("  stats, s       - Show session statistics")
        print("  clear, c       - Clear screen")
        print("  threshold <n>  - Set detection threshold")
        return

    help_table = Table(
        title="[bold yellow]Interactive Commands[/bold yellow]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    help_table.add_column("Command", style="cyan", width=20)
    help_table.add_column("Description", style="white")

    help_table.add_row("exit, quit, q", "Exit interactive mode")
    help_table.add_row("help, h, ?", "Show this help message")
    help_table.add_row("stats, s", "Display session statistics")
    help_table.add_row("clear, c", "Clear the screen")
    help_table.add_row("threshold <n>", "Set detection threshold (0.0-1.0)")
    help_table.add_row("verbose", "Toggle verbose mode on/off")
    help_table.add_row("history", "Show recent checks")

    console.print()
    console.print(help_table)
    console.print()


def print_session_stats(stats: SessionStats):
    """Display session statistics"""
    if not RICH_AVAILABLE:
        print(f"\nSession Statistics:")
        print(f"  Total Checks: {stats.total_checks}")
        print(f"  Safe: {stats.safe_count} | Blocked: {stats.blocked_count}")
        print(f"  Session Time: {stats.elapsed_time}")
        return

    stats_table = Table(
        title="[bold yellow]Session Statistics[/bold yellow]",
        box=box.ROUNDED,
        show_header=False
    )
    stats_table.add_column("Metric", style="cyan", width=20)
    stats_table.add_column("Value", style="white")

    # Create visual bar for safe vs blocked
    if stats.total_checks > 0:
        safe_pct = int((stats.safe_count / stats.total_checks) * 20)
        blocked_pct = 20 - safe_pct
        ratio_bar = f"[green]{'█' * safe_pct}[/green][red]{'█' * blocked_pct}[/red]"
    else:
        ratio_bar = "[dim]No checks yet[/dim]"

    stats_table.add_row("Total Checks", str(stats.total_checks))
    stats_table.add_row("Safe", f"[green]{stats.safe_count}[/green]")
    stats_table.add_row("Blocked", f"[red]{stats.blocked_count}[/red]")
    stats_table.add_row("Safe/Blocked Ratio", ratio_bar)
    stats_table.add_row("Block Rate", f"{stats.block_rate:.1%}")
    stats_table.add_row("Session Time", stats.elapsed_time)

    # Risk level breakdown
    if stats.total_checks > 0:
        risk_breakdown = (
            f"[green]{stats.risk_levels['low']}[/green] Low | "
            f"[yellow]{stats.risk_levels['medium']}[/yellow] Med | "
            f"[#ff8800]{stats.risk_levels['high']}[/#ff8800] High | "
            f"[red]{stats.risk_levels['critical']}[/red] Critical"
        )
        stats_table.add_row("Risk Breakdown", risk_breakdown)

    console.print()
    console.print(stats_table)
    console.print()


def style_risk_level(risk_level: str) -> str:
    """Return styled risk level string"""
    styles = {
        "low": "[green]Low[/green]",
        "medium": "[yellow]Medium[/yellow]",
        "high": "[#ff8800]High[/#ff8800]",
        "critical": "[red]Critical[/red]"
    }
    return styles.get(risk_level, risk_level)
