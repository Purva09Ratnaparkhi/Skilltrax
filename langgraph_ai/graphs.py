from langgraph.graph import END, StateGraph

from langgraph_ai.nodes import (
    node_analyze_skill_gap,
    node_enrich_roadmap_resources,
    node_extract_job_description_text,
    node_extract_syllabus_text,
    node_generate_quiz,
    node_generate_roadmap,
    node_generate_roadmap_from_syllabus,
    node_transcribe_video,
)
from langgraph_ai.state import GraphState


def build_roadmap_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("generate_roadmap", node_generate_roadmap)
    graph.add_node("enrich_resources", node_enrich_roadmap_resources)

    graph.set_entry_point("generate_roadmap")
    graph.add_edge("generate_roadmap", "enrich_resources")
    graph.add_edge("enrich_resources", END)
    return graph


def build_syllabus_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("extract_syllabus", node_extract_syllabus_text)
    graph.add_node("generate_roadmap", node_generate_roadmap_from_syllabus)
    graph.add_node("enrich_resources", node_enrich_roadmap_resources)

    graph.set_entry_point("extract_syllabus")
    graph.add_edge("extract_syllabus", "generate_roadmap")
    graph.add_edge("generate_roadmap", "enrich_resources")
    graph.add_edge("enrich_resources", END)
    return graph


def build_skill_gap_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("extract_job_description", node_extract_job_description_text)
    graph.add_node("analyze_skill_gap", node_analyze_skill_gap)

    graph.set_entry_point("extract_job_description")
    graph.add_edge("extract_job_description", "analyze_skill_gap")
    graph.add_edge("analyze_skill_gap", END)
    return graph


def build_quiz_graph() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("transcribe", node_transcribe_video)
    graph.add_node("generate_quiz", node_generate_quiz)

    graph.set_entry_point("transcribe")
    graph.add_edge("transcribe", "generate_quiz")
    graph.add_edge("generate_quiz", END)
    return graph
