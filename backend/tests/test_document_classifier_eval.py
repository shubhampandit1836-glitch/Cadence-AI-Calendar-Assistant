"""
Deterministic eval for the document relevance classifier used during PDF upload.
Run: pytest tests/test_document_classifier_eval.py -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.services.rag_service import validate_document_relevance

with open(os.path.join(os.path.dirname(__file__), "data", "document_classifier_cases.json")) as f:
    CASES = json.load(f)


@pytest.mark.parametrize("case", CASES, ids=[c["text"][:30] for c in CASES])
async def test_document_relevance_classification(case):
    result = await validate_document_relevance(case["text"])
    predicted = bool(result.get("is_relevant", False))
    assert predicted == case["expected_relevant"], (
        f"Text: {case['text'][:60]!r}... — expected relevant={case['expected_relevant']}, "
        f"got {predicted} (doc_type={result.get('doc_type')}, reason={result.get('rejection_reason')})"
    )