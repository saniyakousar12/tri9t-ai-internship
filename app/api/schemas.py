"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============ BROWSE API SCHEMAS ============

class SectionListResponse(BaseModel):
    """Response for listing sections"""
    id: int
    heading: str
    level: int
    child_count: int


class NodeResponse(BaseModel):
    """Response for getting a single node"""
    id: int
    heading: str
    level: int
    body_text: Optional[str] = None
    content_hash: str
    parent_id: Optional[int] = None
    children: List[int] = []
    has_changed_across_versions: bool = False


class SearchResponse(BaseModel):
    """Response for search results"""
    id: int
    heading: str
    level: int
    body_preview: str


# ============ SELECTION API SCHEMAS ============

class SelectionCreate(BaseModel):
    """Request for creating a selection"""
    name: str = Field(..., description="Selection name")
    node_ids: List[int] = Field(..., description="List of node IDs to select")
    version: Optional[int] = Field(None, description="Document version (defaults to latest)")


class SelectionResponse(BaseModel):
    """Response for selection operations"""
    id: int
    name: str
    version: int
    node_ids: List[int]
    created_at: datetime


# ============ GENERATION API SCHEMAS ============

class GenerateRequest(BaseModel):
    """Request for generating test cases"""
    selection_id: int = Field(..., description="Selection ID to generate from")
    force: bool = Field(False, description="Force regeneration if already exists")


class TestCase(BaseModel):
    """Individual test case"""
    id: str
    title: str
    description: str
    steps: List[str]
    expected_result: str
    priority: str


class GenerateResponse(BaseModel):
    """Response for generation"""
    status: str
    selection_id: Optional[int] = None
    test_cases: Optional[List[Dict[str, Any]]] = None
    version_used: Optional[int] = None
    generated_at: Optional[datetime] = None
    message: Optional[str] = None
    existing_tests: Optional[List[Dict[str, Any]]] = None


# ============ STALENESS API SCHEMAS ============

class StalenessNode(BaseModel):
    """Staleness info for a single node"""
    node_id: int
    old_hash: Optional[str] = None
    new_hash: Optional[str] = None
    reason: Optional[str] = None
    severity: str = "info"


class StalenessResponse(BaseModel):
    """Response for staleness check"""
    is_stale: bool
    stale_nodes: List[StalenessNode] = []
    changed_nodes: List[StalenessNode] = []
    message: str
    version_at_generation: int
    current_version: int


# ============ DIFF SCHEMAS ============

class DiffResponse(BaseModel):
    """Response for diff between versions"""
    node_id: int
    from_version: int
    to_version: int
    heading: str
    has_changed: bool
    diff: Optional[Dict[str, Any]] = None