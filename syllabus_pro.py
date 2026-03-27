import fitz  
import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from llama_agent import roadmap_gen_pro 
from youtube_video_search import search_youtube_lectures
from article_search import search_for_articles

pytesseract.pytesseract.tesseract_cmd = r'E:/Softwares/Tesseract-OCR/tesseract.exe'


def extract_from_scanned_pdf(pdf_path):
    pages = convert_from_path(pdf_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)
    return text

def extract_text_with_fitz(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return full_text

def generator_pro(pdf_path):
    text = extract_text_with_fitz(pdf_path)
    if text:
        response = roadmap_gen_pro(text)
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
    else:
        text = extract_from_scanned_pdf(pdf_path)
        if text:
            response = roadmap_gen_pro(text)
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
        else:
            print("Cannot extract data")
        