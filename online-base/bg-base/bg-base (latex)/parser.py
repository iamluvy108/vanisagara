import os
import re
import json
import glob

# Configuration
INPUT_DIR = "."
OUTPUT_FILE = "chapters.json"

def latex_to_html(text):
    """Surgically converts specific LaTeX macros to clean HTML."""
    if not text: return ""
    
    # 1. Strip structural spacing commands (We will use CSS for this instead)
    text = re.sub(r'\\vspace\{.*?\}', '', text)
    text = re.sub(r'\\hspace\*?\{.*?\}', '', text)
    text = text.replace('\\noindent', '').replace('\\devanagari\\setstretch{0.85}', '')
    
    # 2. Handle the Centered Sanskrit Quotes in the Purports
    # Converts {\centering ... \par} into a styled HTML div
    text = re.sub(r'\{\\centering(.*?)\\par\}', r'<div class="quote-block">\1</div>', text, flags=re.DOTALL)
    text = re.sub(r'\{\\centering(.*?)\}', r'<div class="quote-block">\1</div>', text, flags=re.DOTALL)
    
    # 3. Handle the double-nested bolding in Translations
    text = text.replace('\\textbf{\\textbf{', '<strong>').replace('}}', '</strong>')
    
    # 4. Standard Bold and Italics (Loops to catch any remaining basic nesting)
    for _ in range(3):
        text = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', text)
        text = re.sub(r'\\textit\{([^{}]+)\}', r'<em>\1</em>', text)
        
    # 5. Convert line breaks and paragraphs
    text = re.sub(r'\\\\(?:\*)?\s*', '<br>', text)
    text = text.replace('\\par', '<br>')
    text = text.replace('\n\n', '<br>')
    
    # 6. Clean up trailing/leading breaks and empty tags
    text = re.sub(r'(<br>\s*)+$', '', text)
    text = re.sub(r'^(<br>\s*)+', '', text)
    text = text.replace('<strong></strong>', '').replace('<em></em>', '')
    
    return text.strip()

def parse_chapter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapter_num_match = re.search(r'CHAPTER\s+([A-Z]+)', content)
    chapter_title_match = re.search(r'\\fontsize\{19pt\}\{21pt\}\\selectfont\\textbf\{(.*?)\}', content, re.DOTALL)
    
    chapter_data = {
        "chapter_number": chapter_num_match.group(1) if chapter_num_match else "UNKNOWN",
        "chapter_title": latex_to_html(chapter_title_match.group(1)) if chapter_title_match else "UNKNOWN",
        "verses": []
    }

    verse_blocks = re.split(r'\\texttitle\{TEXTS?\s+([0-9-]+)\}', content)[1:] 
    
    for i in range(0, len(verse_blocks), 2):
        verse_num = verse_blocks[i]
        verse_text = verse_blocks[i+1]
        
        verse_data = {
            "text_number": verse_num,
            "devanagari": "",
            "roman": "",
            "synonyms": "",
            "translation": "",
            "purport": ""
        }

        sections = re.split(r'\\sectitle\{(SYNONYMS|TRANSLATION|PURPORT)\}', verse_text)
        pre_sections = sections[0]
        
        devanagari_match = re.search(r'\\devanagari.*?\\textbf\{(.*?)\\par\}', pre_sections, re.DOTALL)
        if devanagari_match:
            verse_data["devanagari"] = latex_to_html(devanagari_match.group(1))
            
        roman_match = re.search(r'\{\\centering\s*\\textit\{(.*?)\\par\}', pre_sections, re.DOTALL)
        if roman_match:
            verse_data["roman"] = latex_to_html(roman_match.group(1))

        for j in range(1, len(sections), 2):
            sec_type = sections[j]
            sec_content = sections[j+1]
            
            if sec_type == "SYNONYMS":
                verse_data["synonyms"] = latex_to_html(sec_content)
            elif sec_type == "TRANSLATION":
                verse_data["translation"] = latex_to_html(sec_content)
            elif sec_type == "PURPORT":
                sec_content = re.sub(r'\\vspace\{.*?\\textit\{Thus end the Bhaktivedanta.*', '', sec_content, flags=re.DOTALL)
                verse_data["purport"] = latex_to_html(sec_content)
                
        chapter_data["verses"].append(verse_data)
        
    return chapter_data

def main():
    all_chapters = []
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.txt")))
    
    print(f"Found {len(files)} chapter files. Parsing...")
    for f in files:
        print(f" -> Processing {os.path.basename(f)}...")
        chapter_json = parse_chapter(f)
        all_chapters.append(chapter_json)
        
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_chapters, f, ensure_ascii=False, indent=4)
        
    print(f"Success! Data exported to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()