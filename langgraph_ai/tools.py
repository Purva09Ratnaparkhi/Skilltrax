import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from groq import Groq

from article_search import search_for_articles
from syllabus_pro import extract_from_scanned_pdf, extract_text_with_fitz
from youtube_transcriber import yt_transcribe
from youtube_video_search import search_youtube_lectures

SYSTEM_PROMPT_ROADMAP = """
You are an expert learning planner that generates structured learning roadmaps for mastering a subject efficiently.

You will receive input in the following format:
{
  \"subject area\": \"<name of subject>\",
  \"current knowledge level\": \"<Beginner | Intermediate | Advanced>\",
  \"learning goals\": \"<Exam Preparation | Career Development | Personal Interest | Professional Certification>\",
  \"custom requirenment\": \"<any additional requirements>\"
}

Your task is to create a logical and structured roadmap that helps a learner progress from fundamentals to advanced concepts.

Guidelines:
1. Generate topics in a proper learning sequence (beginner -> advanced).
2. Ensure each topic builds upon the previous one.
3. Adjust topic depth based on the user's knowledge level and learning goals.
4. Keep descriptions concise but informative.
5. Do not include topics unrelated to the subject.
6. Avoid duplicate or overlapping topics.

Output Requirements:
Return ONLY valid JSON using the following structure:

{
  \"subject\": \"name of the subject\",
  \"subject_desc\": \"brief description of the subject and what the learner will achieve\",
  \"roadmap\": [
    {
      \"title\": \"topic title\",
      \"description\": \"short explanation of what the learner will study in this topic\",
      \"level\": \"Beginner | Intermediate | Advanced\"
    }
  ]
}

Rules:
- The roadmap must contain topics arranged in correct learning order.
- Ensure the output is strictly valid JSON.
- Use double quotes for all keys and strings.
- Do not include any explanation, markdown, or text outside the JSON.
- Do not add trailing commas.
"""

SYSTEM_PROMPT_SYLLABUS = """
You are an expert academic curriculum planner.

You will receive syllabus content as plain text.

Your task is to convert the syllabus into a structured learning roadmap while preserving the topics and order defined in the syllabus.

Guidelines:
1. Carefully analyze the syllabus content.
2. Extract the main topics and convert them into roadmap chapters.
3. If a syllabus topic contains multiple sub-topics, split them into separate roadmap entries.
4. Maintain the logical sequence defined in the syllabus.
5. Do NOT add topics that are not present in the syllabus.
6. Keep descriptions concise and aligned with the syllabus.

Output Requirements:
Return ONLY valid JSON using the following structure:

{
  \"subject\": \"name of the subject\",
  \"subject_desc\": \"brief description of the subject based on syllabus context\",
  \"roadmap\": [
    {
      \"title\": \"topic title\",
      \"description\": \"short explanation derived from the syllabus\",
      \"level\": \"Beginner | Intermediate | Advanced\"
    }
  ]
}

Rules:
- Follow the order of the syllabus topics.
- If subtopics exist, convert them into individual roadmap items.
- Ensure the output is strictly valid JSON.
- Use double quotes for all keys and values.
- Do not include any text before or after the JSON.
- Do not add trailing commas.
"""

SYSTEM_PROMPT_QUIZ = """
You are a system that generates multiple choice quiz based on transcript of educational video provided to you.
Don't add anything extra other than that in transcript, but make sure all the points in transcript are covered.
If the transcript is in any other language, then first translate it into English.
Generate exactly 10 questions in following json format:
{
  quiz: [
    { question: <only question>, options: [ <option1>, <option2>, <option3>, <option4> ], correct_ans: <actual correct answer> },
    { question: <only question>, options: [ <option1>, <option2>, <option3>, <option4> ], correct_ans: <actual correct answer> }
  ]
}
Don't make changes in given output format, don't add any header or footer please give only json.
"""

