from youtube_video_search import search_youtube_lectures
from groq import Groq
import json
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are an expert learning planner that generates structured learning roadmaps for mastering a subject efficiently.

You will receive input in the following format:
{
  "subject area": "<name of subject>",
  "current knowledge level": "<Beginner | Intermediate | Advanced>",
  "learning goals": "<Exam Preparation | Career Development | Personal Interest | Professional Certification>",
  "custom requirement": "<any additional requirements>"
}

Your task is to create a logical and structured roadmap that helps a learner progress from fundamentals to advanced concepts.

Guidelines:
1. Generate topics in a proper learning sequence (beginner → advanced).
2. Ensure each topic builds upon the previous one.
3. Adjust topic depth based on the user's knowledge level and learning goals.
4. Keep descriptions concise but informative.
5. Do not include topics unrelated to the subject.
6. Avoid duplicate or overlapping topics.

Output Requirements:
Return ONLY valid JSON using the following structure:

{
  "subject": "name of the subject",
  "subject_desc": "brief description of the subject and what the learner will achieve",
  "roadmap": [
    {
      "title": "topic title",
      "description": "short explanation of what the learner will study in this topic",
      "level": "Beginner | Intermediate | Advanced"
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

SYLLABUS_SYSTEM_PROMPT = """
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
  "subject": "name of the subject",
  "subject_desc": "brief description of the subject based on syllabus context",
  "roadmap": [
    {
      "title": "topic title",
      "description": "short explanation derived from the syllabus",
      "level": "Beginner | Intermediate | Advanced"
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

def safe_json_loads(content):
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Attempt to fix common JSON issues
        import re
        # Remove trailing commas
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        # Replace single quotes with double quotes
        content = content.replace("'", '"')
        try:
            return json.loads(content)
        except Exception as e:
            # Optionally, log or return a default error structure
            return {"error": "Invalid JSON from model", "raw_content": content}

def roadmap_gen(prompt):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content

    return safe_json_loads(content)

def roadmap_gen_pro(syllabus):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYLLABUS_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": syllabus
            }
        ]
    )
    
    content = response.choices[0].message.content
    return safe_json_loads(content)