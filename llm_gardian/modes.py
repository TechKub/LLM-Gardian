"""
Interactive and batch mode implementations
"""

import os
import sys
import json
from pathlib import Path
from typing import List

from llm_gardian import DetectorConfig, PromptInjectionPipeline
from llm_gardian.stats import SessionStats
from llm_gardian.output import (
    check_and_display,
    process_prompt,
    display_rich_result,
    display_simple_result,
    EXIT_SUCCESS,
    EXIT_INJECTION_DETECTED,
    EXIT_ERROR
)

try:
    from rich.console import Console
    from rich.prompt import Prompt
    from rich.table import Table
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import UI functions
from llm_gardian.ui import (
    console,
    print_banner,
    print_interactive_help,
    print_session_stats,
    style_risk_level
)


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
