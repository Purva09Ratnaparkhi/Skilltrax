from youtube_transcriber import yt_transcribe
from ollama import ChatResponse, Client
import json
import asyncio

client = Client("http://localhost:11434")

async def generate_quiz(url):
    transcript = await yt_transcribe(url=url)
    response = client.chat(
        model='quiz_generator', 
        messages=[{'role': 'user', 'content': transcript}], 
        stream=False
    )
    print(response['message']['content'])
    try:
        jresponse =  json.loads(response['message']['content'])
    except:
        return False
    return jresponse
    # for response in response_stream:
    #     print(response['message']['content'], end='', flush=True) 
    # return json.loads(response['message']['content'])

# text = asyncio.run(generate_quiz("https://youtu.be/YmKmS9bpMqM?si=D94UYeYS4BbT57sA"))
# print(text)