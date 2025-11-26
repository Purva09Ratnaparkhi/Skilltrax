import asyncio
from youtube_transcript_api import YouTubeTranscriptApi
import re
from googletrans import Translator

async def yt_transcribe(url):
    video_id = get_video_id(url=url)
    if not video_id:
        print("Invalid YouTube URL")
        return
    try:
    # Get transcript in English or Hindi if available
        fetchedTranscript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
        transcript_list = [item['text'] for item in fetchedTranscript]
        transcript = " ".join(transcript_list)        
        try:
            # Detect language of the first item (assuming all are same)
            language = fetchedTranscript[0].get('language_code', 'unknown')

            if language != "en":
                translator = Translator()
                translated = await translator.translate(transcript, dest='en')
                # print(f"Original language: {language}")
                # print("Translated transcript:")
                return translated.text
            else:
                # print("English transcript:")
                return transcript

        except Exception as e:
            # print(f"Error: {str(e)}")
            return transcript
    except Exception as e:
            print(f"Error: {str(e)}")
            
def get_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
    return match.group(1) if match else None

