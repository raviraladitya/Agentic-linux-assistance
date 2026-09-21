"""
MCPilot — LangGraph diagnostic agent graph.

State machine:
START → analyze_request → execute_tools → evaluate_evidence ─┬─ insufficient → analyze_request
                                                              └─ sufficient  → generate_diagnosis → END
"""

from langgraph.graph import StateGraph, END
from agent.state import DiagnosticState
from agent.nodes import analyze_request, execute_tools, evaluate_evidence, generate_diagnosis


def build_graph() -> StateGraph:
    """Build and compile the diagnostic LangGraph."""
    graph = StateGraph(DiagnosticState)

    graph.add_node("analyze_request", analyze_request)
    graph.add_node("execute_tools", execute_tools)
    graph.add_node("evaluate_evidence", evaluate_evidence)
    graph.add_node("generate_diagnosis", generate_diagnosis)

    graph.set_entry_point("analyze_request")
    graph.add_edge("analyze_request", "execute_tools")
    graph.add_edge("execute_tools", "evaluate_evidence")
    graph.add_conditional_edges(
        "evaluate_evidence",
        lambda state: "generate_diagnosis" if state.get("sufficient", False) else "analyze_request",
    )
    graph.add_edge("generate_diagnosis", END)

    return graph.compile()


# Pre-compiled app for import
app = build_graph()
