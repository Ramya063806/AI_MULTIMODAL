from __future__ import annotations

import base64
import io
import os
import re
from pathlib import Path
from typing import Iterable

import fitz
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image

from .models import DocumentAnalysis, Section
from .knowledge import (
    extract_concepts,
    build_concept_web,
    generate_socratic_questions,
    generate_layered_questions,
    detect_prerequisites,
)
from .utils import _shorten_text



HEADING_PATTERNS = (
    re.compile(r"^\d+(?:\.\d+)*\s+[A-Z].+"),
    re.compile(r"^(?:[A-Z][A-Za-z0-9\- ]{2,})$"),
)


def analyze_uploaded_document(uploaded_file) -> DocumentAnalysis:
    file_name = uploaded_file.name
    file_bytes = uploaded_file.getvalue()
    suffix = Path(file_name).suffix.lower()

    if not file_bytes:
        return DocumentAnalysis(
            file_name=file_name,
            document_type="unknown",
            page_count=0,
            summary="",
            extracted_text="",
            error="The uploaded file is empty.",
        )

    try:
        if suffix == ".pdf":
            return _analyze_pdf(file_name, file_bytes)
        if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return _analyze_image(file_name, file_bytes)
        return DocumentAnalysis(
            file_name=file_name,
            document_type="unknown",
            page_count=0,
            summary="",
            extracted_text="",
            error="Unsupported file type. Please upload a PDF or image.",
        )
    except Exception as exc:  # noqa: BLE001
        return DocumentAnalysis(
            file_name=file_name,
            document_type="unknown",
            page_count=0,
            summary="",
            extracted_text="",
            error=f"Failed to analyze document: {exc}",
        )


def _analyze_pdf(file_name: str, file_bytes: bytes) -> DocumentAnalysis:
    pdf_data = io.BytesIO(file_bytes)
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_count = len(doc)

    text_pages: list[str] = []
    visual_descriptions: list[str] = []
    tables: list[pd.DataFrame] = []
    sections: list[Section] = []
    form_fields: list[dict[str, str]] = []

    with pdfplumber.open(pdf_data) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            page_text = _extract_pdf_page_text(page)
            if page_text:
                text_pages.append(page_text)
                sections.extend(_extract_sections_from_text(page_text, page_index))
                form_fields.extend(_extract_form_fields_from_text(page_text, page_index))

            extracted_tables = page.extract_tables() or []
            for table in extracted_tables:
                table_frame = _table_to_dataframe(table)
                if not table_frame.empty:
                    tables.append(table_frame)

    for page_index in range(page_count):
        page = doc[page_index]
        image_descriptions = _describe_page_images(page, page_index + 1)
        visual_descriptions.extend(image_descriptions)

    extracted_text = "\n\n".join(text_pages).strip()
    summary = _build_summary(extracted_text)
    if page_count:
        try:
            first_page_pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            groq_summary = _generate_groq_multimodal_summary(
                file_name=file_name,
                extracted_text=extracted_text,
                image_bytes=first_page_pixmap.tobytes("png"),
                image_mime="image/png",
                document_type="PDF",
                page_count=page_count,
            )
            if groq_summary:
                summary = groq_summary
        except Exception:  # noqa: BLE001
            pass

    # Knowledge features (lightweight heuristics)
    concepts = extract_concepts(extracted_text, top_k=40)
    nodes, edges = build_concept_web(concepts, [p for p in text_pages])
    questions = generate_socratic_questions(extracted_text, concepts, num_questions=4)
    layered = generate_layered_questions(extracted_text, _deduplicate_sections(sections), max_per_layer=4)
    prerequisites = detect_prerequisites(extracted_text, concepts, _deduplicate_sections(sections))

    return DocumentAnalysis(
        file_name=file_name,
        document_type="PDF",
        page_count=page_count,
        summary=summary,
        extracted_text=extracted_text,
        tables=tables,
        visual_descriptions=visual_descriptions,
        form_fields=form_fields,
        sections=_deduplicate_sections(sections),
        knowledge_questions=questions,
        layered_questions=layered,
        concept_nodes=nodes,
        concept_edges=edges,
        prerequisite_gaps=prerequisites,
    )


def _analyze_image(file_name: str, file_bytes: bytes) -> DocumentAnalysis:
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    extracted_text = pytesseract.image_to_string(image).strip()
    summary = _build_summary(extracted_text)
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    groq_summary = _generate_groq_multimodal_summary(
        file_name=file_name,
        extracted_text=extracted_text,
        image_bytes=image_buffer.getvalue(),
        image_mime="image/png",
        document_type="Image",
        page_count=1,
    )
    if groq_summary:
        summary = groq_summary
    sections = _extract_sections_from_text(extracted_text, 1)
    form_fields = _extract_form_fields_from_text(extracted_text, 1)
    visual_descriptions = [
        f"Image detected with size {image.width}x{image.height}. OCR text was used to inspect visible content."
    ]

    # Knowledge features for images
    concepts = extract_concepts(extracted_text, top_k=40)
    nodes, edges = build_concept_web(concepts, [s.content for s in sections])
    questions = generate_socratic_questions(extracted_text, concepts, num_questions=4)
    layered = generate_layered_questions(extracted_text, sections, max_per_layer=4)
    prerequisites = detect_prerequisites(extracted_text, concepts, sections)

    return DocumentAnalysis(
        file_name=file_name,
        document_type="Image",
        page_count=1,
        summary=summary,
        extracted_text=extracted_text,
        tables=[],
        visual_descriptions=visual_descriptions,
        form_fields=form_fields,
        sections=_deduplicate_sections(sections),
        knowledge_questions=questions,
        layered_questions=layered,
        concept_nodes=nodes,
        concept_edges=edges,
        prerequisite_gaps=prerequisites,
    )


