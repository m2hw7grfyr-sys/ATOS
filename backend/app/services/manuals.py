from __future__ import annotations

import textwrap
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MANUAL_ROOT = REPO_ROOT / "docs" / "manual"
PDF_ROOT = MANUAL_ROOT / "pdf"


@dataclass(frozen=True)
class ManualDefinition:
    key: str
    title: str
    source: Path
    pdf_name: str
    admin_only: bool = False


MANUALS = {
    "operator": ManualDefinition(
        key="operator",
        title="操作人员手册",
        source=MANUAL_ROOT / "ATOS_OPERATOR_MANUAL.md",
        pdf_name="ATOS_OPERATOR_MANUAL_v1.0.pdf",
    ),
    "administrator": ManualDefinition(
        key="administrator",
        title="管理员手册",
        source=MANUAL_ROOT / "ATOS_ADMINISTRATOR_MANUAL.md",
        pdf_name="ATOS_ADMINISTRATOR_MANUAL_v1.0.pdf",
        admin_only=True,
    ),
}


def normalize_role(role: str | None) -> str:
    value = (role or "Operator").strip().lower()
    if value in {"administrator", "admin"}:
        return "Administrator"
    if value == "reviewer":
        return "Reviewer"
    if value == "viewer":
        return "Viewer"
    return "Operator"


def can_view_manual(manual: ManualDefinition, role: str | None) -> bool:
    return not manual.admin_only or normalize_role(role) == "Administrator"


def read_manual(manual: ManualDefinition) -> str:
    return manual.source.read_text(encoding="utf-8")


def heading_id(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    while "--" in value:
        value = value.replace("--", "-")
    return value.strip("-") or "section"


def extract_toc(markdown: str) -> list[dict[str, object]]:
    toc: list[dict[str, object]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        hashes = len(stripped) - len(stripped.lstrip("#"))
        if hashes > 4:
            continue
        title = stripped[hashes:].strip()
        if title:
            toc.append({"level": hashes, "title": title, "anchor": heading_id(title)})
    return toc


def list_manuals(role: str | None) -> list[dict[str, object]]:
    items = []
    for manual in MANUALS.values():
        if not can_view_manual(manual, role):
            continue
        items.append(
            {
                "key": manual.key,
                "title": manual.title,
                "admin_only": manual.admin_only,
                "source_path": str(manual.source.relative_to(REPO_ROOT)),
                "pdf_path": str((PDF_ROOT / manual.pdf_name).relative_to(REPO_ROOT)),
            }
        )
    return items


def get_manual_payload(key: str, role: str | None) -> dict[str, object]:
    manual = MANUALS[key]
    markdown = read_manual(manual)
    return {
        "key": manual.key,
        "title": manual.title,
        "admin_only": manual.admin_only,
        "markdown": markdown,
        "toc": extract_toc(markdown),
        "source_path": str(manual.source.relative_to(REPO_ROOT)),
        "pdf_path": str((PDF_ROOT / manual.pdf_name).relative_to(REPO_ROOT)),
        "download_url": f"/help/manuals/{manual.key}/pdf",
    }


def pdf_escape_hex(text: str) -> str:
    return text.encode("utf-16-be", errors="replace").hex().upper()


def clean_markdown_for_pdf(markdown: str) -> list[str]:
    lines: list[str] = []
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            in_code = not in_code
            lines.append("代码块" if in_code else "")
            continue
        if not in_code:
            line = line.replace("#", "").replace("`", "")
            line = line.replace("|", "  ")
            line = line.replace("---", "")
            line = line.replace("**", "")
        if not line.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(line, width=74, replace_whitespace=False, drop_whitespace=False) or [""])
    return lines


def build_pdf_from_markdown(markdown: str, title: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [title, ""] + clean_markdown_for_pdf(markdown)
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= 42:
            pages.append(current)
            current = []
    if current:
        pages.append(current)

    objects: list[str] = []

    def add_object(body: str) -> int:
        objects.append(body)
        return len(objects)

    font_id = add_object("<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H >>")
    page_object_ids: list[int] = []
    content_object_ids: list[int] = []
    for page_lines in pages:
        stream_lines = ["BT", "/F1 10 Tf", "50 792 Td", "16 TL"]
        for index, line in enumerate(page_lines):
            if index:
                stream_lines.append("T*")
            stream_lines.append(f"<{pdf_escape_hex(line)}> Tj")
        stream_lines.append("ET")
        stream = "\n".join(stream_lines)
        content_id = add_object(f"<< /Length {len(stream.encode('utf-8'))} >>\nstream\n{stream}\nendstream")
        page_id = add_object("")
        content_object_ids.append(content_id)
        page_object_ids.append(page_id)

    pages_id = len(objects) + 1
    for page_id, content_id in zip(page_object_ids, content_object_ids):
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    pages_id = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>")
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    pdf = ["%PDF-1.4\n%\u00E2\u00E3\u00CF\u00D3\n"]
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1", errors="replace")) for part in pdf))
        pdf.append(f"{index} 0 obj\n{body}\nendobj\n")
    xref_offset = sum(len(part.encode("latin-1", errors="replace")) for part in pdf)
    pdf.append(f"xref\n0 {len(objects) + 1}\n")
    pdf.append("0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.append(f"{offset:010d} 00000 n \n")
    pdf.append(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n")
    output_path.write_bytes("".join(pdf).encode("latin-1", errors="replace"))
    return output_path


def build_manual_pdf(key: str) -> Path:
    manual = MANUALS[key]
    return build_pdf_from_markdown(read_manual(manual), manual.title, PDF_ROOT / manual.pdf_name)


def ensure_manual_pdf(key: str) -> Path:
    manual = MANUALS[key]
    output_path = PDF_ROOT / manual.pdf_name
    if not output_path.exists() or output_path.stat().st_mtime < manual.source.stat().st_mtime:
        return build_manual_pdf(key)
    return output_path
