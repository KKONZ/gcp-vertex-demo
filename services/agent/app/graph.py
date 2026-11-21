from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.nodes.decide import decide
from app.nodes.draft import draft
from app.nodes.retrieval import retrieve


class AssessmentState(TypedDict):
    user_id: int
    persona_summary: str
    category: str
    message: str
    category_stats: dict
    retrieved_docs: list
    draft: str
    decision: dict


def build_graph():
    graph = StateGraph(AssessmentState)
    # Node names must not collide with AssessmentState keys (LangGraph rejects
    # that) -- "draft" is both a state field and the natural node name, so the
    # node is "write_draft" instead.
    graph.add_node("retrieve", retrieve)
    graph.add_node("write_draft", draft)
    graph.add_node("decide", decide)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "write_draft")
    graph.add_edge("write_draft", "decide")
    graph.add_edge("decide", END)
    return graph.compile()
