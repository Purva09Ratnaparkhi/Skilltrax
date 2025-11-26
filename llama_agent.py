from youtube_video_search import search_youtube_lectures
from ollama import ChatResponse, Client
import json

client = Client("http://localhost:11434")

def roadmap_gen(prompt):
    response = client.chat(
        model='skilltraxx_model', 
        messages=[{'role': 'user', 'content': prompt}], 
        stream=False
    )

    # for response in response_stream:
    #     print(response['message']['content'], end='', flush=True) 
    return json.loads(response['message']['content'])

def roadmap_gen_pro(syllabus):
    response = client.chat(
        model='syllabus_pro', 
        messages=[{'role': 'user', 'content': syllabus}], 
        stream=False
    )

    # for response in response_stream:
    #     print(response['message']['content'], end='', flush=True) 
    return json.loads(response['message']['content'])
        
