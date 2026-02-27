from bs4 import BeautifulSoup
from typing import Optional

def detect_form(html_content: str) -> Optional[str]:
    """
    Parses HTML with BeautifulSoup to find a likely newsletter subscription form.
    Returns a CSS selector for the form or email input, or None.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Priority 1: input[type="email"]
    email_inputs = soup.find_all('input', type='email')
    if email_inputs:
        return 'input[type="email"]'
        
    # Priority 2: name, id, placeholder contains "email"
    for inp in soup.find_all('input'):
        if inp.get('name') and 'email' in inp.get('name').lower():
            return f"input[name='{inp.get('name')}']"
        if inp.get('id') and 'email' in inp.get('id').lower():
            return f"input[id='{inp.get('id')}']"
        if inp.get('placeholder') and 'email' in inp.get('placeholder').lower():
            # Use a more generic selector if placeholder has quotes
            return f"input[placeholder*='email' i]"
            
    # Priority 3: form keywords
    keywords = ['subscribe', 'signup', 'newsletter', 'join', 'get updates']
    for form in soup.find_all('form'):
        form_text = form.get_text().lower()
        if any(kw in form_text for kw in keywords):
            if form.get('id'):
                return f"form#{form.get('id')} input[type='text'], form#{form.get('id')} input[type='email']"
            elif form.get('class'):
                cls = form.get('class')[0]
                return f"form.{cls} input[type='text'], form.{cls} input[type='email']"
                
    return None
