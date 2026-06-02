try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional during setup
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

from html import escape

import streamlit as st

from src.document_analyzer.analyzer import analyze_uploaded_document


st.set_page_config(
    page_title="Multimodal Document Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    :root {
        --app-bg: #f6f8fb;
        --panel-bg: #ffffff;
        --panel-soft: #edf4f7;
        --ink: #172026;
        --muted: #667085;
        --line: #d9e3ea;
        --accent: #096b72;
        --accent-strong: #075a60;
        --warn: #b54708;
    }

    .stApp {
        background: var(--app-bg);
        color: var(--ink);
    }

    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1280px;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label {
        color: var(--ink);
    }

    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--ink);
    }

    .hero {
        border-bottom: 1px solid var(--line);
        margin-bottom: 1rem;
        padding: 0.65rem 0 1rem;
    }

    .hero h1 {
        font-size: 2.1rem;
        line-height: 1.15;
        margin: 0 0 0.4rem;
    }

    .hero p {
        color: var(--muted);
        font-size: 1rem;
        margin: 0;
        max-width: 760px;
    }

    .metric-row {
        display: grid;
        gap: 0.75rem;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin: 0.4rem 0 1.1rem;
    }

    .metric-tile,
    .empty-state,
    .note-panel {
        background: var(--panel-bg);
        border: 1px solid var(--line);
        border-radius: 8px;
    }

    .metric-tile {
        padding: 0.9rem 1rem;
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .metric-value {
        color: var(--ink);
        font-size: 1.1rem;
        font-weight: 700;
        margin-top: 0.25rem;
        overflow-wrap: anywhere;
    }

    .empty-state {
        align-items: center;
        display: grid;
        min-height: 360px;
        padding: 2rem;
    }

    .empty-state h2 {
        font-size: 1.75rem;
        margin-bottom: 0.35rem;
    }

    .empty-state p {
        color: var(--muted);
        margin: 0;
        max-width: 620px;
    }

    .note-panel {
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .note-panel p {
        color: var(--muted);
        margin-bottom: 0;
    }

    .status-pill {
        background: var(--panel-soft);
        border: 1px solid #c9dde3;
        border-radius: 999px;
        color: var(--accent-strong);
        display: inline-flex;
        font-size: 0.8rem;
        font-weight: 700;
        gap: 0.35rem;
        line-height: 1;
        padding: 0.45rem 0.7rem;
    }

    .stButton > button {
        background: var(--accent);
        border: 1px solid var(--accent);
        border-radius: 7px;
        color: #ffffff;
        font-weight: 700;
    }

    .stButton > button:hover {
        background: var(--accent-strong);
        border-color: var(--accent-strong);
        color: #ffffff;
    }

    div[data-baseweb="tab-list"] {
        gap: 0.35rem;
    }

    button[data-baseweb="tab"] {
        border-radius: 7px;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }

    @media (max-width: 760px) {
        .hero h1 {
            font-size: 1.65rem;
        }

        .metric-row {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_metric(label: str, value: object) -> str:
    return (
        '<div class="metric-tile">'
        f'<div class="metric-label">{escape(str(label))}</div>'
        f'<div class="metric-value">{escape(str(value))}</div>'
        "</div>"
    )


def render_sidebar_metadata(analysis) -> None:
    st.sidebar.markdown("### Document")
    st.sidebar.write(f"**File:** {analysis.file_name}")
    st.sidebar.write(f"**Type:** {analysis.document_type}")
    st.sidebar.write(f"**Pages:** {analysis.page_count}")
    st.sidebar.divider()
    st.sidebar.markdown(
        '<span class="status-pill">Analysis ready</span>',
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <div class="hero">
        <h1>Multimodal Document Analyzer</h1>
        <p>Turn PDFs, scanned pages, and images into structured summaries, tables,
        study questions, concept links, and prerequisite checks.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Upload")
    uploaded_file = st.file_uploader(
        "Choose a PDF or image",
        type=["pdf", "png", "jpg", "jpeg", "tif", "tiff"],
        accept_multiple_files=False,
    )
    st.caption("Supported: PDF, PNG, JPG, JPEG, TIF, TIFF")

if uploaded_file is None:
    st.markdown(
        """
        <div class="empty-state">
            <div>
                <span class="status-pill">Waiting for document</span>
                <h2>Upload a file to begin analysis.</h2>
                <p>The app will extract readable text, detect tables and form-like
                fields, describe visual content, and build study aids from the
                uploaded material.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

with st.spinner("Reading and analyzing the uploaded document..."):
    analysis = analyze_uploaded_document(uploaded_file)

if analysis.error:
    st.error(analysis.error)
    st.stop()

render_sidebar_metadata(analysis)

st.markdown(
    '<div class="metric-row">'
    + render_metric("File", analysis.file_name)
    + render_metric("Document Type", analysis.document_type)
    + render_metric("Pages", analysis.page_count)
    + "</div>",
    unsafe_allow_html=True,
)

summary_col, navigator_col = st.columns([1.15, 0.85], gap="large")

with summary_col:
    st.subheader("Document Summary")
    st.markdown(
        f"""
        <div class="note-panel">
            <p>{escape(analysis.summary or "No summary could be generated from the uploaded content.")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with navigator_col:
    st.subheader("Smart Section Navigator")
    if analysis.sections:
        section_titles = [section.title for section in analysis.sections]
        selected_title = st.selectbox("Jump to section", section_titles, index=0)
        selected_section = next(
            section for section in analysis.sections if section.title == selected_title
        )
        st.markdown(f"**{selected_section.title}**")
        st.write(selected_section.content or "No content extracted for this section.")
    else:
        st.info("No logical sections were detected in this document.")

st.divider()
st.subheader("Analysis Workspace")

(
    text_tab,
    table_tab,
    visual_tab,
    form_tab,
    knowledge_tab,
    concept_tab,
    socratic_tab,
    radar_tab,
) = st.tabs(
    [
        "Text",
        "Tables",
        "Visuals",
        "Forms",
        "Knowledge",
        "Concepts",
        "Socratic",
        "Prerequisites",
    ]
)

with text_tab:
    st.text_area(
        "Extracted text",
        value=analysis.extracted_text or "No text could be extracted.",
        height=360,
    )

with table_tab:
    if analysis.tables:
        for index, table in enumerate(analysis.tables, start=1):
            st.markdown(f"#### Table {index}")
            st.dataframe(table, use_container_width=True)
    else:
        st.info("No tables were detected.")

with visual_tab:
    if analysis.visual_descriptions:
        for description in analysis.visual_descriptions:
            st.markdown(f"- {description}")
    else:
        st.info("No visual elements were detected or OCR text was unavailable.")

with form_tab:
    if analysis.form_fields:
        st.dataframe(analysis.form_fields, use_container_width=True)
    else:
        st.info("No form-like fields were detected.")

with knowledge_tab:
    st.markdown("#### Socratic Knowledge Probe")
    if not analysis.knowledge_questions:
        st.info("No knowledge questions could be generated for this document.")
    else:
        answers = []
        for i, question in enumerate(analysis.knowledge_questions):
            st.markdown(f"**Q{i + 1}. {question['question']}**")
            answer = st.text_area(f"Your answer {i + 1}", key=f"answer_{i}", height=120)
            answers.append(answer)

        if st.button("Evaluate my answers"):
            try:
                from src.document_analyzer.knowledge import evaluate_answers

                results = evaluate_answers(
                    answers, analysis.knowledge_questions, analysis.extracted_text
                )
            except Exception as exc:
                st.error(f"Failed to evaluate answers: {exc}")
                results = []

            rows = []
            for index, result in enumerate(results):
                rows.append(
                    {
                        "question": analysis.knowledge_questions[index]["question"],
                        "status": result.get("status", "gap"),
                        "score": round(result.get("score", 0.0), 2),
                        "matched_snippets": " ".join(result.get("matched", [])[:3]),
                    }
                )
            st.dataframe(rows, use_container_width=True)

with concept_tab:
    st.markdown("#### Concept Relationship Web")
    if not analysis.concept_nodes:
        st.info("No concepts detected in this document.")
    else:
        concepts = [node["label"] for node in analysis.concept_nodes]
        selected = st.selectbox("Select a concept to inspect", concepts)
        st.markdown("**Top related concepts**")
        related = [
            edge
            for edge in analysis.concept_edges
            if edge["source"] == selected or edge["target"] == selected
        ]
        related_sorted = sorted(related, key=lambda item: item["weight"], reverse=True)
        for relationship in related_sorted[:10]:
            st.write(
                f"{relationship['source']} - {relationship['target']} "
                f"(co-occurs in {relationship['weight']} sections)"
            )

        occurrences = [
            section
            for section in analysis.sections
            if selected.lower() in section.content.lower()
        ]
        if occurrences:
            st.markdown("**Occurrences**")
            for occurrence in occurrences:
                excerpt = occurrence.content[:200]
                st.markdown(
                    f"- **{occurrence.title}** "
                    f"(page {occurrence.page_number}): {excerpt}..."
                )
        else:
            st.info("No section occurrences found for this concept.")

with socratic_tab:
    st.markdown("#### Socratic Study Companion")
    if not analysis.layered_questions:
        st.info("No Socratic questions could be generated for this document.")
    else:
        layers = {"recall": [], "comprehension": [], "analysis": []}
        for question in analysis.layered_questions:
            layers.setdefault(question["layer"], []).append(question)

        engagement = {section.title: False for section in analysis.sections}

        for layer_name in ["recall", "comprehension", "analysis"]:
            st.markdown(f"**{layer_name.title()} Questions**")
            for question in layers.get(layer_name, [])[:8]:
                st.markdown(f"**{question['id']}. {question['question']}**")
                answer_col, action_col = st.columns([3, 1])
                with answer_col:
                    answer = st.text_area(
                        f"Answer {question['id']}",
                        key=f"s_ans_{question['id']}",
                        height=100,
                    )
                with action_col:
                    if st.button("Hint", key=f"hint_{question['id']}"):
                        st.info(question.get("hint", "No hint available."))
                    if st.button("Answer", key=f"ans_{question['id']}"):
                        st.success(question.get("model_answer", "No model answer available."))

                if answer and answer.strip():
                    model_answer = (question.get("model_answer") or "").strip()
                    for section in analysis.sections:
                        if model_answer and model_answer[:30].lower() in section.content.lower():
                            engagement[section.title] = True

        total_questions = len(analysis.layered_questions)
        answered = sum(
            1
            for question in analysis.layered_questions
            if st.session_state.get(f"s_ans_{question['id']}", "").strip()
        )
        readiness = int((answered / total_questions) * 100) if total_questions else 0
        st.metric("Readiness Score", f"{readiness} / 100")

        mastery_rows = [
            {"section": section.title, "engaged": engagement.get(section.title, False)}
            for section in analysis.sections
        ]
        st.dataframe(mastery_rows, use_container_width=True)

with radar_tab:
    st.markdown("#### Knowledge Gap Radar")
    if not analysis.prerequisite_gaps:
        st.info("No prerequisite concepts detected in this document.")
    else:
        for gap in analysis.prerequisite_gaps:
            st.markdown(f"- **{gap['concept']}** - {gap['difficulty']}")
            with st.expander("Details"):
                st.write(gap.get("micro_explanation"))
                st.write("**Why assumed:** " + gap.get("why", ""))
                st.write("**Suggested search:** " + gap.get("suggested_query", ""))
