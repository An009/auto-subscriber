import re
import os

# Simple robust regex for standard email validation
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

def parse_emails_file(file_path: str) -> tuple[list, list]:
    """Reads file, returns (valid_emails, invalid_emails)"""
    # Performance/security: Limit file size (2MB)
    if os.path.getsize(file_path) > 2 * 1024 * 1024:
        raise ValueError("File exceeds 2MB limit.")
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Handle CSV and semicolon separated files by converting them to newlines
    content = content.replace(',', '\n').replace(';', '\n')
    lines = content.split('\n')
    
    valid = set()
    invalid = set()
    
    for line in lines:
        # Sanitize/trim
        line = line.strip()
        if not line:
            continue
            
        # Validate
        if EMAIL_REGEX.match(line):
            valid.add(line)
        else:
            invalid.add(line)
            
    return list(valid), list(invalid)
