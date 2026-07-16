"""
Unit tests for LLM Generator
"""

import json
import pytest

from app.llm.generator import LLMGenerator


class TestLLMGenerator:
    """Tests for the LLMGenerator class."""

    @pytest.fixture
    def generator(self):
        """
        Create an instance without calling __init__()
        so no real API client is created.
        """
        return LLMGenerator.__new__(LLMGenerator)

    # ==========================================================
    # RESPONSE PARSING
    # ==========================================================

    def test_parse_valid_json(self, generator):

        response = """
        [
            {
                "id":"TC-001",
                "title":"Pressure Test",
                "description":"Verify pressure limit",
                "steps":["Step 1","Step 2"],
                "expected_result":"Alarm triggers",
                "priority":"High"
            }
        ]
        """

        result = generator._parse_response(response)

        assert len(result) == 1
        assert result[0]["id"] == "TC-001"
        assert result[0]["priority"] == "High"

    def test_parse_markdown_json(self, generator):

        response = """
```json
[
    {
        "id":"TC-002",
        "title":"Battery Test",
        "description":"Check battery",
        "steps":["Step 1"],
        "expected_result":"Battery works",
        "priority":"Medium"
    }
]

"""

    result = generator._parse_response(response)

    assert len(result) == 1
    assert result[0]["title"] == "Battery Test"

def test_parse_dictionary(self, generator):

    response = """

{
"id":"TC-003",
"title":"Display Test",
"description":"Display Verification",
"steps":["Step 1"],
"expected_result":"Display OK",
"priority":"Low"
}
"""

    result = generator._parse_response(response)

    assert len(result) == 1
    assert result[0]["id"] == "TC-003"

def test_parse_tests_key(self, generator):

    response = """

{
"tests":[
{
"id":"TC-004",
"title":"Alarm Test",
"description":"Alarm Check",
"steps":["Step 1"],
"expected_result":"Alarm Sounds",
"priority":"High"
}
]
}
"""

    result = generator._parse_response(response)

    assert len(result) == 1
    assert result[0]["title"] == "Alarm Test"

def test_invalid_json(self, generator):

    with pytest.raises(json.JSONDecodeError):
        generator._parse_response("Not a JSON Response")

# ==========================================================
# VALIDATION
# ==========================================================

def test_validate_valid_testcase(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test",
            "description":"Description",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"High"
        }
    ]

    generator._validate_test_cases(data)

def test_missing_field(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"High"
        }
    ]

    with pytest.raises(ValueError):
        generator._validate_test_cases(data)

def test_invalid_priority(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test",
            "description":"Description",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"Critical"
        }
    ]

    with pytest.raises(ValueError):
        generator._validate_test_cases(data)

def test_steps_not_list(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test",
            "description":"Description",
            "steps":"Wrong",
            "expected_result":"Pass",
            "priority":"High"
        }
    ]

    with pytest.raises(ValueError):
        generator._validate_test_cases(data)

def test_empty_testcases(self, generator):

    with pytest.raises(ValueError):
        generator._validate_test_cases([])

def test_auto_fix_id(self, generator):

    data = [
        {
            "id":"001",
            "title":"Test",
            "description":"Description",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"Medium"
        }
    ]

    generator._validate_test_cases(data)

    assert data[0]["id"] == "TC-001"

# ==========================================================
# RESPONSE FIX
# ==========================================================

def test_fix_trailing_comma(self, generator):

    response = """

[
{
"id":"TC-001",
"title":"Test",
"description":"Description",
"steps":["One"],
"expected_result":"Pass",
"priority":"High",
}
]
"""

    result = generator._attempt_response_fix(response)

    assert result[0]["id"] == "TC-001"

def test_fix_unquoted_keys(self, generator):

    response = """

[
{
id:"TC-001",
title:"Test",
description:"Description",
steps:["One"],
expected_result:"Pass",
priority:"High"
}
]
"""

    result = generator._attempt_response_fix(response)

    assert result[0]["title"] == "Test"

def test_invalid_json_returns_fallback(self, generator):

    result = generator._attempt_response_fix("%%%% invalid json %%%%")

    assert len(result) == 1
    assert result[0]["id"] == "TC-FALLBACK"

# ==========================================================
# FALLBACK
# ==========================================================

def test_generate_fallback(self, generator):

    result = generator._generate_fallback_response()

    assert len(result) == 1
    assert result[0]["id"] == "TC-FALLBACK"
    assert result[0]["priority"] == "Medium"

def test_generation_failure(self, generator):

    result = generator._handle_generation_failure("Rate Limit")

    assert len(result) == 1
    assert result[0]["title"] == "Manual Review Required"
    assert result[0]["priority"] == "High"

def test_long_error_message(self, generator):

    error = "A" * 500

    result = generator._handle_generation_failure(error)

    assert len(result) == 1
    assert "LLM generation failed" in result[0]["description"]

# ==========================================================
# STRUCTURE
# ==========================================================

def test_fallback_structure(self, generator):

    result = generator._generate_fallback_response()

    tc = result[0]

    assert "id" in tc
    assert "title" in tc
    assert "description" in tc
    assert "steps" in tc
    assert "expected_result" in tc
    assert "priority" in tc

def test_special_characters(self, generator):

    result = generator._handle_generation_failure(
        "Pressure 200 mmHg ±5%"
    )

    assert len(result) == 1

def test_parse_multiple_testcases(self, generator):

    response = """

[
{
"id":"TC-001",
"title":"Test1",
"description":"Desc1",
"steps":["Step1"],
"expected_result":"Pass",
"priority":"High"
},
{
"id":"TC-002",
"title":"Test2",
"description":"Desc2",
"steps":["Step1"],
"expected_result":"Pass",
"priority":"Medium"
}
]
"""

    result = generator._parse_response(response)

    assert len(result) == 2
    assert result[1]["id"] == "TC-002"

def test_validate_multiple_cases(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test1",
            "description":"Desc",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"High"
        },
        {
            "id":"TC-002",
            "title":"Test2",
            "description":"Desc",
            "steps":["Step"],
            "expected_result":"Pass",
            "priority":"Medium"
        }
    ]

    generator._validate_test_cases(data)

def test_missing_priority(self, generator):

    data = [
        {
            "id":"TC-001",
            "title":"Test",
            "description":"Desc",
            "steps":["Step"],
            "expected_result":"Pass"
        }
    ]

    with pytest.raises(ValueError):
        generator._validate_test_cases(data)