SYSTEM_PROMPT_SKILL_GAP = """
You are an expert career coach performing skill gap analysis.

You will receive:
- A job description (text)
- A list of user skills with levels

Rules:
- Ignore any skills where level is \"advanced\" (case-insensitive).
- Identify skills that user needs to learn (skills with level \"beginner\" or \"intermediate\" or not mentioned).
- If the user is not familiar with a skill, consider it as \"beginner\".
- Focus on skills that are relevant to the job description.
- Give list of subjects that the user should learn to bridge the skill gap for the job.

Output requirements:
Return ONLY valid JSON in this structure:
{
    \"job role\": \"<name of the job role>\",
    \"subjects\": [
        {
            \"subject area\": \"<name of subject>\",
            \"current knowledge level\": \"Beginner | Intermediate | Advanced\"
        }
    ]
}

Rules:
- Output only JSON.
- Use double quotes for all keys and values.
- Do not include any text outside the JSON.
- Do not add trailing commas.
"""

SYSTEM_PROMPT_INTERVIEW_QUESTION = """
You are an interview coach generating one adaptive interview question at a time.

You will receive JSON with:
- profile: projects, experience (no skills)
- roadmap_topics: roadmap titles and subtopic titles only (no description/level)
- history: previous questions and answer scores
- last_answer: last answer text (may be empty for the first question)
- last_score: last answer score (0-100 or null)
- question_order: 1-based index of the next question to generate
- current_focus: one of general|roadmap|project|experience
- question_plan: question distribution counts
- generation_guidance (optional):
    - last_score_low
    - repeated_low_same_focus
    - prefer_new_topic
    - avoid_question_texts
    - target_difficulty
    - force_topic_switch

Generate ONE next question to evaluate the user.

Sequence rules you MUST follow:
1) Question 1 is general introduction.
2) Questions 2 to 6 or 7 are roadmap-focused.
3) Next 2 questions are project-focused.
4) Final 1 question is experience-focused.

Use current_focus and question_order strictly. Adapt the depth based on last_score:
- high score: ask deeper follow-up
- low score: ask simpler clarification

Important behavior rules:
- Do not repeat or paraphrase questions from avoid_question_texts.
- If prefer_new_topic is true, switch to a different topic within current_focus.
- If repeated_low_same_focus or force_topic_switch is true, do not ask same-topic follow-up; ask a new topic with lower difficulty.
- Prefer difficulty that matches target_difficulty when provided.

Output ONLY valid JSON in this structure:
{
    "question": "...",
    "difficulty": "easy|medium|hard",
    "focus": "general|roadmap|project|experience",
    "rubric": ["point1", "point2", "point3"]
}

Rules:
- Return only JSON.
- Use double quotes for keys and strings.
- Do not add any text outside JSON.
"""

SYSTEM_PROMPT_INTERVIEW_GRADE = """
You are an interview evaluator. Grade the answer using the provided rubric.

You will receive JSON with:
- question
- rubric (list of expected points)
- answer_text

Return ONLY valid JSON with:
{
    "score": 0-100,
    "feedback": "short feedback",
    "key_points_covered": ["..."],
    "missing_points": ["..."]
}

Rules:
- Be strict but fair.
- Return only JSON.
- Use double quotes for keys and strings.
"""


def safe_json_loads(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        content = re.sub(r",(\s*[}\]])", r"\1", content)
        content = content.replace("'", '"')
        try:
            return json.loads(content)
        except Exception:
            return {"error": "Invalid JSON from model", "raw_content": content}


def _get_groq_client() -> Optional[Groq]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def groq_chat_json(system_prompt: str, user_content: str, temperature: float) -> Dict[str, Any]:
    client = _get_groq_client()
    if not client:
        return {"error": "GROQ_API_KEY is not configured"}

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )

    content = response.choices[0].message.content
    return safe_json_loads(content)


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def enrich_resources(subject: str, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for step in steps:
        try:
            res_link = search_youtube_lectures(
                subject=subject,
                topic=step.get("title", ""),
                description=step.get("description", "")
            )[0]["url"]
        except Exception:
            res_link = "link not found"

        try:
            article_query = f"{subject} {step.get('title', '')}".strip()
            article_results = search_for_articles(article_query)
            article_links = [item.get("href") for item in article_results if item.get("href")]
        except Exception:
            article_links = []

        step["res_link"] = res_link
        step["resource_link_webs"] = article_links

    return steps


def extract_pdf_text(pdf_path: str) -> str:
    text = extract_text_with_fitz(pdf_path)
    if text:
        return text
    return extract_from_scanned_pdf(pdf_path)


def transcribe_video(video_url: str) -> Optional[str]:
    return run_async(yt_transcribe(video_url))

