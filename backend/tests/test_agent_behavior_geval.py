"""
DeepEval GEval suite for open-ended agent behavior that has no single correct string to
assert against: disambiguation quality, retroactive execution, refusal tone, and identity
protection. An LLM judge scores the actual agent response against a written rubric per case.

Unlike test_supervisor_eval.py and test_document_classifier_eval.py (which check discrete
classifier outputs), this exercises the FULL agent — including tool calls — through
stream_agent_reply, so each case runs the real conversational pipeline, not a stubbed piece
of it.

Kept deliberately small (see geval_cases.json) to fit a free-tier Groq daily token budget
after test_rag_retrieval_eval.py already spends part of it.

Run: pytest tests/test_agent_behavior_geval.py -v -s
"""
import json
import os
import sys
import uuid

import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase
try:
    from deepeval.test_case import SingleTurnParams as LLMTestCaseParams
except ImportError:
    from deepeval.test_case import LLMTestCaseParams

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.services.agent_service import stream_agent_reply

EVAL_USER_ID = "eval_test_user_do_not_use_for_real_data"

with open(os.path.join(os.path.dirname(__file__), "data", "geval_cases.json")) as f:
    CASES = json.load(f)

behavior_metric = GEval(
    name="Agent Behavior Correctness",
    criteria="Evaluate whether the assistant's response satisfies the specific behavioral requirement described.",
    evaluation_params=[
        getattr(LLMTestCaseParams, "INPUT"),
        getattr(LLMTestCaseParams, "ACTUAL_OUTPUT"),
    ],
    threshold=0.6,
)


async def _get_agent_response(message: str) -> str:
    """Run one message through the real agent pipeline in a fresh, isolated thread per case."""
    thread_id = f"geval_{uuid.uuid4()}"
    full_reply = ""
    async for event in stream_agent_reply(
        EVAL_USER_ID,
        EVAL_USER_ID,   # user_id — use the same synthetic ID for tests
        thread_id,
        message,
    ):
        if event.get("type") == "token":
            full_reply += event.get("token", "")
    return full_reply


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
async def test_agent_behavior(case):
    actual_output = await _get_agent_response(case["input"])

    test_case = LLMTestCase(
        input=f"{case['input']}\n\nRequirement: {case['criteria']}",
        actual_output=actual_output,
    )

    print(f"\n--- {case['name']} ---\nAgent said: {actual_output[:300]}")

    assert_test(test_case, [behavior_metric])