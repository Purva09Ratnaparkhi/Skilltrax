import os
import uuid
from typing import Any, Dict, Optional

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError as exc:
    try:
        from langgraph.checkpoint import SqliteSaver
    except ImportError:
        raise ImportError(
            "SqliteSaver is not available. Install langgraph-checkpoint-sqlite."
        ) from exc

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    from langgraph.checkpoint import MemorySaver

from langgraph_ai.graphs import (
    build_quiz_graph,
    build_roadmap_graph,
    build_skill_gap_graph,
    build_syllabus_graph,
)
from langgraph_ai.state import GraphState


_graph_cache: Dict[str, Any] = {}
_checkpointer = None
_checkpointer_cm = None


def _checkpoint_conn_string(path: str) -> str:
    normalized = os.path.abspath(path).replace("\\", "/")
    return f"sqlite:///{normalized}?check_same_thread=false"


def _get_checkpointer():
    global _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    print("✅ Using MemorySaver (SQLite removed to fix DB error)")

    _checkpointer = MemorySaver()
    return _checkpointer


def _get_compiled_graph(key: str, builder) -> Any:
    if key not in _graph_cache:
        checkpointer = _get_checkpointer()
        _graph_cache[key] = builder().compile(checkpointer=checkpointer)
    return _graph_cache[key]


def _invoke_graph(graph_key: str, builder, state: GraphState, thread_id: Optional[str]) -> GraphState:
    graph = _get_compiled_graph(graph_key, builder)
    run_id = thread_id or state.get("run_id") or str(uuid.uuid4())
    state["run_id"] = run_id
    return graph.invoke(state, config={"configurable": {"thread_id": run_id}})


def run_roadmap_graph(
    subject_area: str,
    knowledge_level: str,
    learning_goals,
    custom_requirement: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> GraphState:
    state: GraphState = {
        "subject_area": subject_area,
        "knowledge_level": knowledge_level,
        "learning_goals": learning_goals,
        "custom_requirement": custom_requirement or "",
    }
    return _invoke_graph("roadmap", build_roadmap_graph, state, thread_id)


def run_syllabus_graph(
    syllabus_path: str,
    thread_id: Optional[str] = None,
) -> GraphState:
    state: GraphState = {"syllabus_path": syllabus_path}
    return _invoke_graph("syllabus", build_syllabus_graph, state, thread_id)


def run_skill_gap_graph(
    job_description_path: str,
    skills,
    thread_id: Optional[str] = None,
) -> GraphState:
    state: GraphState = {
        "job_description_path": job_description_path,
        "skills": skills,
    }
    return _invoke_graph("skill_gap", build_skill_gap_graph, state, thread_id)


def run_quiz_graph(video_url: str, thread_id: Optional[str] = None) -> GraphState:
    state: GraphState = {"video_url": video_url}
    return _invoke_graph("quiz", build_quiz_graph, state, thread_id)
