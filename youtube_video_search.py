import googleapiclient.discovery
import os
from dotenv import load_dotenv

load_dotenv()

def search_youtube_lectures(subject, topic, description, language="en", max_results=5):
    """
    Searches YouTube for lecture videos related to a given topic and description,
    prioritizing relevance (best match).

    Args:
        topic (str): The topic to search for.
        description (str): A description of the topic (for refining search).
        language (str): The language code (e.g., "en" for English, "es" for Spanish).
        max_results (int): The maximum number of results to return.

    Returns:
        list: A list of dictionaries, where each dictionary contains information
              about a YouTube video. Returns an empty list if no results are found
              or if there's an error.
    """
    API_KEY = os.environ.get("YOUTUBE_API_KEY")
    try:
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=API_KEY)

        search_query = f"{subject} {topic} lecture {description} in english"

        request = youtube.search().list(
            part="snippet",
            maxResults=max_results,
            q=search_query,
            type="video",
            videoDefinition="high",
            videoDuration="medium",
            relevanceLanguage=language,
            order="relevance"
        )
        response = request.execute()

        results = []
        for item in response.get("items", []):
            if item["id"]["kind"] == "youtube#video":
                video_id = item["id"]["videoId"]
                video_title = item["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                channel_title = item["snippet"]["channelTitle"]
                published_at = item["snippet"]["publishedAt"]

                results.append({
                    "title": video_title,
                    "videoId": video_id,
                    "url": video_url,
                    "channelTitle": channel_title,
                    "publishedAt": published_at
                })

        return results

    except googleapiclient.errors.HttpError as e:
        print(f"An HTTP error occurred: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
