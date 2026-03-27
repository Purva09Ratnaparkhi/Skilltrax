import googleapiclient.discovery
import os
from dotenv import load_dotenv

load_dotenv()
_api_key_index = 0

def search_youtube_lectures(subject, topic, description, language="en", max_results=1):
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
    global _api_key_index

    api_keys = [
        os.environ.get("YOUTUBE_API_KEY"),
        os.environ.get("YOUTUBE_API_KEY1"),
        os.environ.get("YOUTUBE_API_KEY2"),
    ]
    available_keys = [key for key in api_keys if key]

    if not available_keys:
        print("No YouTube API keys configured.")
        return []

    # Rotate starting key across calls, then try remaining keys as fallback.
    start_index = _api_key_index % len(available_keys)
    _api_key_index = (_api_key_index + 1) % len(available_keys)
    rotated_keys = available_keys[start_index:] + available_keys[:start_index]

    search_query = f"{subject} {topic} lecture {description} in english"
    last_error = None

    for api_key in rotated_keys:
        try:
            youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

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
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    print(f"All YouTube API keys failed. Last error: {last_error}")
    return []