def _extract_pdf_page_text(page) -> str:
    text = page.extract_text() or ""
    return text.strip()


def _extract_sections_from_text(text: str, page_number: int) -> list[Section]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections: list[Section] = []
    current_title = "General Content"
    current_lines: list[str] = []

    def flush_section() -> None:
        if current_lines:
            sections.append(
                Section(
                    title=current_title,
                    content=" ".join(current_lines).strip(),
                    page_number=page_number,
                )
            )

    for line in lines:
        if _looks_like_heading(line):
            flush_section()
            current_title = line
            current_lines = []
            continue
        current_lines.append(line)

    flush_section()
    return sections


def _extract_form_fields_from_text(text: str, page_number: int) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        label = label.strip(" -\t")
        value = value.strip()
        if len(label) < 2:
            continue
        fields.append(
            {
                "page": str(page_number),
                "label": label,
                "value": value,
            }
        )
    return fields


def _describe_page_images(page, page_number: int) -> list[str]:
    descriptions: list[str] = []
    for image_index, image_ref in enumerate(page.get_images(full=True), start=1):
        xref = image_ref[0]
        extracted = page.parent.extract_image(xref)
        image_bytes = extracted["image"]
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            ocr_text = pytesseract.image_to_string(pil_image).strip()
            if ocr_text:
                text_preview = re.sub(r"\s+", " ", ocr_text).strip()
                if len(text_preview) > 160:
                    text_preview = text_preview[:157].rstrip() + "..."
            else:
                text_preview = "No readable text found in the image area."
            descriptions.append(
                f"Page {page_number}, image {image_index}: {pil_image.width}x{pil_image.height}. {text_preview}"
            )
        except Exception:  # noqa: BLE001
            descriptions.append(f"Page {page_number}, image {image_index}: visual image block detected.")
    return descriptions


def _table_to_dataframe(table: list[list[str | None]]) -> pd.DataFrame:
    cleaned_rows = [
        [cell.strip() if isinstance(cell, str) else "" for cell in row]
        for row in table
        if any(cell not in (None, "") for cell in row)
    ]
    if not cleaned_rows:
        return pd.DataFrame()

    header = cleaned_rows[0]
    rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else []
    if rows and len(header) == len(rows[0]) and any(header):
        return pd.DataFrame(rows, columns=header)

    return pd.DataFrame(cleaned_rows)


def _build_summary(text: str, max_sentences: int = 3) -> str:
    cleaned_text = re.sub(r"\s+", " ", text).strip()
    if not cleaned_text:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", cleaned_text)
    selected_sentences: list[str] = []
    for sentence in sentences:
        if sentence:
            selected_sentences.append(sentence)
        if len(selected_sentences) >= max_sentences:
            break
    return " ".join(selected_sentences)


def _looks_like_heading(line: str) -> bool:
    if len(line) > 80:
        return False
    if any(pattern.match(line) for pattern in HEADING_PATTERNS):
        return True
    if line.isupper() and len(line.split()) <= 8:
        return True
    return False


def _generate_groq_multimodal_summary(
    file_name: str,
    extracted_text: str,
    image_bytes: bytes,
    image_mime: str,
    document_type: str,
    page_count: int,
) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from groq import Groq
    except ImportError:
        return None

    model = os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview").strip()
    if not model:
        model = "llama-3.2-90b-vision-preview"

    client = Groq(api_key=api_key)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        f"Analyze this {document_type.lower()} named {file_name}. It has {page_count} page(s). "
        "Use both the visual content and any OCR text to produce a concise, beginner-friendly summary. "
        "Include the main topic, notable visual cues, and any important entities or actions. "
        "Keep the result to 4 short sentences max."
    )
    if extracted_text.strip():
        prompt += f"\n\nOCR text:\n{_shorten_text(extracted_text, 1800)}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{image_b64}",
                            "detail": "auto",
                        },
                    },
                ],
            }
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content if response.choices else None
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str):
        return None
    content = content.strip()
    return content or None


def _deduplicate_sections(sections: Iterable[Section]) -> list[Section]:
    unique: list[Section] = []
    seen: set[tuple[str, str, int | None]] = set()
    for section in sections:
        key = (section.title, section.content, section.page_number)
        if key in seen:
            continue
        seen.add(key)
        unique.append(section)
    return unique
