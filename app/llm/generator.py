"""
LLM Generator for QA test case generation
"""

import json
import logging
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import os

from app.llm.prompt_templates import QA_GENERATION_PROMPT, FIX_JSON_PROMPT
from app.config import settings

logger = logging.getLogger(__name__)


class LLMGenerator:
    """Generate test cases using LLM"""
    
    def __init__(self):
        self.provider = settings.llm_provider
        self.client = self._initialize_client()
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        # Fallback models if primary fails
        self.fallback_models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "qwen/qwen3-32b"
        ]
    
    def _initialize_client(self):
        """Initialize LLM client based on provider"""
        if self.provider == "groq":
            from groq import Groq
            return Groq(api_key=settings.groq_api_key)
        elif self.provider == "openai":
            from openai import OpenAI
            return OpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def generate_test_cases(self, document_text: str) -> List[Dict]:
        """
        Generate test cases with retry logic
        
        Args:
            document_text: Document section text
            
        Returns:
            List of test case dictionaries
        """
        logger.info(f"Generating test cases for document (length: {len(document_text)} chars)")
        
        # Truncate if too long (prevent token overflow)
        if len(document_text) > 8000:
            document_text = document_text[:8000] + "... (truncated)"
        
        # Prepare prompt
        prompt = QA_GENERATION_PROMPT.format(document_text=document_text)
        
        try:
            # Call LLM
            response = self._call_llm(prompt)
            
            # Parse and validate
            test_cases = self._parse_response(response)
            self._validate_test_cases(test_cases)
            
            logger.info(f"Successfully generated {len(test_cases)} test cases")
            return test_cases
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {str(e)}. Attempting to fix...")
            return self._attempt_response_fix(response)
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            # Return a fallback response
            return self._handle_generation_failure(str(e))
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the prompt"""
        try:
            if self.provider == "groq":
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a QA engineer for medical devices. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=2000
                )
                return completion.choices[0].message.content
            
            elif self.provider == "openai":
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a QA engineer for medical devices. Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=2000
                )
                return completion.choices[0].message.content
                
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise
    
    def _parse_response(self, response: str) -> List[Dict]:
        """Parse LLM response into Python objects"""
        # Try to extract JSON from markdown blocks
        import re
        json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
        
        # Try to parse JSON
        try:
            data = json.loads(response)
            
            # If it's a dict with a 'tests' key, extract it
            if isinstance(data, dict) and 'tests' in data:
                return data['tests']
            
            # If it's a single test case, wrap in list
            if isinstance(data, dict):
                return [data]
            
            return data
            
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if array_match:
                try:
                    return json.loads(array_match.group(0))
                except:
                    pass
            
            raise
    
    def _validate_test_cases(self, test_cases: List[Dict]):
        """Validate test case structure"""
        required_fields = ["id", "title", "description", "steps", "expected_result", "priority"]
        
        if not test_cases:
            raise ValueError("No test cases generated")
        
        for tc in test_cases:
            # Check all required fields
            for field in required_fields:
                if field not in tc:
                    raise ValueError(f"Test case missing required field: {field}")
            
            # Validate steps is a list
            if not isinstance(tc["steps"], list):
                raise ValueError("Steps must be a list")
            
            # Validate priority
            if tc["priority"] not in ["High", "Medium", "Low"]:
                raise ValueError(f"Invalid priority: {tc['priority']}")
            
            # Validate id format
            if not tc["id"].startswith("TC-"):
                tc["id"] = f"TC-{tc['id']}"  # Fix format
    
    def _attempt_response_fix(self, response: str) -> List[Dict]:
        """Attempt to fix malformed JSON response"""
        try:
            # Try to fix common JSON issues
            # 1. Remove trailing commas
            fixed = re.sub(r',\s*}', '}', response)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # 2. Add missing quotes
            fixed = re.sub(r'([{,])\s*(\w+)\s*:', r'\1"\2":', fixed)
            
            # Parse again
            return self._parse_response(fixed)
            
        except Exception as e:
            logger.error(f"Failed to fix response: {str(e)}")
            # Return a minimal valid response
            return self._generate_fallback_response()
    
    def _handle_generation_failure(self, error: str) -> List[Dict]:
        """Handle generation failure with fallback response"""
        logger.error(f"Generation failed, returning fallback: {error}")
        
        return [
            {
                "id": "TC-001",
                "title": "Manual Review Required",
                "description": f"LLM generation failed: {error[:100]}",
                "steps": ["Please review the document manually"],
                "expected_result": "Test cases reviewed",
                "priority": "High"
            }
        ]
    
    def _generate_fallback_response(self) -> List[Dict]:
        """Generate a minimal valid response"""
        return [
            {
                "id": "TC-FALLBACK",
                "title": "Fallback Test Case",
                "description": "Generated due to parsing error",
                "steps": ["Review document manually"],
                "expected_result": "Test cases prepared",
                "priority": "Medium"
            }
        ]