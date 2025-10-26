"""Ingestion package for ERP file imports (SAP/Oracle/Dynamics).

Modules:
- file_processor: CSV/XLSX loading and basic sniffing
- mappings: ERP header detection and mapping application
- validators: Per-entity validation rules
- transformers: Normalization helpers (dates, enums, geo)
- loader: Dual-write to PostgreSQL and Neo4j
- models: In-memory ingestion job models and enums
"""


