import re
import tempfile
from pathlib import Path

import networkx as nx
import pytest

from graphify.extract import extract_python
from graphify.report import generate


_HEX_LIKE_RE = re.compile(r"\b[A-Fa-f0-9]{32,}\b")
_BASE64_LIKE_RE = re.compile(r"\b(?:[A-Za-z0-9+/]{40,}={0,2}|eyJ[A-Za-z0-9._-]{20,})\b")


def _assert_no_secretish_strings(text: str) -> None:
    forbidden_literals = (
        "config/antigravity-chatbot/tokens.json",
        "C:\\Users\\alice\\secrets\\.env",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",
        "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        "Private key material should not appear in reports.",
        "Bearer token should never leak into the report output.",
        "access_token",
        "refresh_token",
        "tokens.json",
        ".env",
    )

    for literal in forbidden_literals:
        assert literal not in text

    assert not _HEX_LIKE_RE.search(text)
    assert not _BASE64_LIKE_RE.search(text)


def test_generate_redacts_sensitive_labels_paths_and_json_values() -> None:
    jwt_like = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    hex_like = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    base64_like = "dGhpcy1sb29rcy1saWtlLWFsb25nLWJhc2U2NC1zZWNyZXQtc3RyaW5n"

    graph = nx.Graph()
    graph.add_node(
        "artifact",
        label="config/antigravity-chatbot/tokens.json",
        file_type="document",
        source_file="C:\\Users\\alice\\graph\\config\\antigravity-chatbot\\tokens.json",
    )
    graph.add_node(
        "json_blob",
        label=(
            '{"access_token":"'
            + jwt_like
            + '","refresh_token":"'
            + hex_like
            + '"}'
        ),
        file_type="document",
        source_file="C:\\Users\\alice\\secrets\\.env",
    )
    graph.add_node(
        "rationale",
        label="Bearer token should never leak into the report output.",
        file_type="rationale",
        source_file="C:\\Users\\alice\\src\\auth.py",
    )
    graph.add_edge(
        "artifact",
        "json_blob",
        relation="references",
        confidence="INFERRED",
        confidence_score=0.91,
        source_file="C:\\Users\\alice\\graph\\config\\antigravity-chatbot\\tokens.json",
    )
    graph.graph["hyperedges"] = [
        {
            "id": "secret_bundle",
            "label": f"Secret bundle {base64_like}",
            "nodes": ["artifact", "json_blob", "rationale"],
            "relation": "participate_in",
            "confidence": "INFERRED",
            "confidence_score": 0.88,
            "source_file": "C:\\Users\\alice\\graph\\config\\antigravity-chatbot\\tokens.json",
        }
    ]

    report = generate(
        graph,
        communities={0: ["artifact", "json_blob", "rationale"]},
        cohesion_scores={0: 1.0},
        community_labels={0: "tokens.json credential cluster"},
        god_node_list=[{"label": "config/antigravity-chatbot/tokens.json", "degree": 2}],
        surprise_list=[
            {
                "source": "config/antigravity-chatbot/tokens.json",
                "target": '{"access_token":"' + jwt_like + '"}',
                "source_files": [
                    "C:\\Users\\alice\\graph\\config\\antigravity-chatbot\\tokens.json",
                    "C:\\Users\\alice\\secrets\\.env",
                ],
                "confidence": "INFERRED",
                "confidence_score": 0.91,
                "relation": "references",
                "note": f"Bearer {base64_like}",
            }
        ],
        detection_result={"total_files": 2, "total_words": 42, "warning": None},
        token_cost={"input": 0, "output": 0},
        root="secret-graph",
        suggested_questions=[
            {
                "question": f"What is the purpose of {jwt_like}?",
                "why": f"Review the {hex_like} dependency path.",
            }
        ],
    )

    assert "<REDACTED>" in report
    _assert_no_secretish_strings(report)


def test_extract_python_rationale_nodes_do_not_store_source_text() -> None:
    pytest.importorskip("tree_sitter_python")

    with tempfile.TemporaryDirectory(dir="C:\\tmp") as temp_dir:
        sample = Path(temp_dir) / "sample.py"
        sample.write_text(
            '"""Private key material should not appear in reports."""\n'
            "# NOTE: API_KEY=deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
            "def demo():\n"
            '    """Bearer token should never leak into the report output."""\n'
            "    return True\n",
            encoding="utf-8",
        )

        result = extract_python(sample)
        rationale_nodes = [node for node in result["nodes"] if node.get("file_type") == "rationale"]

        assert rationale_nodes
        assert {node["label"] for node in rationale_nodes} == {"Rationale note <REDACTED>"}

        for node in rationale_nodes:
            _assert_no_secretish_strings(node["label"])
