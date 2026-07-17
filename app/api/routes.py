"""
API routes for the Tri9T AI system
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from typing import List, Optional
from datetime import datetime
import logging
import os
import hashlib

from app.database import get_db
from app.api.schemas import (
    NodeResponse, SectionListResponse, SearchResponse,
    SelectionCreate, SelectionResponse, GenerateRequest,
    GenerateResponse
)
from app.models.node import Node
from app.models.document import Document
from app.models.selection import Selection
from app.models.generated_test import GeneratedTest
from app.versioning.manager import VersionManager
from app.services.staleness import StalenessChecker
from app.llm.generator import LLMGenerator
from app.parser.pdf_parser import PDFParser

logger = logging.getLogger(__name__)

router = APIRouter()

version_manager = VersionManager()
staleness_checker = StalenessChecker()
llm_generator = LLMGenerator()


# ============ INGESTION ============

@router.post("/ingest", status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    version: int = Query(..., description="Document version number"),
    db: Session = Depends(get_db)
):
    logger.info(f"Ingesting version {version} of {file.filename}")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    existing = db.query(Document).filter(Document.version == version).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Version {version} already exists")
    
    temp_path = f"/tmp/{file.filename}"
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        
        parser = PDFParser(temp_path)
        nodes_data = parser.parse_structure()
        
        if not nodes_data:
            raise HTTPException(status_code=400, detail="No content extracted")
        
        doc = Document(
            version=version,
            filename=file.filename,
            file_hash=hashlib.sha256(content).hexdigest(),
            total_nodes=len(nodes_data)
        )
        db.add(doc)
        db.flush()
        
        for node_data in nodes_data:
            node = Node(
                document_id=doc.id,
                heading=node_data.get("heading", "Untitled"),
                level=node_data.get("level", 1),
                body_text=node_data.get("body_text", ""),
                content_hash=node_data.get("content_hash", ""),
                parent_id=node_data.get("parent_id"),
                logical_id=node_data.get("logical_id"),
                page_number=node_data.get("page_number"),
                position=node_data.get("position", 0)
            )
            db.add(node)
        
        db.commit()
        
        if version > 1:
            version_manager.link_with_previous_version(doc.id, db)
        
        return {"status": "success", "document_id": doc.id, "version": version, "nodes_created": len(nodes_data)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ============ BROWSE ============

@router.get("/sections", response_model=List[SectionListResponse])
async def list_sections(
    version: Optional[int] = Query(None),
    parent_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    if version is None:
        doc = db.query(Document).order_by(Document.version.desc()).first()
        if not doc:
            raise HTTPException(status_code=404, detail="No documents found")
        version = doc.version
    else:
        doc = db.query(Document).filter(Document.version == version).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    query = db.query(Node).filter(Node.document_id == doc.id)
    if parent_id is None:
        query = query.filter(Node.parent_id.is_(None))
    else:
        query = query.filter(Node.parent_id == parent_id)
    
    nodes = query.order_by(Node.position, Node.id).all()
    return [SectionListResponse(id=n.id, heading=n.heading, level=n.level, child_count=len(n.children)) for n in nodes]


@router.get("/node/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int, version: Optional[int] = Query(None), db: Session = Depends(get_db)):
    if version is None:
        doc = db.query(Document).order_by(Document.version.desc()).first()
        if not doc:
            raise HTTPException(status_code=404, detail="No documents found")
        version = doc.version
    else:
        doc = db.query(Document).filter(Document.version == version).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    node = db.query(Node).filter(Node.id == node_id, Node.document_id == doc.id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    has_changed = False
    if version > 1:
        has_changed = version_manager.has_node_changed(node.logical_id, version, db)
    
    children = db.query(Node).filter(Node.parent_id == node.id, Node.document_id == doc.id).all()
    
    return NodeResponse(
        id=node.id, heading=node.heading, level=node.level,
        body_text=node.body_text, content_hash=node.content_hash,
        parent_id=node.parent_id, children=[c.id for c in children],
        has_changed_across_versions=has_changed,
        page_number=node.page_number, logical_id=node.logical_id
    )


@router.get("/search", response_model=List[SearchResponse])
async def search_nodes(q: str, version: Optional[int] = Query(None), limit: int = Query(50), db: Session = Depends(get_db)):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    
    if version is None:
        doc = db.query(Document).order_by(Document.version.desc()).first()
        if not doc:
            raise HTTPException(status_code=404, detail="No documents found")
        version = doc.version
    else:
        doc = db.query(Document).filter(Document.version == version).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    search_pattern = f"%{q}%"
    nodes = db.query(Node).filter(
        Node.document_id == doc.id,
        (Node.heading.ilike(search_pattern) | Node.body_text.ilike(search_pattern))
    ).limit(limit).all()
    
    return [SearchResponse(id=n.id, heading=n.heading, level=n.level, body_preview=n.body_text[:200] if n.body_text else "", match_type="heading" if q.lower() in n.heading.lower() else "body") for n in nodes]


@router.get("/node/{node_id}/diff")
async def get_node_diff(node_id: int, from_version: int, to_version: int, db: Session = Depends(get_db)):
    if from_version == to_version:
        raise HTTPException(status_code=400, detail="Versions must be different")
    
    from_doc = db.query(Document).filter(Document.version == from_version).first()
    to_doc = db.query(Document).filter(Document.version == to_version).first()
    
    if not from_doc or not to_doc:
        raise HTTPException(status_code=404, detail="Version not found")
    
    from_node = db.query(Node).filter(Node.id == node_id, Node.document_id == from_doc.id).first()
    if not from_node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found in version {from_version}")
    
    to_node = db.query(Node).filter(Node.logical_id == from_node.logical_id, Node.document_id == to_doc.id).first()
    if not to_node:
        to_node = db.query(Node).filter(Node.heading == from_node.heading, Node.document_id == to_doc.id).first()
    
    if not to_node:
        return {"status": "deleted", "node_id": node_id, "heading": from_node.heading, "from_version": from_version, "to_version": to_version, "has_changed": True}
    
    diff = version_manager.generate_diff(from_node.body_text or "", to_node.body_text or "", from_node.content_hash, to_node.content_hash)
    
    return {
        "status": "found",
        "node_id": node_id,
        "heading": from_node.heading,
        "from_version": from_version,
        "to_version": to_version,
        "has_changed": from_node.content_hash != to_node.content_hash,
        "diff": diff,
        "structural_changes": {"level_changed": from_node.level != to_node.level, "from_level": from_node.level, "to_level": to_node.level, "parent_changed": from_node.parent_id != to_node.parent_id, "from_parent": from_node.parent_id, "to_parent": to_node.parent_id}
    }


# ============ SELECTION ============

@router.post("/selection", response_model=SelectionResponse, status_code=201)
async def create_selection(selection: SelectionCreate, db: Session = Depends(get_db)):
    if selection.version is None:
        doc = db.query(Document).order_by(Document.version.desc()).first()
        if not doc:
            raise HTTPException(status_code=404, detail="No documents found")
        version = doc.version
    else:
        version = selection.version
    
    doc = db.query(Document).filter(Document.version == version).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    existing = db.query(Selection).filter(Selection.name == selection.name, Selection.version == version).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Selection '{selection.name}' already exists")
    
    if not selection.node_ids:
        raise HTTPException(status_code=400, detail="At least one node ID is required")
    
    for node_id in selection.node_ids:
        node = db.query(Node).filter(Node.id == node_id, Node.document_id == doc.id).first()
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    db_selection = Selection(name=selection.name, version=version)
    db.add(db_selection)
    db.flush()
    
    for node_id in selection.node_ids:
        db.execute(
            text("INSERT INTO selection_nodes (selection_id, node_id, node_version) VALUES (:sid, :nid, :nv)"),
            {"sid": db_selection.id, "nid": node_id, "nv": version}
        )
    
    db.commit()
    db.refresh(db_selection)
    return SelectionResponse(id=db_selection.id, name=db_selection.name, version=db_selection.version, node_ids=selection.node_ids, created_at=db_selection.created_at)


@router.get("/selection/{selection_id}", response_model=SelectionResponse)
async def get_selection(
    selection_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a selection with its versioned nodes.
    """
    selection = db.query(Selection).filter(Selection.id == selection_id).first()
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")
    
    # THIS MUST HAVE text() WRAPPER
    result = db.execute(
        text("SELECT node_id FROM selection_nodes WHERE selection_id = :selection_id"),
        {"selection_id": selection_id}
    )
    node_ids = [row[0] for row in result.fetchall()]
    
    return SelectionResponse(
        id=selection.id,
        name=selection.name,
        version=selection.version,
        node_ids=node_ids,
        created_at=selection.created_at
    )

