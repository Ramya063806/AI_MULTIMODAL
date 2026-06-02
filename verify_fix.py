import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from src.document_analyzer.knowledge import generate_layered_questions
from src.document_analyzer.models import Section

# Mock some data
text = "The year was 2024. Artificial intelligence was booming. It was a time of great change."
sections = [Section(title="Intro", content=text, page_number=1)]

try:
    print("Testing generate_layered_questions...")
    questions = generate_layered_questions(text, sections)
    print(f"Successfully generated {len(questions)} questions.")
    for q in questions:
        print(f"- {q['question']}")
    print("Verification successful!")
except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
