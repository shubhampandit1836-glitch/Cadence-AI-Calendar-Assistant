"""
RAGAS evaluation of the RAG retrieval pipeline: does search_uploaded_documents pull the
right chunks (context precision/recall), and is the synthesized answer actually grounded
in those chunks (faithfulness)?

Requires: python tests/seed_eval_documents.py has already been run successfully.
Uses Groq (the existing primary model) as judge LLM and fastembed as judge embeddings —
never calls a paid API, same as the rest of the app.

Deliberately scaled down to fit a free-tier Groq daily token budget: 5 questions and 2
metrics (faithfulness, context_precision) rather than the full 10/3. context_recall is
the most token-hungry of the three (it needs an extra reference-comparison pass per
question) and is the first thing to drop if budget is tight — faithfulness and precision
already cover "is retrieval finding the right stuff" and "is the answer grounded in it".
max_workers is capped low so requests are spread out instead of firing in a burst, which
reduces how much a single retry storm can eat into the daily cap.

Run: pytest tests/test_rag_retrieval_eval.py -v -s
(the -s is important — without it pytest hides the printed score table)
"""
import json
import os
import sys
from typing import Any, cast

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, context_precision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from langchain_community.embeddings import FastEmbedEmbeddings

from src.config.llm_config import get_llm_model
from src.services.rag_service import search_rag_context

EVAL_USER_ID = "eval_test_user_do_not_use_for_real_data"

# Keep the full golden set in the JSON file for later; only spend budget on the first
# N here. Raise this once you're on a paid tier or want a bigger nightly run.
MAX_CASES = 5

with open(os.path.join(os.path.dirname(__file__), "data", "rag_eval_cases.json")) as f:
    CASES = json.load(f)[:MAX_CASES]

_ANSWER_PROMPT = """Answer the question using ONLY the context below. If the context does not
contain the answer, say you don't know. Be concise — one or two sentences.

Context:
{context}

Question: {question}
Answer:"""


async def _build_ragas_dataset():
    model = get_llm_model(temperature=0.0)
    questions, contexts_list, answers, ground_truths = [], [], [], []

    for case in CASES:
        results = await search_rag_context(EVAL_USER_ID, query=case["question"], top_k=5)
        contexts = [r["content"] for r in results] if results else []
        context_block = "\n\n".join(contexts) if contexts else "(no context found)"

        response = await model.ainvoke(
            [{"role": "system", "content": _ANSWER_PROMPT.format(context=context_block, question=case["question"])}]
        )
        answer = str(response.content).strip()

        questions.append(case["question"])
        contexts_list.append(contexts if contexts else ["(no context found)"])
        answers.append(answer)
        ground_truths.append(case["ground_truth"])

    return Dataset.from_dict({
        "question": questions,
        "contexts": contexts_list,
        "answer": answers,
        "ground_truth": ground_truths,
    })


@pytest.mark.asyncio
async def test_rag_retrieval_quality():
    dataset = await _build_ragas_dataset()

    judge_llm = LangchainLLMWrapper(get_llm_model(temperature=0.0))
    judge_embeddings = LangchainEmbeddingsWrapper(FastEmbedEmbeddings())

    result = evaluate(
        dataset,
        metrics=[faithfulness, context_precision],
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=RunConfig(max_workers=2, timeout=180),
    )

    # ragas 0.3.x renames columns internally on output: question->user_input,
    # contexts->retrieved_contexts, answer->response, ground_truth->reference —
    # even though it still accepts the old names as input. Use the actual output names.
    scores = cast(Any, result).to_pandas()
    print("\n" + scores[["user_input", "faithfulness", "context_precision"]].to_string())

    mean_faithfulness = scores["faithfulness"].mean()
    mean_precision = scores["context_precision"].mean()

    print(f"\nMean faithfulness:      {mean_faithfulness:.2f}")
    print(f"Mean context precision: {mean_precision:.2f}")

    assert mean_faithfulness >= 0.7, f"Faithfulness too low ({mean_faithfulness:.2f}) — answers may not be grounded in retrieved context."
    assert mean_precision >= 0.5, f"Context precision too low ({mean_precision:.2f}) — retrieval is pulling irrelevant chunks."