from typing import Any, Dict, List, Optional, TypedDict


class RoadmapStepDict(TypedDict, total=False):
    title: str
    description: str
    level: str
    res_link: str
    resource_link_webs: List[str]


class GraphState(TypedDict, total=False):
    # Core inputs
    subject_area: str
    knowledge_level: str
    learning_goals: List[str]
    custom_requirement: str

    # Syllabus / job description inputs
    syllabus_path: str
    syllabus_text: str
    job_description_path: str
    job_description_text: str
    job_role: str
    skills: List[Dict[str, Any]]

    # Quiz inputs
    video_url: str
    transcript: str

    # Outputs
    roadmap_response: Dict[str, Any]
    quiz_response: Dict[str, Any]
    skill_gap_response: Dict[str, Any]

    # Error reporting
    error: str
    errors: List[str]
    warnings: List[str]

    # Metadata
    run_id: str
