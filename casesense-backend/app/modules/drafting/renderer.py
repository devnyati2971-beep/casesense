"""Draft export rendering — Blueprint §D21.

Primary renderer is WeasyPrint (installed in the worker image). In environments
where WeasyPrint (or its system libs) is unavailable we fall back to a minimal
deterministic PDF writer so the export pipeline never hard-fails in dev.
"""

from __future__ import annotations

import zlib
from typing import List, Dict

from app.core.logging import get_logger

logger = get_logger(__name__)


def _html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_html(title: str, sections_data: List[Dict]) -> str:
    parts = [f"<h1>{_html_escape(title)}</h1>"]
    for sec in sections_data:
        if sec.get("heading"):
            parts.append(f"<h2>{_html_escape(str(sec['heading']))}</h2>")
        if sec.get("body"):
            body_safe = _html_escape(str(sec["body"])).replace("\n", "<br>")
            parts.append(f"<p>{body_safe}</p>")

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{_html_escape(title)}</title>
  <style>
    @page {{ size: A4; margin: 1in; }}
    body {{ font-family: serif; font-size: 12pt; line-height: 1.6; }}
    h1 {{ text-align: center; font-size: 16pt; text-transform: uppercase; margin-bottom: 30pt; }}
    h2 {{ font-size: 14pt; margin-top: 24pt; margin-bottom: 12pt; }}
    p {{ margin-bottom: 12pt; text-align: justify; }}
  </style>
</head>
<body>
  {''.join(parts)}
</body>
</html>"""


def _render_fallback_pdf(title: str, sections_data: List[Dict]) -> bytes:
    """Minimal PDF writer — text lines + newline-delimited content."""
    lines: list[str] = [title, ""]
    for sec in sections_data:
        if sec.get("heading"):
            lines.append(f"# {sec['heading']}")
        if sec.get("body"):
            lines.append(str(sec["body"]))
        lines.append("")

    text = "\n".join(lines)
    stream = b"BT\n/F1 11 Tf\n14 TL\n16 TL\n" + b""
    # Escape PDF text
    esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length 0 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    # Content stream with simple text
    content = (
        "BT /F1 12 Tf 56 800 Td 14 TL\n"
        + "\n".join(f"({esc_line}) Tj T*" for esc_line in esc.split("\n"))
        + " ET"
    ).encode("latin-1", errors="replace")
    objects[3] = b"<< /Length " + str(len(content)).encode() + b" >>"
    objects.append(content)

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(pdf.tell())
        pdf += b"%d 0 obj\n" % (len(offsets))
        pdf += obj + b"\nendobj\n"
    xref_pos = pdf.tell()
    pdf += b"xref\n0 %d\n" % (len(objects) + 1)
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += b"%010d 00000 n \n" % off
    pdf += (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
        % (len(objects) + 1, xref_pos)
    )
    return pdf


def render_draft_to_pdf(title: str, sections_data: List[Dict]) -> bytes:
    """Render draft version to PDF bytes (§D21)."""
    try:
        import weasyprint  # type: ignore

        return weasyprint.HTML(string=_build_html(title, sections_data)).write_pdf()
    except Exception as exc:  # pragma: no cover - depends on environment
        logger.warning("WeasyPrint unavailable; using fallback PDF writer", error=str(exc))
        return _render_fallback_pdf(title, sections_data)