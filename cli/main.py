"""
MCPilot — CLI entrypoint.

Usage:
    mcpilot                          # interactive prompt
    mcpilot "Why is my system slow?" # one-shot
"""

import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from agent.graph import app
from agent.nodes import set_approval_callback

load_dotenv()
console = Console()


def approval_prompt(tool_name: str, arguments: dict) -> bool:
    """
    Human-in-the-loop approval prompt for state-changing operations.
    Only a literal 'y' proceeds. Anything else (including empty) is rejection.
    """
    console.print()
    console.print(Panel.fit(
        f"[bold yellow]⚠ State-changing operation[/]\n\n"
        f"  Tool: [bold]{tool_name}[/]\n"
        + "".join(f"  {k.title()}: [bold]{v}[/]\n" for k, v in arguments.items())
        + "\n  Reason: service action requested by diagnostic agent",
        title="MCPilot requests action",
        border_style="yellow",
    ))
    response = input("  Approve? [y/N] ").strip().lower()
    return response == "y"


def run_diagnosis(query: str) -> None:
    """Run the full diagnostic pipeline for a query."""
    console.print()
    console.print(f"[bold blue]━━━ MCPilot Diagnostic Session ━━━[/]", highlight=False)
    console.print(f"[dim]Query:[/] {query}\n", highlight=False)

    # Set up the approval callback
    set_approval_callback(approval_prompt)

    # Initial state
    initial_state = {
        "query": query,
        "observations": [],
        "tool_calls": [],
        "sufficient": False,
        "missing_information": [],
        "diagnosis": "",
        "evidence": [],
        "confidence": "",
        "iteration": 0,
    }

    # Run the graph
    try:
        final_state = app.invoke(initial_state)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/] {e}", highlight=False)
        return

    # Display the diagnosis
    console.print()
    if final_state.get("diagnosis"):
        console.print(Panel(
            Markdown(final_state["diagnosis"]),
            title="[bold green]Diagnosis[/]",
            border_style="green",
            padding=(1, 2),
        ))
    else:
        console.print("[yellow]No diagnosis generated.[/]", highlight=False)


def main():
    """CLI entrypoint."""
    console.print("[bold blue]🔍 MCPilot[/] — Linux Diagnostic Assistant", highlight=False)
    console.print("[dim]Type your question or 'quit' to exit.[/]\n", highlight=False)

    if len(sys.argv) > 1:
        # One-shot mode
        query = " ".join(sys.argv[1:])
        run_diagnosis(query)
        return

    # Interactive mode
    while True:
        try:
            query = console.input("[bold blue]You:[/] ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye![/]", highlight=False)
                break
            run_diagnosis(query)
            console.print()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/]", highlight=False)
            break


if __name__ == "__main__":
    main()
