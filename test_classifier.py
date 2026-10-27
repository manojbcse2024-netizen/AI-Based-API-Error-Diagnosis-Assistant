import pytest
from backend.classifier import classify_error

@pytest.mark.parametrize("status,category",[(401,"authentication"),(403,"authorization"),(422,"validation"),(429,"rate_limit"),(504,"timeout"),(503,"server")])
def test_classifies_status_codes(status,category):
    assert classify_error({"status_code":status})["key"]==category

def test_unknown_is_uncertain():
    result=classify_error({"status_code":200})
    assert result["key"]=="unknown" and result["uncertain"]

def test_textual_timeout_classification():
    assert classify_error({"error_message":"deadline exceeded"})["key"]=="timeout"
