from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class Section:
    title: str
    content: str
    page_number: int | None = None


@dataclass
class DocumentAnalysis:
    file_name: str
    document_type: str
    page_count: int
    summary: str
    extracted_text: str
    tables: list[pd.DataFrame] = field(default_factory=list)
    visual_descriptions: list[str] = field(default_factory=list)
    form_fields: list[dict[str, str]] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    # Knowledge/learning features
    knowledge_questions: list[dict] = field(default_factory=list)
    knowledge_map: list[dict] = field(default_factory=list)
    concept_nodes: list[dict] = field(default_factory=list)
    concept_edges: list[dict] = field(default_factory=list)
    # Socratic Study Companion
    layered_questions: list[dict] = field(default_factory=list)
    readiness_score: float | None = None
    topic_mastery_map: list[dict] = field(default_factory=list)
    # Knowledge Gap Radar
    prerequisite_gaps: list[dict] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "document_type": self.document_type,
            "page_count": self.page_count,
            "summary": self.summary,
            "extracted_text": self.extracted_text,
            "tables": [table.fillna("").to_dict(orient="records") for table in self.tables],
            "visual_descriptions": self.visual_descriptions,
            "form_fields": self.form_fields,
            "sections": [
                {
                    "title": section.title,
                    "content": section.content,
                    "page_number": section.page_number,
                }
                for section in self.sections
            ],
            "error": self.error,
        }
