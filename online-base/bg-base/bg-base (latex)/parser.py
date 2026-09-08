import os
import re
import json
import glob

# Configuration
INPUT_DIR = "."
OUTPUT_FILE = "chapters.json"

def latex_to_html(text):
    """Converts basic LaTeX formatting to HTML for the web reader."""
    if not text: return ""
    # Remove specific LaTeX commands but keep the text
    text = re.sub(r'\\noindent\s*', '', text)
    text = re.sub(r'\\hspace\*\{.*?\}', '&nbsp;&nbsp;&nbsp;&nbsp;', text)
    text = re.sub(r'\\par', '<br>', text)
    text = re.sub(r'\\\\(?:\*)?', '<br>', text) # Handle \\ and \\*
    
    # Convert bold and italics
    text = re.sub(r'\\textbf\{([^}]+)\}', r'<strong>\1</strong>', text)
    text = re.sub(r'\\textit\{([^}]+)\}', r'<em>\1</em>', text)
    
    # Strip remaining layout wrappers
    text = re.sub(r'\{\\centering(.*?)\}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\devanagari\\setstretch\{.*?\}', '', text)
    
    return text.strip()

def parse_chapter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Extract Chapter Number and Title
    chapter_num_match = re.search(r'CHAPTER\s+([A-Z]+)', content)
    chapter_title_match = re.search(r'\\fontsize\{19pt\}\{21pt\}\\selectfont\\textbf\{(.*?)\}', content, re.DOTALL)
    
    chapter_data = {
        "chapter_number": chapter_num_match.group(1) if chapter_num_match else "UNKNOWN",
        "chapter_title": latex_to_html(chapter_title_match.group(1)) if chapter_title_match else "UNKNOWN",
        "verses": []
    }

    # 2. Split the document by \texttitle (Each verse block)
    verse_blocks = re.split(r'\\texttitle\{TEXTS?\s+([0-9-]+)\}', content)[1:] # Skip preamble
    
    # Iterate through pairs of (Verse Number, Verse Content)
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

        # 3. Extract sections using your specific \sectitle macros
        # Split by \sectitle to get SYNONYMS, TRANSLATION, PURPORT
        sections = re.split(r'\\sectitle\{(SYNONYMS|TRANSLATION|PURPORT)\}', verse_text)
        
        # The first chunk (sections[0]) contains the Devanagari and Roman transliteration
        pre_sections = sections[0]
        
        # Naive extraction for Devanagari (first bold block) and Roman (first italic block)
        devanagari_match = re.search(r'\\devanagari.*?\\textbf\{(.*?)\\par\}', pre_sections, re.DOTALL)
        if devanagari_match:
            verse_data["devanagari"] = latex_to_html(devanagari_match.group(1))
            
        roman_match = re.search(r'\{\\centering\s*\\textit\{(.*?)\\par\}', pre_sections, re.DOTALL)
        if roman_match:
            verse_data["roman"] = latex_to_html(roman_match.group(1))

        # Loop through the remaining sections to assign them properly
        for j in range(1, len(sections), 2):
            sec_type = sections[j]
            sec_content = sections[j+1]
            
            if sec_type == "SYNONYMS":
                verse_data["synonyms"] = latex_to_html(sec_content)
            elif sec_type == "TRANSLATION":
                verse_data["translation"] = latex_to_html(sec_content)
            elif sec_type == "PURPORT":
                # Clean up the purport end-marker if it exists
                sec_content = re.sub(r'\\vspace\{.*?\\textit\{Thus end the Bhaktivedanta.*', '', sec_content, flags=re.DOTALL)
                verse_data["purport"] = latex_to_html(sec_content)
                
        chapter_data["verses"].append(verse_data)
        
    return chapter_data

def main():
    all_chapters = []
    # Find all txt files in the latex folder
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