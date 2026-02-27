import pytest
from src.detector import detect_form

def test_detect_email_input_type():
    html = '<form><input type="email" name="test"/></form>'
    assert detect_form(html) == 'input[type="email"]'

def test_detect_email_by_name():
    html = '<form><input type="text" name="user_email"/></form>'
    assert detect_form(html) == "input[name='user_email']"

def test_detect_by_form_keyword():
    html = '<form id="subForm">Subscribe to our newsletter<input type="text"/></form>'
    assert detect_form(html) in ["form#subForm input[type='text'], form#subForm input[type='email']"]

def test_no_form_detected():
    html = '<div>Just some text here without any forms.</div>'
    assert detect_form(html) is None