@router.get("/selections")
async def list_selections(version: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Selection)
    if version is not None:
        query = query.filter(Selection.version == version)
    selections = query.order_by(Selection.created_at.desc()).all()
    
    return [{
        "id": s.id,
        "name": s.name,
        "version": s.version,
        "created_at": s.created_at,
        "node_count": db.execute(text("SELECT COUNT(*) FROM selection_nodes WHERE selection_id = :sid"), {"sid": s.id}).scalar()
    } for s in selections]


@router.delete("/selection/{selection_id}")
async def delete_selection(selection_id: int, db: Session = Depends(get_db)):
    selection = db.query(Selection).filter(Selection.id == selection_id).first()
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")
    
    db.execute(text("DELETE FROM selection_nodes WHERE selection_id = :sid"), {"sid": selection_id})
    db.query(GeneratedTest).filter(GeneratedTest.selection_id == selection_id).delete()
    db.delete(selection)
    db.commit()
    return {"status": "success", "message": f"Selection {selection_id} deleted"}


# ============ GENERATION ============

@router.post("/generate", response_model=GenerateResponse)
async def generate_test_cases(request: GenerateRequest, db: Session = Depends(get_db)):
    selection = db.query(Selection).filter(Selection.id == request.selection_id).first()
    if not selection:
        raise HTTPException(status_code=404, detail=f"Selection {request.selection_id} not found")
    
    existing = db.query(GeneratedTest).filter(GeneratedTest.selection_id == request.selection_id).first()
    if existing and not request.force:
        staleness = staleness_checker.check_staleness(existing, db)
        return GenerateResponse(status="already_generated", selection_id=request.selection_id, message="Use force=true to regenerate", existing_tests=existing.output, version_used=existing.version_at_generation, generated_at=existing.created_at, staleness=staleness)
    
    doc = db.query(Document).filter(Document.version == selection.version).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document version {selection.version} not found")
    
    result = db.execute(
        text("""
            SELECT sn.node_id, n.heading, n.body_text, n.level, n.position
            FROM selection_nodes sn JOIN nodes n ON n.id = sn.node_id
            WHERE sn.selection_id = :sid AND n.document_id = :did
            ORDER BY n.position
        """),
        {"sid": request.selection_id, "did": doc.id}
    )
    selected_nodes = result.fetchall()
    
    if not selected_nodes:
        raise HTTPException(status_code=400, detail="No nodes found in this selection")
    
    document_text = "DOCUMENT SECTION:\n\n"
    for node in selected_nodes:
        indent = "  " * (node.level - 1)
        document_text += f"{indent}{node.heading}\n"
        if node.body_text:
            document_text += f"{indent}  {node.body_text}\n\n"
    
    try:
        test_cases = llm_generator.generate_test_cases(document_text)
        if not test_cases:
            raise ValueError("No test cases generated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
    
    if existing and request.force:
        existing.output = test_cases
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        generated_test = existing
    else:
        generated_test = GeneratedTest(selection_id=request.selection_id, output=test_cases, version_at_generation=selection.version, created_at=datetime.now())
        db.add(generated_test)
        db.commit()
        db.refresh(generated_test)
    
    return GenerateResponse(status="success", selection_id=request.selection_id, test_cases=test_cases, version_used=selection.version, generated_at=generated_test.created_at, message=f"Generated {len(test_cases)} test cases")


@router.get("/generations/selection/{selection_id}")
async def get_generated_tests(selection_id: int, include_staleness: bool = True, db: Session = Depends(get_db)):
    selection = db.query(Selection).filter(Selection.id == selection_id).first()
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")
    
    tests = db.query(GeneratedTest).filter(GeneratedTest.selection_id == selection_id).order_by(GeneratedTest.created_at.desc()).all()
    if not tests:
        return {"selection_id": selection_id, "selection_name": selection.name, "message": "No generated tests found", "tests": []}
    
    response = []
    for test in tests:
        result = {"id": test.id, "selection_id": test.selection_id, "output": test.output, "version_at_generation": test.version_at_generation, "generated_at": test.created_at, "updated_at": test.updated_at}
        if include_staleness:
            result["staleness"] = staleness_checker.check_staleness(test, db)
        response.append(result)
    
    return {"selection_id": selection_id, "selection_name": selection.name, "total_tests": len(response), "tests": response}


@router.get("/tests/node/{node_id}")
async def get_tests_by_node(node_id: int, version: Optional[int] = Query(None), db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    result = db.execute(
        text("SELECT selection_id FROM selection_nodes WHERE node_id = :nid"),
        {"nid": node_id}
    )
    selection_ids = [row[0] for row in result.fetchall()]
    
    if not selection_ids:
        return {"node_id": node_id, "node_heading": node.heading, "message": "No selections found", "tests": []}
    
    query = db.query(GeneratedTest).filter(GeneratedTest.selection_id.in_(selection_ids))
    if version is not None:
        query = query.filter(GeneratedTest.version_at_generation == version)
    tests = query.order_by(GeneratedTest.created_at.desc()).all()
    
    selections = db.query(Selection).filter(Selection.id.in_(selection_ids)).all()
    selection_map = {s.id: s.name for s in selections}
    
    return {
        "node_id": node_id,
        "node_heading": node.heading,
        "total_tests": len(tests),
        "tests": [{"id": t.id, "selection_id": t.selection_id, "selection_name": selection_map.get(t.selection_id, "Unknown"), "output": t.output, "version_at_generation": t.version_at_generation, "generated_at": t.created_at} for t in tests]
    }


@router.get("/tests/staleness/{test_id}")
async def check_test_staleness(test_id: int, db: Session = Depends(get_db)):
    test = db.query(GeneratedTest).filter(GeneratedTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail=f"Test {test_id} not found")
    return {"test_id": test_id, "selection_id": test.selection_id, "staleness": staleness_checker.check_staleness(test, db)}


# ============ VERSION ============

@router.get("/versions")
async def list_versions(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.version.desc()).all()
    return [{"version": d.version, "document_id": d.id, "filename": d.filename, "total_nodes": d.total_nodes, "created_at": d.created_at, "processed_at": d.processed_at} for d in docs]


@router.get("/versions/latest")
async def get_latest_version(db: Session = Depends(get_db)):
    doc = db.query(Document).order_by(Document.version.desc()).first()
    if not doc:
        raise HTTPException(status_code=404, detail="No versions found")
    return {"version": doc.version, "document_id": doc.id, "filename": doc.filename, "total_nodes": doc.total_nodes, "created_at": doc.created_at}


@router.get("/versions/{version}/stats")
async def get_version_stats(version: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.version == version).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Version {version} not found")
    
    total_nodes = db.query(Node).filter(Node.document_id == doc.id).count()
    top_level = db.query(Node).filter(Node.document_id == doc.id, Node.parent_id.is_(None)).count()
    max_level = db.query(func.max(Node.level)).filter(Node.document_id == doc.id).scalar() or 0
    
    changes = None
    if version > 1:
        prev_doc = db.query(Document).filter(Document.version == version - 1).first()
        if prev_doc:
            changed = db.query(Node).filter(Node.document_id == doc.id, Node.logical_id.isnot(None)).count()
            new_nodes = db.query(Node).filter(Node.document_id == doc.id, Node.logical_id.is_(None)).count()
            changes = {"total_nodes": total_nodes, "changed_nodes": changed, "new_nodes": new_nodes, "from_version": version - 1}
    
    return {"version": version, "document_id": doc.id, "filename": doc.filename, "created_at": doc.created_at, "statistics": {"total_nodes": total_nodes, "top_level_sections": top_level, "max_depth": max_level, "changes": changes}}