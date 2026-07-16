"""
Prompt templates for LLM interactions
"""

QA_GENERATION_PROMPT = """
You are a QA engineer for medical devices. Generate 3-5 test cases based on the following document section:

{document_text}

Requirements:
1. Each test case must be specific and executable
2. Include: Test ID, Description, Steps, Expected Result, Priority
3. Focus on safety-critical aspects
4. Test IDs should follow format: TC-001, TC-002, etc.

Format your response as a valid JSON array:
[
    {{
        "id": "TC-001",
        "title": "Test title",
        "description": "What this test verifies",
        "steps": ["Step 1", "Step 2"],
        "expected_result": "What should happen",
        "priority": "High/Medium/Low"
    }}
]

Only output the JSON array, no additional text.
"""

FIX_JSON_PROMPT = """
The following response from the LLM is not valid JSON. Please fix it to be valid JSON:

{invalid_response}

The JSON should follow this schema:
[
    {{
        "id": "TC-XXX",
        "title": "string",
        "description": "string",
        "steps": ["string"],
        "expected_result": "string",
        "priority": "High/Medium/Low"
    }}
]

Output only the fixed JSON array.
"""

DOCUMENT_RECONSTRUCTION_TEMPLATE = """
Document Section Reconstruction:
{content}

Please extract the key requirements and generate test cases.
"""