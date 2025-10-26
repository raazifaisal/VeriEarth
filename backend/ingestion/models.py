from enum import Enum
from typing import Dict, List, Optional, Any


class IngestionStatus(str, Enum):
    PENDING = "pending"
    PREVIEWED = "previewed"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob:
    def __init__(self, entity: str, organization_id: str):
        self.entity = entity
        self.organization_id = organization_id
        self.status: IngestionStatus = IngestionStatus.PENDING
        self.original_headers: List[str] = []
        self.mapped_headers: List[str] = []
        self.header_mapping: Dict[str, str] = {}
        self.sample_rows: List[Dict[str, Any]] = []
        self.errors_path: Optional[str] = None
        self.summary: Dict[str, Any] = {}


