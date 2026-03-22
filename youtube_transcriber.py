# import asyncio
# from youtube_transcript_api import YouTubeTranscriptApi
# import re
# from googletrans import Translator

# async def yt_transcribe(url):
#     video_id = get_video_id(url=url)
#     if not video_id:
#         print("Invalid YouTube URL")
#         return
#     try:
#     # Get transcript in English or Hindi if available
#         fetchedTranscript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
#         transcript_list = [item['text'] for item in fetchedTranscript]
#         transcript = " ".join(transcript_list)        
#         try:
#             # Detect language of the first item (assuming all are same)
#             language = fetchedTranscript[0].get('language_code', 'unknown')

#             if language != "en":
#                 translator = Translator()
#                 translated = await translator.translate(transcript, dest='en')
#                 # print(f"Original language: {language}")
#                 # print("Translated transcript:")
#                 return translated.text
#             else:
#                 # print("English transcript:")
#                 return transcript

#         except Exception as e:
#             # print(f"Error: {str(e)}")
#             return transcript
#     except Exception as e:
#             print(f"Error: {str(e)}")
            
# def get_video_id(url):
#     match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
#     return match.group(1) if match else None

# if __name__ == "__main__":
#     result = asyncio.run(
#         yt_transcribe("https://youtu.be/UqiPDGkOSbE?si=jbFaKjH5GmmY8k6c")
#     )
#     print(result)

import asyncio
import serpapi
import re
from googletrans import Translator
import os

API_KEY = os.environ.get("SERP_API_KEY")

def get_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

async def yt_transcribe(url):
    video_id = get_video_id(url)
    if not video_id:
        print("Invalid YouTube URL")
        return

    try:
        client = serpapi.Client(api_key=API_KEY)

        results = client.search({
            "engine": "youtube_video_transcript",
            "v": video_id,
            "type": "asr"
        })

        results_dict = results.as_dict()

        # ✅ Extract transcript snippets
        transcript_data = results_dict.get("transcript", [])
        transcript_list = [item.get("snippet", "") for item in transcript_data]

        transcript = " ".join(transcript_list).strip()

        if not transcript:
            print("No transcript found")
            return

        try:
            # SerpAPI already gives language_code sometimes
            language = results_dict.get("search_parameters", {}).get("language_code", "unknown")

            if language != "en":
                translator = Translator()
                translated = await translator.translate(transcript, dest='en')
                return translated.text
            else:
                return transcript

        except Exception as e:
            print(f"Translation error: {str(e)}")
            return transcript

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    result = asyncio.run(
        yt_transcribe("https://youtu.be/Gk8gB5VACZw")
    )
    print(result)