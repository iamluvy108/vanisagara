import os
import re
import json
import glob

# Configuration
INPUT_DIR = "."
OUTPUT_FILE = "chapters.json"

def clean_latex_formatting(text):
    """Surgically cleans text, handles nested bold/italics, and strips raw LaTeX."""
    if not text: return ""
    
    # Strip raw layout commands
    text = text.replace('\\noindent', '').replace('\\devanagari\\setstretch{0.85}', '').replace('\\centering', '')
    
    # Recursively un-nest bold and italics safely to prevent HTML bleeding
    while True:
        new_text = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', text)
        new_text = re.sub(r'\\textit\{([^{}]+)\}', r'<em>\1</em>', new_text)
        if new_text == text: break
        text = new_text
        
    # THE KILL SWITCH: Strip any remaining raw tags and braces
    text = text.replace('\\textbf', '').replace('\\textit', '')
    text = text.replace('{', '').replace('}', '')
    return text.strip()

def process_inline(text):
    """Processes simple text blocks (Synonyms, Translation, Devanagari)."""
    if not text: return ""
    # Destroy any \vspace or \hspace, with or without braces
    text = re.sub(r'\\[vh]space\*?(?:\{[^}]*\}|\s*[0-9.]+[a-zA-Z]+)', '', text)
    
    # NEW: Catch LaTeX line-breaks with spacing modifiers (like \\[0.8em]) BEFORE stripping
    text = re.sub(r'\\\\(?:\*)?\[.*?\]\s*', '<br><br>', text)
    text = re.sub(r'\\\\(?:\*)?\s*', '<br>', text)
    
    text = clean_latex_formatting(text)
    text = text.replace('\\par', '<br>').replace('\n\n', '<br>')
    text = re.sub(r'(<br>\s*)+$', '', text)
    return text.strip()

def process_purport(text):
    """Processes complex purports, creating quote blocks and paragraph tags."""
    if not text: return ""
    
    # Remove the "Thus end the..." sign-off at the end of chapters
    text = re.sub(r'\\vspace\*?(?:\{[^}]*\}|\s*[0-9.]+[a-zA-Z]+)?\s*\\textit\{Thus end the Bhaktivedanta.*', '', text, flags=re.DOTALL)
    
    # Destroy spacing commands (catches \vspace{...} and rogue \vspace0.5em)
    text = re.sub(r'\\[vh]space\*?(?:\{[^}]*\}|\s*[0-9.]+[a-zA-Z]+)', '', text)
    
    # Extract centered quotes and turn them into HTML blockquotes
    text = re.sub(r'\{\s*\\centering(.*?)\\par\}', r'\n\n<blockquote class="quote-block">\1</blockquote>\n\n', text, flags=re.DOTALL)
    text = re.sub(r'\{\s*\\centering(.*?)\}', r'\n\n<blockquote class="quote-block">\1</blockquote>\n\n', text, flags=re.DOTALL)
    
    # Clean the rest of the text
    text = clean_latex_formatting(text)
    
    # Split the text into actual paragraphs
    text = text.replace('\\par', '\n\n').replace('<br>', '\n\n')
    paragraphs = re.split(r'\n\s*\n', text)
    
    html_blocks = []
    for p in paragraphs:
        p = p.strip()
        if not p: continue
        
        if p.startswith('<blockquote'):
            # Convert internal linebreaks within the quote block (Handles \\[0.8em])
            p = re.sub(r'\\\\(?:\*)?\[.*?\]\s*', '<br><br>', p)
            p = re.sub(r'\\\\(?:\*)?\s*', '<br>', p)
            html_blocks.append(p)
        else:
            # Wrap standard text in paragraph tags for perfect CSS indentation
            p = re.sub(r'\\\\(?:\*)?\[.*?\]\s*', ' ', p)
            p = re.sub(r'\\\\(?:\*)?\s*', ' ', p)
            html_blocks.append(f'<p>{p}</p>')
            
    return '\n'.join(html_blocks)

def parse_chapter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapter_num_match = re.search(r'CHAPTER\s+([A-Z]+)', content)
    chapter_title_match = re.search(r'\\fontsize\{19pt\}\{21pt\}\\selectfont\\textbf\{(.*?)\}', content, re.DOTALL)
    
    chapter_data = {
        "chapter_number": chapter_num_match.group(1) if chapter_num_match else "UNKNOWN",
        "chapter_title": clean_latex_formatting(chapter_title_match.group(1)) if chapter_title_match else "UNKNOWN",
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
            verse_data["devanagari"] = process_inline(devanagari_match.group(1))
            
        roman_match = re.search(r'\{\\centering\s*\\textit\{(.*?)\\par\}', pre_sections, re.DOTALL)
        if roman_match:
            verse_data["roman"] = process_inline(roman_match.group(1))

        for j in range(1, len(sections), 2):
            sec_type = sections[j]
            sec_content = sections[j+1]
            
            if sec_type == "SYNONYMS":
                verse_data["synonyms"] = process_inline(sec_content)
            elif sec_type == "TRANSLATION":
                verse_data["translation"] = process_inline(sec_content)
            elif sec_type == "PURPORT":
                verse_data["purport"] = process_purport(sec_content)
                
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