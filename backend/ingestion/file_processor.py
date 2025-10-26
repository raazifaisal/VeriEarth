import csv
from typing import Iterable, Tuple, List, Dict, Any, IO


def sniff_csv(sample: bytes) -> Tuple[str, str]:
    try:
        dialect = csv.Sniffer().sniff(sample.decode("utf-8", errors="ignore"))
        return (dialect.delimiter, "utf-8")
    except Exception:
        return (",", "utf-8")


def read_csv(file_obj, limit_preview_rows: int = 20) -> Tuple[List[str], List[Dict[str, Any]]]:
    # Handle both file-like objects and bytes
    if hasattr(file_obj, 'read'):
        # File-like object
        sample = file_obj.read(4096)
        delimiter, encoding = sniff_csv(sample)
        file_obj.seek(0)
        text_stream = (chunk.decode(encoding, errors="ignore") for chunk in [file_obj.read()])
        content = "".join(text_stream)
    else:
        # Bytes object
        sample = file_obj[:4096]
        delimiter, encoding = sniff_csv(sample)
        content = file_obj.decode(encoding, errors="ignore")
    
    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    headers = reader.fieldnames or []
    rows: List[Dict[str, Any]] = []
    for idx, row in enumerate(reader):
        rows.append(row)
        if idx + 1 >= limit_preview_rows:
            break
    return headers, rows


