import os
import re
import json
import glob

# Configuration
INPUT_DIR = "."
OUTPUT_FILE = "chapters.json"

def clean_text(text):
    """Core cleaning: strips LaTeX syntax and converts bold/italics."""
    if not text: return ""
    
    # 1. Destroy spacing commands completely (catches \vspace{...} and rogue \vspace0.5em)
    text = re.sub(r'\\[vh]space\*?\{[^}]*\}', '', text)
    text = re.sub(r'\\[vh]space[a-zA-Z0-9.]+', '', text) 
    
    # 2. Strip raw layout commands
    text = text.replace('\\noindent', '').replace('\\devanagari\\setstretch{0.85}', '')
    text = text.replace('\\centering', '')
    
    # 3. Handle double-nested bolding from LaTeX
    text = text.replace('\\textbf{\\textbf{', '<strong>').replace('}}', '</strong>')
    
    # 4. Standard Bold and Italics (Loops to catch any remaining basic nesting)
    for _ in range(3):
        text = re.sub(r'\\textbf\{([^{}]+)\}', r'<strong>\1</strong>', text)
        text = re.sub(r'\\textit\{([^{}]+)\}', r'<em>\1</em>', text)
        
    # 5. Catch any unmatched tags and line breaks
    text = text.replace('\\textbf{', '<strong>').replace('\\textit{', '<em>')
    text = re.sub(r'\\\\(?:\*)?\s*', '<br>', text)
    
    # 6. THE KILL SWITCH: Strip ALL remaining '{' and '}'
    text = text.replace('{', '').replace('}', '')
    
    return text.strip()

def process_inline(text):
    """Processes simple text blocks (Synonyms, Translation)."""
    text = clean_text(text)
    return text.replace('\\par', '<br>').replace('\n\n', '<br>')

def process_purport(text):
    """Processes complex purports, creating quote blocks and paragraph tags."""
    if not text: return ""
    
    # Extract the centered Sanskrit quotes BEFORE stripping braces
    text = re.sub(r'\{\s*\\centering(.*?)\\par\}', r'<blockquote class="quote-block">\1</blockquote>', text, flags=re.DOTALL)
    
    # Send through the core cleaner to strip everything else
    text = clean_text(text)
    
    # Standardize paragraph breaks
    text = text.replace('\\par', '\n\n')
    blocks = re.split(r'\n\s*\n', text)
    
    html_blocks = []
    for block in blocks:
        block = block.strip()
        if not block: continue
        
        # If it is our centered quote, keep it isolated
        if '<blockquote' in block:
            html_blocks.append(block)
        else:
            # Wrap regular text in paragraph tags for perfect CSS indentation
            html_blocks.append(f'<p>{block}</p>')
            
    return '\n'.join(html_blocks)

def parse_chapter(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    chapter_num_match = re.search(r'CHAPTER\s+([A-Z]+)', content)
    chapter_title_match = re.search(r'\\fontsize\{19pt\}\{21pt\}\\selectfont\\textbf\{(.*?)\}', content, re.DOTALL)
    
    chapter_data = {
        "chapter_number": chapter_num_match.group(1) if chapter_num_match else "UNKNOWN",
        "chapter_title": clean_text(chapter_title_match.group(1)) if chapter_title_match else "UNKNOWN",
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
                # Remove the "Thus end the..." sign-off if it exists
                sec_content = re.sub(r'\\vspace\{.*?\\textit\{Thus end the Bhaktivedanta.*', '', sec_content, flags=re.DOTALL)
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