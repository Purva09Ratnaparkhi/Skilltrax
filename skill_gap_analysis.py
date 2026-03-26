from syllabus_pro import extract_text_with_fitz, extract_from_scanned_pdf
from groq import Groq
import json
import os
import re

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are an expert career coach performing skill gap analysis.

You will receive:
- A job description (text)
- A list of user skills with levels

Rules:
- Ignore any skills where level is "advanced" (case-insensitive).
- Identify skills that user needs to learn (skills with level "beginner" or "intermediate" or not mentioned).
- If the user is not familiar with a skill, consider it as "beginner".
- Focus on skills that are relevant to the job description.
- Give list of subjects that the user should learn to bridge the skill gap for the job.

Output requirements:
Return ONLY valid JSON in this structure:
{
    "subjects": [
        {
            "subject area": "<name of subject>",
            "current knowledge level": "Beginner | Intermediate | Advanced",
           
        }
    ]
}

Rules:
- Output only JSON.
- Use double quotes for all keys and values.
- Do not include any text outside the JSON.
- Do not add trailing commas.
"""


def safe_json_loads(content):
        try:
                return json.loads(content)
        except json.JSONDecodeError:
                content = re.sub(r",(\s*[}\]])", r"\1", content)
                content = content.replace("'", '"')
                try:
                        return json.loads(content)
                except Exception:
                        return {"subjects": []}


def analyze_skill_gap(job_description_path, skills):
    text = extract_text_with_fitz(job_description_path)
    if not text:
        text = extract_from_scanned_pdf(job_description_path)
    return analyze_skill_gap_from_text(text, skills)


def analyze_skill_gap_from_text(job_description_text, skills):
    filtered_skills = [
        skill for skill in skills
        if skill.get("level", "").lower() != "advanced"
    ]

    payload = {
        "job_description": job_description_text,
        "skills": filtered_skills
    }

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)}
        ]
    )

    content = response.choices[0].message.content
    data = safe_json_loads(content)
    for subject in data.get("subjects", []):
        subject["learning goals"] = "Interview Preparation"
        subject["custom requirement"] = "Focus on practical skills and real-world applications relevant to the job description."
    return data.get("subjects", [])


def test_skill_gap_with_pdf(skills, job_description_path=None):
    if job_description_path is None:
        job_description_path = os.path.join(
            "temp",
            "Backend_Intern_JD (1).pdf"
        )
    return analyze_skill_gap(job_description_path, skills)


def main():
    skills_json = os.getenv("SKILLTRAX_SKILLS", "[]")
    try:
        skills = json.loads(skills_json)
    except json.JSONDecodeError:
        print("Invalid SKILLTRAX_SKILLS JSON.")
        return

    job_description_path = os.getenv("JOB_DESC_PATH", "").strip() or None
    subjects = test_skill_gap_with_pdf(skills, job_description_path)
    print(json.dumps(subjects, indent=2))


if __name__ == "__main__":
    main()
        

