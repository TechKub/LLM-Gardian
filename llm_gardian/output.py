"""
Output formatting and display functions
"""

import json

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None

# Exit codes for scripting
EXIT_SUCCESS = 0
EXIT_INJECTION_DETECTED = 1
EXIT_ERROR = 2


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
