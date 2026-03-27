from llama_agent import roadmap_gen
from youtube_video_search import search_youtube_lectures
from article_search import search_for_articles
from pprint import pprint

def gen_roadmap(subject_area, knowledge_level, learning_goals, custom_requirement):
    prompt = f"{{ subject area: {subject_area}, current knowledge level: {knowledge_level}, learning goals: {learning_goals}, custom requirement: {custom_requirement} }}"

    response = roadmap_gen(prompt=prompt)

    for i in range(len(response['roadmap'])):
        try:
            res_link = search_youtube_lectures(subject= response['subject'],topic=response['roadmap'][i]['title'],description=response['roadmap'][i]['description'])[0]['url']
        except Exception:
            res_link = "link not found"

        try:
            article_query = f"{response['subject']} {response['roadmap'][i]['title']}"
            article_results = search_for_articles(article_query)
            article_links = [item.get('href') for item in article_results if item.get('href')]
        except Exception:
            article_links = []
        
        response['roadmap'][i]['res_link'] = res_link
        response['roadmap'][i]['resource_link_webs'] = article_links
        
    return response