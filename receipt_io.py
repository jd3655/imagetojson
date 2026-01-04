"""Utilities for handling receipt ZIP archives and outputs."""

from __future__ import annotations

import base64
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple


PNG_EXTENSIONS = {".png", ".PNG"}


@dataclass
class ReceiptGroup:
    """Represents a receipt folder and its ordered image pages."""

    name: str
    pages: List[Path]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def sanitize_filename(name: str) -> str:
    """Remove path separators to keep receipt names filesystem-safe."""

    unsafe = {"/", "\\"}
    for char in unsafe:
        name = name.replace(char, "_")
    return name.strip()


def safe_extract_zip(zip_path: str, dest_dir: str) -> None:
    """Safely extract a ZIP file to ``dest_dir`` while preventing Zip Slip."""

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            extracted_path = Path(dest_dir, member.filename)
            normalized = extracted_path.resolve()
            if not str(normalized).startswith(str(Path(dest_dir).resolve())):
                raise ValueError(f"Unsafe path detected in zip: {member.filename}")
        zf.extractall(dest_dir)


def _page_sort_key(path: Path) -> Tuple[int, str]:
    """Sort pages by explicit page number when available, otherwise by name."""

    match = re.search(r"page[_-]?(\d+)", path.stem, re.IGNORECASE)
    if match:
        return int(match.group(1)), path.name
    digits = re.findall(r"(\d+)", path.stem)
    if digits:
        return int(digits[-1]), path.name
    return float("inf"), path.name


def discover_receipts(root_dir: str) -> List[ReceiptGroup]:
    """Find top-level directories in ``root_dir`` and collect PNG pages."""

    receipts: List[ReceiptGroup] = []
    root = Path(root_dir)
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            pages = [
                p
                for p in sorted(entry.iterdir(), key=_page_sort_key)
                if p.is_file() and p.suffix in PNG_EXTENSIONS
            ]
            if pages:
                receipts.append(ReceiptGroup(name=entry.name, pages=pages))
    return receipts


def encode_image_to_data_url(path: Path) -> str:
    """Convert a PNG file to a base64 data URL for llama.cpp vision calls."""

    with path.open("rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def prepare_workdir() -> str:
    """Create a temporary working directory and return its path."""

    return tempfile.mkdtemp(prefix="receipts_")


def ensure_directory(path: str | Path) -> Path:
    """Create the directory if needed and return it as a Path."""

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_output(receipt_name: str, content: str, output_format: str, output_dir: str) -> Path:
    """Write content to ``<receipt_name>.<ext>`` inside ``output_dir``."""

    ext = "md" if output_format == "markdown" else "json"
    safe_name = sanitize_filename(receipt_name)
    ensure_directory(output_dir)
    path = Path(output_dir, f"{safe_name}.{ext}")
    path.write_text(content, encoding="utf-8")
    return path


def build_outputs_zip(output_dir: str, zip_path: str) -> Path:
    """Zip all files inside ``output_dir`` for download."""

    output_dir_path = Path(output_dir)
    ensure_directory(output_dir_path)
    zip_file = Path(zip_path)
    with zipfile.ZipFile(zip_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(output_dir_path.glob("*")):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.name)
    return zip_file


def list_receipt_table(receipts: Iterable[ReceiptGroup]) -> List[List[str | int]]:
    """Return a simple table representation for Gradio display."""

    return [[receipt.name, receipt.page_count] for receipt in receipts]
