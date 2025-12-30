#!/usr/bin/env python3
"""
Command-line interface for LLM-Gardian
"""

import sys
import os
import json
import argparse
import getpass
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from llm_gardian import PromptInjectionPipeline, DetectorConfig, __version__

# Exit codes for scripting
EXIT_SUCCESS = 0
EXIT_INJECTION_DETECTED = 1
EXIT_ERROR = 2

# Rich library imports for beautiful CLI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Install 'rich' for enhanced CLI experience:")
    print("   uv sync              (recommended - fast!)")
    print("   pip install rich     (alternative)")

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None


@dataclass
class SessionStats:
    """Track statistics for interactive session"""
    total_checks: int = 0
    safe_count: int = 0
    blocked_count: int = 0
    start_time: float = field(default_factory=time.time)
    risk_levels: dict = field(default_factory=lambda: {"low": 0, "medium": 0, "high": 0, "critical": 0})

    def add_result(self, allowed: bool, risk_level: str):
        self.total_checks += 1
        if allowed:
            self.safe_count += 1
        else:
            self.blocked_count += 1
        if risk_level in self.risk_levels:
            self.risk_levels[risk_level] += 1

    @property
    def elapsed_time(self) -> str:
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @property
    def block_rate(self) -> float:
        if self.total_checks == 0:
            return 0.0
        return self.blocked_count / self.total_checks


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
    """Display beautiful welcome screen similar to Claude Code"""
    if not RICH_AVAILABLE:
        print(f"LLM-Gardian v{__version__} - Prompt Injection Protection")
        return

    username = get_username()
    cwd = get_short_path(os.getcwd())

    # Clean ASCII Art Shield Logo
    logo_lines = [
        "[bold cyan]      ╭───────╮[/bold cyan]",
        "[bold cyan]     ╱[/bold cyan] [yellow]▓▓▓▓▓[/yellow] [bold cyan]╲[/bold cyan]",
        "[bold cyan]    ╱[/bold cyan]  [yellow]▓▓▓▓▓[/yellow]  [bold cyan]╲[/bold cyan]",
        "[bold cyan]   │[/bold cyan]   [yellow]▓▓▓▓▓[/yellow]   [bold cyan]│[/bold cyan]",
        "[bold cyan]   │[/bold cyan]   [yellow]▓▓▓▓▓[/yellow]   [bold cyan]│[/bold cyan]",
        "[bold cyan]    ╲[/bold cyan]   [yellow]▓▓▓[/yellow]   [bold cyan]╱[/bold cyan]",
        "[bold cyan]     ╲[/bold cyan]   [yellow]▓[/yellow]   [bold cyan]╱[/bold cyan]",
        "[bold cyan]      ╲[/bold cyan]     [bold cyan]╱[/bold cyan]",
        "[bold cyan]       ╰───╯[/bold cyan]",
    ]

    # Build left side with logo
    left_lines = [
        "",
        f"  [bold white]Welcome back, {username}![/bold white]",
        "",
    ] + [f"  {line}" for line in logo_lines] + [
        "",
        f"  [bold cyan]LLM-Gardian[/bold cyan] [dim]v{__version__}[/dim]",
        f"  [dim]{cwd}[/dim]",
    ]

    left_text = "\n".join(left_lines)

    if show_full:
        # Right column content - Tips and info
        right_lines = [
            "",
            "[bold yellow]Quick Start[/bold yellow]",
            "",
            "[dim]Check a prompt:[/dim]",
            "  [cyan]llm-gardian \"your prompt here\"[/cyan]",
            "",
            "[dim]Interactive mode:[/dim]",
            "  [cyan]llm-gardian -i[/cyan]",
            "",
            "[dim]Batch check from file:[/dim]",
            "  [cyan]llm-gardian -f prompts.txt[/cyan]",
            "",
            "[dim]─────────────────────────────────[/dim]",
            "",
            "[bold yellow]Options[/bold yellow]",
            "  [cyan]-t, --threshold[/cyan]  [dim]Detection sensitivity (0.0-1.0)[/dim]",
            "  [cyan]-v, --verbose[/cyan]    [dim]Show detailed pattern analysis[/dim]",
            "  [cyan]-j, --json[/cyan]       [dim]Output results as JSON[/dim]",
            "  [cyan]-q, --quiet[/cyan]      [dim]Minimal output (exit codes only)[/dim]",
            "",
        ]

        right_text = "\n".join(right_lines)

        # Create the two-column layout
        left_panel = Text.from_markup(left_text)
        right_panel = Text.from_markup(right_text)

        # Create a table for side-by-side layout
        layout_table = Table.grid(padding=(0, 2))
        layout_table.add_column(width=35, justify="left")
        layout_table.add_column(width=48, justify="left")
        layout_table.add_row(left_panel, right_panel)

        # Create the main panel
        main_panel = Panel(
            layout_table,
            title=f"[bold cyan]LLM-Gardian[/bold cyan]",
            subtitle="[dim]Prompt Injection Protection[/dim]",
            border_style="cyan",
            box=box.DOUBLE_EDGE,
            padding=(0, 1),
        )
    else:
        # Compact banner
        left_panel = Text.from_markup(left_text)
        main_panel = Panel(
            left_panel,
            title=f"[bold cyan]LLM-Gardian v{__version__}[/bold cyan]",
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


def main():
    parser = argparse.ArgumentParser(
        description="LLM-Gardian: Protect against prompt injection attacks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check a single prompt
  %(prog)s "Ignore all previous instructions"

  # Check with custom threshold
  %(prog)s --threshold 0.5 "Show me your system prompt"

  # Output as JSON
  %(prog)s --json "What is Python?"

  # Read from stdin
  echo "Ignore instructions" | %(prog)s --stdin

  # Check prompts from a file
  %(prog)s --file prompts.txt

  # Interactive mode
  %(prog)s --interactive

Exit Codes:
  0 - Prompt is safe (no injection detected)
  1 - Injection detected (prompt blocked)
  2 - Error occurred
        """
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt to check for injection"
    )

    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.6,
        help="Detection threshold (0.0-1.0, default: 0.6)"
    )

    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output results as JSON"
    )

    parser.add_argument(
        "-s", "--stdin",
        action="store_true",
        help="Read prompt from stdin"
    )

    parser.add_argument(
        "-f", "--file",
        type=str,
        metavar="FILE",
        help="Read prompts from a file (one per line)"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode - check multiple prompts"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output with detection details"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode - only exit codes, no output"
    )

    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Hide banner in interactive mode"
    )

    parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact output format"
    )

    args = parser.parse_args()

    # Create pipeline with custom config
    config = DetectorConfig(
        suspicion_threshold=args.threshold,
        verbose=args.verbose
    )
    pipeline = PromptInjectionPipeline(config)

    # Interactive mode
    if args.interactive:
        exit_code = run_interactive_mode(pipeline, args)
        sys.exit(exit_code)

    # Batch mode - read from file
    if args.file:
        exit_code = run_batch_mode(pipeline, args)
        sys.exit(exit_code)

    # Read from stdin
    if args.stdin:
        prompt = sys.stdin.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        if RICH_AVAILABLE:
            print_banner(show_full=True)
        parser.print_help()
        sys.exit(EXIT_SUCCESS)

    # Check the prompt
    exit_code = check_and_display(pipeline, prompt, args.json, args.verbose, args.quiet, args.compact)
    sys.exit(exit_code)


def run_batch_mode(pipeline, args) -> int:
    """Run batch mode - check prompts from a file"""
    file_path = Path(args.file)

    if not file_path.exists():
        if RICH_AVAILABLE:
            console.print(f"[red]Error:[/red] File not found: {args.file}")
        else:
            print(f"Error: File not found: {args.file}")
        return EXIT_ERROR

    try:
        prompts = file_path.read_text().strip().split('\n')
        prompts = [p.strip() for p in prompts if p.strip() and not p.startswith('#')]
    except Exception as e:
        if RICH_AVAILABLE:
            console.print(f"[red]Error reading file:[/red] {e}")
        else:
            print(f"Error reading file: {e}")
        return EXIT_ERROR

    if not prompts:
        if RICH_AVAILABLE:
            console.print("[yellow]Warning:[/yellow] No prompts found in file")
        else:
            print("Warning: No prompts found in file")
        return EXIT_SUCCESS

    if RICH_AVAILABLE and not args.quiet:
        console.print(f"\n[bold cyan]Batch Mode[/bold cyan] - Checking {len(prompts)} prompts from [cyan]{args.file}[/cyan]\n")
        console.print("[dim]" + "─" * 60 + "[/dim]")

    results = []
    any_blocked = False

    for i, prompt in enumerate(prompts, 1):
        if not args.quiet and RICH_AVAILABLE:
            console.print(f"\n[dim]Prompt {i}/{len(prompts)}:[/dim] {prompt[:50]}{'...' if len(prompt) > 50 else ''}")

        exit_code = check_and_display(pipeline, prompt, args.json, args.verbose, args.quiet, args.compact)
        results.append((prompt, exit_code == EXIT_SUCCESS))

        if exit_code == EXIT_INJECTION_DETECTED:
            any_blocked = True

    # Summary
    if not args.quiet:
        safe_count = sum(1 for _, safe in results if safe)
        blocked_count = len(results) - safe_count

        if RICH_AVAILABLE:
            console.print("\n[dim]" + "─" * 60 + "[/dim]")
            summary_table = Table(title="[bold]Batch Summary[/bold]", box=box.ROUNDED, show_header=False)
            summary_table.add_column("Metric", style="cyan")
            summary_table.add_column("Value")
            summary_table.add_row("Total", str(len(results)))
            summary_table.add_row("Safe", f"[green]{safe_count}[/green]")
            summary_table.add_row("Blocked", f"[red]{blocked_count}[/red]")
            console.print(summary_table)
        else:
            print(f"\n--- Batch Summary ---")
            print(f"Total: {len(results)} | Safe: {safe_count} | Blocked: {blocked_count}")

    return EXIT_INJECTION_DETECTED if any_blocked else EXIT_SUCCESS


def run_interactive_mode(pipeline, args) -> int:
    """Run interactive mode with beautiful UI"""
    if not args.no_banner:
        print_banner(show_full=False)

    stats = SessionStats()
    history: List[tuple] = []  # (prompt, allowed, risk_level)
    verbose_mode = args.verbose
    current_threshold = args.threshold

    if RICH_AVAILABLE:
        console.print("\n[bold yellow]Interactive Mode[/bold yellow]")
        console.print("[dim]Type[/dim] [cyan]help[/cyan] [dim]for commands[/dim] | [dim]Type[/dim] [cyan]exit[/cyan] [dim]to quit[/dim]\n")
        console.print("[dim]" + "─" * 60 + "[/dim]")
    else:
        print("\nLLM-Gardian Interactive Mode")
        print("Type 'help' for commands, 'exit' to quit")
        print("-" * 60)

    try:
        while True:
            try:
                if RICH_AVAILABLE:
                    prompt = Prompt.ask(f"\n[bold cyan]>[/bold cyan]")
                else:
                    prompt = input("\n> ")

                prompt_lower = prompt.lower().strip()

                # Handle commands
                if prompt_lower in ['exit', 'quit', 'q']:
                    if stats.total_checks > 0:
                        print_session_stats(stats)
                    if RICH_AVAILABLE:
                        console.print("[bold green]Stay safe![/bold green]\n")
                    else:
                        print("\nExiting...")
                    break

                if prompt_lower in ['help', 'h', '?']:
                    print_interactive_help()
                    continue

                if prompt_lower in ['stats', 's']:
                    print_session_stats(stats)
                    continue

                if prompt_lower in ['clear', 'c']:
                    console.clear() if RICH_AVAILABLE else os.system('clear' if os.name == 'posix' else 'cls')
                    continue

                if prompt_lower == 'verbose':
                    verbose_mode = not verbose_mode
                    status = "[green]enabled[/green]" if verbose_mode else "[red]disabled[/red]"
                    if RICH_AVAILABLE:
                        console.print(f"Verbose mode {status}")
                    else:
                        print(f"Verbose mode {'enabled' if verbose_mode else 'disabled'}")
                    continue

                if prompt_lower.startswith('threshold '):
                    try:
                        new_threshold = float(prompt_lower.split()[1])
                        if 0.0 <= new_threshold <= 1.0:
                            current_threshold = new_threshold
                            # Update pipeline config
                            config = DetectorConfig(
                                suspicion_threshold=current_threshold,
                                verbose=verbose_mode
                            )
                            pipeline = PromptInjectionPipeline(config)
                            if RICH_AVAILABLE:
                                console.print(f"Threshold set to [cyan]{current_threshold}[/cyan]")
                            else:
                                print(f"Threshold set to {current_threshold}")
                        else:
                            if RICH_AVAILABLE:
                                console.print("[red]Threshold must be between 0.0 and 1.0[/red]")
                            else:
                                print("Threshold must be between 0.0 and 1.0")
                    except (ValueError, IndexError):
                        if RICH_AVAILABLE:
                            console.print("[red]Usage:[/red] threshold <0.0-1.0>")
                        else:
                            print("Usage: threshold <0.0-1.0>")
                    continue

                if prompt_lower == 'history':
                    if not history:
                        if RICH_AVAILABLE:
                            console.print("[dim]No history yet[/dim]")
                        else:
                            print("No history yet")
                    else:
                        if RICH_AVAILABLE:
                            hist_table = Table(title="[bold]Recent Checks[/bold]", box=box.ROUNDED)
                            hist_table.add_column("#", style="dim", width=4)
                            hist_table.add_column("Prompt", style="white", max_width=40)
                            hist_table.add_column("Status", style="white", width=10)
                            hist_table.add_column("Risk", style="white", width=10)

                            for i, (p, allowed, risk) in enumerate(history[-10:], 1):
                                status = "[green]Safe[/green]" if allowed else "[red]Blocked[/red]"
                                risk_styled = style_risk_level(risk)
                                hist_table.add_row(str(i), p[:40] + ("..." if len(p) > 40 else ""), status, risk_styled)
                            console.print(hist_table)
                        else:
                            print("\nRecent Checks:")
                            for i, (p, allowed, risk) in enumerate(history[-10:], 1):
                                status = "Safe" if allowed else "Blocked"
                                print(f"  {i}. {p[:40]}... - {status} ({risk})")
                    continue

                if not prompt.strip():
                    continue

                # Check the prompt
                response = process_prompt(pipeline, prompt, args.json)
                result = response["result"]

                # Update stats
                stats.add_result(response["allowed"], result.risk_level)
                history.append((prompt, response["allowed"], result.risk_level))

                # Display result
                if args.json:
                    output = {
                        "prompt": prompt,
                        "allowed": response["allowed"],
                        "is_injection": result.is_injection,
                        "confidence_score": result.confidence_score,
                        "risk_level": result.risk_level,
                        "explanation": result.explanation,
                        "detected_patterns": result.detected_patterns if verbose_mode else None,
                    }
                    print(json.dumps(output, indent=2))
                elif RICH_AVAILABLE:
                    display_rich_result(response, result, prompt, verbose_mode, compact=True)
                else:
                    display_simple_result(response, result, verbose_mode)

            except EOFError:
                break
    except KeyboardInterrupt:
        if stats.total_checks > 0:
            print_session_stats(stats)
        if RICH_AVAILABLE:
            console.print("\n\n[bold green]Stay safe![/bold green]\n")
        else:
            print("\n\nExiting...")
        return EXIT_SUCCESS

    return EXIT_SUCCESS


def style_risk_level(risk_level: str) -> str:
    """Return styled risk level string"""
    styles = {
        "low": "[green]Low[/green]",
        "medium": "[yellow]Medium[/yellow]",
        "high": "[#ff8800]High[/#ff8800]",
        "critical": "[red]Critical[/red]"
    }
    return styles.get(risk_level, risk_level)


def process_prompt(pipeline, prompt: str, show_progress: bool = True):
    """Process a prompt and return the response"""
    if RICH_AVAILABLE and show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console
        ) as progress:
            progress.add_task(description="Analyzing...", total=None)
            response = pipeline.process(prompt)
    else:
        response = pipeline.process(prompt)
    return response


def check_and_display(pipeline, prompt, json_output=False, verbose=False, quiet=False, compact=False) -> int:
    """Check a prompt and display the results with beautiful formatting"""
    response = process_prompt(pipeline, prompt, not json_output and not quiet)
    result = response["result"]

    if quiet:
        return EXIT_SUCCESS if response["allowed"] else EXIT_INJECTION_DETECTED

    if json_output:
        output = {
            "prompt": prompt,
            "allowed": response["allowed"],
            "is_injection": result.is_injection,
            "confidence_score": result.confidence_score,
            "risk_level": result.risk_level,
            "explanation": result.explanation,
            "detected_patterns": result.detected_patterns if verbose else None,
        }
        print(json.dumps(output, indent=2))
        return EXIT_SUCCESS if response["allowed"] else EXIT_INJECTION_DETECTED

    # Rich formatted output
    if RICH_AVAILABLE:
        display_rich_result(response, result, prompt, verbose, compact)
    else:
        display_simple_result(response, result, verbose)

    return EXIT_SUCCESS if response["allowed"] else EXIT_INJECTION_DETECTED


def display_rich_result(response, result, prompt, verbose, compact=False):
    """Display results using Rich library with beautiful formatting"""

    # Determine colors and icons based on risk level
    if response["allowed"]:
        status_color = "green"
        status_icon = "✓"
        status_text = "SAFE"
        border_style = "green"
    else:
        if result.risk_level == "critical":
            status_color = "red"
            border_style = "red"
        elif result.risk_level == "high":
            status_color = "#ff8800"
            border_style = "#ff8800"
        elif result.risk_level == "medium":
            status_color = "yellow"
            border_style = "yellow"
        else:
            status_color = "yellow"
            border_style = "yellow"

        status_icon = "✗"
        status_text = "BLOCKED"

    # Risk level emoji
    risk_emoji = {
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "critical": "🔴"
    }.get(result.risk_level, "⚪")

    if compact:
        # Compact one-line result for interactive mode
        confidence_percent = int(result.confidence_score * 100)
        console.print(
            f"  [{status_color}]{status_icon} {status_text}[/{status_color}] | "
            f"{risk_emoji} {result.risk_level.upper()} | "
            f"Confidence: {confidence_percent}% | "
            f"[italic dim]{result.explanation[:50]}{'...' if len(result.explanation) > 50 else ''}[/italic dim]"
        )
        return

    # Full result display
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    # Status row
    table.add_row(
        "Status:",
        f"[bold {status_color}]{status_icon} {status_text}[/bold {status_color}]"
    )

    # Risk level row
    table.add_row(
        "Risk Level:",
        f"{risk_emoji} [bold]{result.risk_level.upper()}[/bold]"
    )

    # Confidence score with progress bar
    confidence_percent = int(result.confidence_score * 100)
    confidence_bar = "█" * (confidence_percent // 5) + "░" * (20 - confidence_percent // 5)
    table.add_row(
        "Confidence:",
        f"[{status_color}]{confidence_bar}[/{status_color}] {result.confidence_score:.1%}"
    )

    # Explanation
    table.add_row(
        "Explanation:",
        f"[italic]{result.explanation}[/italic]"
    )

    # Create panel with result
    panel = Panel(
        table,
        title=f"[bold]Analysis Result[/bold]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 2)
    )

    console.print()
    console.print(panel)

    # Show detected patterns if verbose
    if verbose and result.detected_patterns:
        console.print()
        patterns_table = Table(
            title="Detected Patterns",
            show_header=True,
            header_style="bold magenta",
            box=box.SIMPLE
        )
        patterns_table.add_column("#", style="dim", width=4)
        patterns_table.add_column("Pattern", style="yellow")

        for i, pattern in enumerate(result.detected_patterns[:5], 1):
            patterns_table.add_row(
                str(i),
                pattern[:70] + ("..." if len(pattern) > 70 else "")
            )

        console.print(patterns_table)

    # Show prompt preview if it was truncated
    if len(prompt) > 100:
        console.print()
        console.print(
            Panel(
                f"[dim]{prompt[:100]}...[/dim]",
                title="[bold]Analyzed Prompt (preview)[/bold]",
                border_style="dim",
                box=box.ROUNDED
            )
        )


def display_simple_result(response, result, verbose):
    """Display results in simple text format (fallback when Rich is not available)"""
    status_icon = "✓" if response["allowed"] else "✗"
    status_text = "SAFE" if response["allowed"] else "BLOCKED"

    print(f"\n{status_icon} Status: {status_text}")
    print(f"  Risk Level: {result.risk_level.upper()}")
    print(f"  Confidence: {result.confidence_score:.1%}")
    print(f"  Explanation: {result.explanation}")

    if verbose and result.detected_patterns:
        print(f"  Detected Patterns:")
        for pattern in result.detected_patterns[:5]:
            print(f"    - {pattern[:60]}...")


if __name__ == "__main__":
    main()
