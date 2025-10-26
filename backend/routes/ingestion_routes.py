from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from ingestion.file_processor import read_csv
from ingestion.mappings import guess_mapping, CANONICAL_HEADERS
from ingestion.validators import VALIDATORS
from ingestion.transformers import normalize_facility, normalize_route
from ingestion.loader import load_facilities, load_routes, load_shipments
from db.database import get_db
from db.neo4j_service import Neo4jService


router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/upload")
async def upload(entity: str = Form(...), org_id: str = Form(...), file: UploadFile = File(...)):
    if entity not in CANONICAL_HEADERS:
        raise HTTPException(status_code=400, detail="Unsupported entity")
    headers, rows = read_csv(await file.read())  # type: ignore[arg-type]
    mapping = guess_mapping(entity, headers)
    return {
        "entity": entity,
        "organization_id": org_id,
        "original_headers": headers,
        "mapping": mapping,
        "sample": rows[:5],
    }


@router.post("/preview")
async def preview(entity: str = Form(...), file: UploadFile = File(...)):
    headers, rows = read_csv(await file.read())  # type: ignore[arg-type]
    mapping = guess_mapping(entity, headers)
    required = CANONICAL_HEADERS.get(entity, [])
    present = set(mapping.values())
    missing = [h for h in required if h in required and h not in present]
    return {"headers": headers, "mapping": mapping, "missing": missing, "sample": rows[:5]}


@router.post("/import")
async def import_file(
    entity: str = Form(...),
    org_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    raw_bytes = await file.read()
    headers, rows = read_csv(raw_bytes)  # type: ignore[arg-type]
    mapping = guess_mapping(entity, headers)

    normalized_rows = []
    for r in rows:
        nr: Dict[str, Any] = {}
        for src, dest in mapping.items():
            nr[dest] = r.get(src)
        if entity == "facilities":
            nr = normalize_facility(nr)
        if entity in ("routes", "shipments"):
            nr = normalize_route(nr)
        normalized_rows.append(nr)

    errors = []
    validator = VALIDATORS.get(entity)
    if validator:
        for i, nr in enumerate(normalized_rows):
            issues = validator(nr)
            if issues:
                errors.append({"row": i + 1, "errors": issues})

    if errors:
        return {"status": "errors", "errors": errors[:50], "errors_count": len(errors)}

    # Neo4j service instance creation (from env)
    neo4j = Neo4jService(
        uri="bolt://neo4j:7687",  # Use container name in Docker environment
        user="neo4j",
        password="12345678",
    )

    created = 0
    if entity == "facilities":
        created = load_facilities(normalized_rows, db, neo4j, org_id)
    elif entity == "routes":
        created = load_routes(normalized_rows, db, neo4j, org_id)
    elif entity == "shipments":
        created = load_shipments(normalized_rows, db, neo4j, org_id)
    else:
        raise HTTPException(status_code=400, detail="Entity import not yet implemented")

    neo4j.close()
    return {"status": "ok", "created": created}


