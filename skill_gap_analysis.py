from syllabus_pro import extract_text_with_fitz, extract_from_scanned_pdf

def analyze_skill_gap(syllabus_path, current_skills):
    text = extract_text_with_fitz(syllabus_path)
    if not text:
        text = extract_from_scanned_pdf(syllabus_path)
        

    required_skills = set()
    
    