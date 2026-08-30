"""
Deterministic classification eval for the scope supervisor. This does NOT use
DeepEval/RAGAS — a binary in/out-of-scope decision has one right answer, so a
plain assertion is more reliable and much cheaper than an LLM-judge metric.
Run: pytest tests/test_supervisor_eval.py -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.services.agent_service import _passes_supervisor

with open(os.path.join(os.path.dirname(__file__), "data", "supervisor_cases.json")) as f:
    CASES = json.load(f)


@pytest.mark.parametrize("case", CASES, ids=[c["message"][:30] for c in CASES])
async def test_supervisor_classification(case):
    passed = await _passes_supervisor(case["message"], context="(no prior context)")
    predicted = "IN_SCOPE" if passed else "OUT_OF_SCOPE"
    assert predicted == case["expected"], (
        f"Message: {case['message']!r} — expected {case['expected']}, got {predicted}"
    )