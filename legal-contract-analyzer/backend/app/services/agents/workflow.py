from langgraph.graph import StateGraph, START, END
from app.services.agents.state import ContractAuditState
from app.services.agents.nodes.triage import triage_node
from app.services.agents.nodes.retriever import retriever_node
from app.services.agents.nodes.extractor import extractor_node
from app.services.agents.nodes.verifier import verifier_node
from app.services.agents.nodes.redline import redline_node
import logging

logger = logging.getLogger(__name__)

def build_audit_graph():
    """
    Constructs the LangGraph stateful audit pipeline for contract analysis.
    """
    workflow = StateGraph(ContractAuditState)

    # Add Nodes
    workflow.add_node("triage", triage_node)
    workflow.add_node("retriever", retriever_node)
    workflow.add_node("extractor", extractor_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("redline", redline_node)

    # Add Edges
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "retriever")
    workflow.add_edge("retriever", "extractor")
    workflow.add_edge("extractor", "verifier")
    workflow.add_edge("verifier", "redline")
    workflow.add_edge("redline", END)

    app = workflow.compile()
    logger.info("LangGraph Contract Audit Workflow compiled successfully.")
    return app

audit_graph = build_audit_graph()

