"""
GuardGPT MCP Server.

This server exposes the existing GuardGPT core as a set of MCP tools. It is a
THIN ADAPTER LAYER - it does not implement its own classifier, jailbreak
detector, content moderator, or decision engine.

The registered tools are:

    prompt_analysis     - IntentClassifier + DatasetLoader (FAISS)
    jailbreak_detection - IntentClassifier (prompt_injection / jailbreak)
                          + small deterministic pattern hints
    content_moderation  - IntentClassifier + dataset category scores
    decision            - core.decision_engine.DecisionEngine
    audit_logger        - append-only writer for logs/guardgpt_audit.jsonl

Run from the project root:

    python -m mcp_server.server
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

# Importing the mcp_server package runs its __init__.py, which sets up
# sys.path. Then the following imports resolve correctly.
import mcp_server  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("GUARDGPT_PROJECT_ROOT", str(PROJECT_ROOT))

from mcp.server import MCPServer  # noqa: E402

from models.schemas import (  # noqa: E402
    PromptAnalysisInput,
    PromptAnalysisOutput,
    JailbreakDetectionInput,
    JailbreakDetectionOutput,
    ContentModerationInput,
    ContentModerationOutput,
    DecisionInput,
    DecisionOutput,
    AuditLoggerInput,
    AuditLoggerOutput,
)

from tools.prompt_analysis import analyze_prompt  # noqa: E402
from tools.jailbreak_detection import detect_jailbreak  # noqa: E402
from tools.content_moderation import moderate_content  # noqa: E402
from tools.decision import decide  # noqa: E402
from tools.audit_logger import log_audit_event  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)


mcp = MCPServer(
    name="GuardGPT MCP Server",
    version="1.0.0",
    description=(
        "MCP adapter exposing the GuardGPT core "
        "(classifier, FAISS dataset, decision engine) as tools."
    ),
)


@mcp.tool(
    name="prompt_analysis",
    description=(
        "Analyze a prompt for intent, risk, and category scores. "
        "Reuses core.intent_classifier and core.dataset_loader."
    ),
)
def prompt_analysis(data: PromptAnalysisInput) -> PromptAnalysisOutput:
    return analyze_prompt(data)


@mcp.tool(
    name="jailbreak_detection",
    description=(
        "Detect prompt-injection and jailbreak attempts. "
        "Reuses core.intent_classifier and existing pattern logic."
    ),
)
def jailbreak_detection(data: JailbreakDetectionInput) -> JailbreakDetectionOutput:
    return detect_jailbreak(data)


@mcp.tool(
    name="content_moderation",
    description=(
        "Identify unsafe content categories and severity. "
        "Reuses core.intent_classifier and dataset category scores."
    ),
)
def content_moderation(data: ContentModerationInput) -> ContentModerationOutput:
    return moderate_content(data)


@mcp.tool(
    name="decision",
    description=(
        "Produce the final ALLOW / SANITIZE / BLOCK decision. "
        "THIN WRAPPER around core.decision_engine.DecisionEngine."
    ),
)
def decision(data: DecisionInput) -> DecisionOutput:
    return decide(data)


@mcp.tool(
    name="audit_logger",
    description=(
        "Append a structured Guard Report to logs/guardgpt_audit.jsonl. "
        "Does not make or modify safety decisions."
    ),
)
def audit_logger(data: AuditLoggerInput) -> AuditLoggerOutput:
    return log_audit_event(data)


if __name__ == "__main__":
    from urllib.parse import urlparse

    raw_url = os.getenv("GUARDGPT_MCP_URL", "http://127.0.0.1:8000/mcp")
    parsed = None
    try:
        parsed = urlparse(raw_url)
    except Exception:
        parsed = None

    if parsed and parsed.hostname and parsed.port:
        host = parsed.hostname
        port = parsed.port
    else:
        host = "127.0.0.1"
        port = 8000

    print(f"Starting GuardGPT MCP Server...")
    print(f"Transport: Streamable HTTP")
    print(f"Endpoint: {raw_url}")
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
    )
