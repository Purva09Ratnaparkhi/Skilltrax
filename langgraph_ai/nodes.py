import json
from typing import Any, Dict, List

from langgraph_ai.state import GraphState
from langgraph_ai.tools import (
    SYSTEM_PROMPT_QUIZ,
    SYSTEM_PROMPT_ROADMAP,
    SYSTEM_PROMPT_SKILL_GAP,
    SYSTEM_PROMPT_SYLLABUS,
    enrich_resources,
    extract_pdf_text,
    groq_chat_json,
    transcribe_video,
)


def _append_error(state: GraphState, message: str) -> GraphState:
    errors = state.get("errors", [])
    errors.append(message)
    return {"errors": errors, "error": message}


def node_generate_roadmap(state: GraphState) -> GraphState:
    subject = state.get("subject_area")
    level = state.get("knowledge_level")
    goals = state.get("learning_goals")
    custom_requirement = state.get("custom_requirement")

    if not subject or not level:
        return _append_error(state, "Missing subject_area or knowledge_level")

    payload = {
        "subject area": subject,
        "current knowledge level": level,
        "learning goals": goals,
        "custom requirenment": custom_requirement
    }

    response = groq_chat_json(
        system_prompt=SYSTEM_PROMPT_ROADMAP,
        user_content=json.dumps(payload),
        temperature=0.5
    )

    if response.get("error"):
        return _append_error(state, response["error"])

    return {"roadmap_response": response}


def node_generate_roadmap_from_syllabus(state: GraphState) -> GraphState:
    syllabus_text = state.get("syllabus_text")
    if not syllabus_text:
        return _append_error(state, "Missing syllabus_text")

    response = groq_chat_json(
        system_prompt=SYSTEM_PROMPT_SYLLABUS,
        user_content=syllabus_text,
        temperature=0.5
    )

    if response.get("error"):
        return _append_error(state, response["error"])

    return {"roadmap_response": response}


def node_enrich_roadmap_resources(state: GraphState) -> GraphState:
    roadmap_response = state.get("roadmap_response")
    if not roadmap_response:
        return _append_error(state, "Roadmap response missing")

    subject = roadmap_response.get("subject", state.get("subject_area", ""))
    steps = roadmap_response.get("roadmap", [])
    if not steps:
        return _append_error(state, "Roadmap steps missing")

    roadmap_response["roadmap"] = enrich_resources(subject, steps)
    return {"roadmap_response": roadmap_response}


def node_extract_syllabus_text(state: GraphState) -> GraphState:
    if state.get("syllabus_text"):
        return {}

    syllabus_path = state.get("syllabus_path")
    if not syllabus_path:
        return _append_error(state, "Missing syllabus_path")

    text = extract_pdf_text(syllabus_path)
    if not text:
        return _append_error(state, "Failed to extract syllabus text")

    return {"syllabus_text": text}


def node_extract_job_description_text(state: GraphState) -> GraphState:
    if state.get("job_description_text"):
        return {}

    job_path = state.get("job_description_path")
    if not job_path:
        return _append_error(state, "Missing job_description_path")

    text = extract_pdf_text(job_path)
    if not text:
        return _append_error(state, "Failed to extract job description text")

    return {"job_description_text": text}


def node_analyze_skill_gap(state: GraphState) -> GraphState:
    job_text = state.get("job_description_text")
    skills = state.get("skills", [])

    if not job_text:
        return _append_error(state, "Missing job_description_text")

    filtered_skills = [
        skill for skill in skills
        if skill.get("level", "").lower() != "advanced"
    ]

    payload = {
        "job_description": job_text,
        "skills": filtered_skills
    }

    response = groq_chat_json(
        system_prompt=SYSTEM_PROMPT_SKILL_GAP,
        user_content=json.dumps(payload),
        temperature=0.3
    )

    if response.get("error"):
        return _append_error(state, response["error"])

    subjects = response.get("subjects", [])
    for subject in subjects:
        subject["learning goals"] = "Interview Preparation"
        subject["custom requirement"] = (
            "Focus on practical skills and real-world applications relevant to the job description."
        )

    return {"skill_gap_response": {"subjects": subjects}}


def node_transcribe_video(state: GraphState) -> GraphState:
    video_url = state.get("video_url")
    if not video_url:
        return _append_error(state, "Missing video_url")

    transcript = transcribe_video(video_url)
    if not transcript:
        return _append_error(state, "Transcript not available")

    return {"transcript": transcript}


def node_generate_quiz(state: GraphState) -> GraphState:
    transcript = state.get("transcript")
    if not transcript:
        return _append_error(state, "Missing transcript")

    response = groq_chat_json(
        system_prompt=SYSTEM_PROMPT_QUIZ,
        user_content=transcript,
        temperature=0.5
    )

    if response.get("error"):
        return _append_error(state, response["error"])

    return {"quiz_response": response}
