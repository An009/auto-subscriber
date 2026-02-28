import pytest
from src.utils import parse_emails_file

def test_parse_emails_file(tmp_path):
    f = tmp_path / "emails.txt"
    f.write_text("valid1@example.com\nvalid2@test.co.uk\n invalid-email \n valid1@example.com \ncsv1@test.com, csv2@test.com; broken@ ")
    valid, invalid = parse_emails_file(str(f))
    
    assert set(valid) == {"valid1@example.com", "valid2@test.co.uk", "csv1@test.com", "csv2@test.com"}
    assert set(invalid) == {"invalid-email", "broken@"}
