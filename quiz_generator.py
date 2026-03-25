from youtube_transcriber import yt_transcribe
from groq import Groq
import json
import asyncio
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """
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

async def generate_quiz(url):
    
    transcript = await yt_transcribe(url)

    if not transcript:
        return {"error": "Transcript not available"}

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript}
        ]
    )

    output = response.choices[0].message.content

    print(output)

    try:
        jresponse = json.loads(output)
    except:
        return False

    return jresponse


# Example
# text = asyncio.run(generate_quiz("https://youtu.be/YmKmS9bpMqM"))
# print(text)