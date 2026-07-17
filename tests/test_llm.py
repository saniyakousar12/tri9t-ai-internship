"""
Unit tests for LLM generator
"""

import sys
import os
import pytest
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.llm.generator import LLMGenerator


class TestLLMGenerator:
    """Test cases for LLM generator"""

    def setup_method(self):
        """Setup before each test"""
        self.generator = LLMGenerator()

    def test_parse_valid_json_response(self):
        """Test parsing valid JSON response"""
        response = '''
        [
            {
                "id": "TC-001",
                "title": "Test Pressure Limit",
                "description": "Verify pressure limit",
                "steps": ["Step 1", "Step 2"],
                "expected_result": "Alarm triggers",
                "priority": "High"
            }
        ]
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 1
        assert result[0]['id'] == 'TC-001'
        assert result[0]['priority'] == 'High'

    def test_parse_malformed_json_with_markdown(self):
        """Test parsing JSON from markdown code block"""
        response = '''
        Here are the test cases:
        ```json
        [
            {
                "id": "TC-002",
                "title": "Test Battery",
                "description": "Verify battery life",
                "steps": ["Step 1"],
                "expected_result": "Battery lasts 8 hours",
                "priority": "Medium"
            }
        ]
        ```
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 1
        assert result[0]['id'] == 'TC-002'
        assert result[0]['title'] == 'Test Battery'
        assert result[0]['priority'] == 'Medium'

    def test_parse_json_with_extra_text(self):
        """Test parsing JSON with extra text around it"""
        response = '''
        Based on the document, here are the test cases:

        [
            {
                "id": "TC-003",
                "title": "Test Display",
                "description": "Verify display functionality",
                "steps": ["Step 1", "Step 2", "Step 3"],
                "expected_result": "Display shows correct values",
                "priority": "High"
            }
        ]

        Let me know if you need more.
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 1
        assert result[0]['id'] == 'TC-003'
        assert len(result[0]['steps']) == 3

    def test_parse_multiple_test_cases(self):
        """Test parsing multiple test cases"""
        response = '''
        [
            {
                "id": "TC-001",
                "title": "Test 1",
                "description": "First test",
                "steps": ["Step 1"],
                "expected_result": "Pass",
                "priority": "High"
            },
            {
                "id": "TC-002",
                "title": "Test 2",
                "description": "Second test",
                "steps": ["Step 1", "Step 2"],
                "expected_result": "Pass",
                "priority": "Medium"
            },
            {
                "id": "TC-003",
                "title": "Test 3",
                "description": "Third test",
                "steps": ["Step 1"],
                "expected_result": "Pass",
                "priority": "Low"
            }
        ]
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 3
        assert result[0]['id'] == 'TC-001'
        assert result[1]['id'] == 'TC-002'
        assert result[2]['id'] == 'TC-003'
        assert result[0]['priority'] == 'High'
        assert result[1]['priority'] == 'Medium'
        assert result[2]['priority'] == 'Low'

    def test_validate_test_cases_valid(self):
        """Test validation of valid test cases"""
        valid_test_cases = [
            {
                "id": "TC-001",
                "title": "Valid Test",
                "description": "This is valid",
                "steps": ["Step 1", "Step 2"],
                "expected_result": "Success",
                "priority": "High"
            }
        ]

        # Should not raise any exception
        self.generator._validate_test_cases(valid_test_cases)

    def test_validate_test_cases_missing_field(self):
        """Test validation catches missing required fields"""
        invalid_test_case = [
            {
                "id": "TC-003",
                "title": "Test Display",
                "steps": ["Step 1"],
                "expected_result": "Display works",
                "priority": "Low"
            }
        ]

        with pytest.raises(ValueError) as excinfo:
            self.generator._validate_test_cases(invalid_test_case)

        assert "missing required field" in str(excinfo.value)

    def test_validate_test_cases_invalid_steps(self):
        """Test validation catches invalid steps (not a list)"""
        invalid_test_case = [
            {
                "id": "TC-004",
                "title": "Test Steps",
                "description": "Steps should be a list",
                "steps": "Not a list",
                "expected_result": "Works",
                "priority": "High"
            }
        ]

        with pytest.raises(ValueError) as excinfo:
            self.generator._validate_test_cases(invalid_test_case)

        assert "Steps must be a list" in str(excinfo.value)

    def test_validate_test_cases_invalid_priority(self):
        """Test validation catches invalid priority value"""
        invalid_test_case = [
            {
                "id": "TC-005",
                "title": "Test Priority",
                "description": "Priority should be High/Medium/Low",
                "steps": ["Step 1"],
                "expected_result": "Works",
                "priority": "Critical"
            }
        ]

        with pytest.raises(ValueError) as excinfo:
            self.generator._validate_test_cases(invalid_test_case)

        assert "Invalid priority" in str(excinfo.value)

    def test_validate_test_cases_empty_list(self):
        """Test validation of empty test case list"""
        with pytest.raises(ValueError) as excinfo:
            self.generator._validate_test_cases([])

        assert "No test cases generated" in str(excinfo.value)

    def test_handle_generation_failure(self):
        """Test generation failure handling"""
        error_message = "API rate limit exceeded"
        result = self.generator._handle_generation_failure(error_message)

        assert len(result) == 1
        assert result[0]['id'] == 'TC-001'
        assert result[0]['title'] == 'Manual Review Required'
        assert "API rate limit exceeded" in result[0]['description']
        assert result[0]['priority'] == 'High'

    def test_generate_fallback_response(self):
        """Test fallback response generation"""
        result = self.generator._generate_fallback_response()

        assert len(result) == 1
        assert result[0]['id'] == 'TC-FALLBACK'
        assert result[0]['title'] == 'Fallback Test Case'
        assert result[0]['priority'] == 'Medium'
        assert len(result[0]['steps']) == 1

    def test_parse_dict_response(self):
        """Test parsing response that's a dict (single test case)"""
        response = '''
        {
            "id": "TC-001",
            "title": "Single Test",
            "description": "Only one test",
            "steps": ["Step 1"],
            "expected_result": "Pass",
            "priority": "High"
        }
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 1
        assert result[0]['id'] == 'TC-001'

    def test_parse_response_with_tests_key(self):
        """Test parsing response with a 'tests' key"""
        response = '''
        {
            "tests": [
                {
                    "id": "TC-001",
                    "title": "Test 1",
                    "description": "First test",
                    "steps": ["Step 1"],
                    "expected_result": "Pass",
                    "priority": "High"
                },
                {
                    "id": "TC-002",
                    "title": "Test 2",
                    "description": "Second test",
                    "steps": ["Step 1"],
                    "expected_result": "Pass",
                    "priority": "Medium"
                }
            ]
        }
        '''

        result = self.generator._parse_response(response)
        assert len(result) == 2
        assert result[0]['id'] == 'TC-001'
        assert result[1]['id'] == 'TC-002'

    def test_auto_fix_test_id_format(self):
        """Test auto-fixing test ID format"""
        test_case = [
            {
                "id": "001",
                "title": "Test",
                "description": "Description",
                "steps": ["Step 1"],
                "expected_result": "Result",
                "priority": "High"
            }
        ]

        # Should fix the ID format
        self.generator._validate_test_cases(test_case)
        assert test_case[0]['id'] == 'TC-001'