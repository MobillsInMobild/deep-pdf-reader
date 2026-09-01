from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).parents[1]
SKILL_ROOT = REPOSITORY_ROOT / ".agents" / "skills" / "deep-pdf-reader"


def _frontmatter() -> dict[str, Any]:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    assert match is not None, "SKILL.md must start with YAML frontmatter"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict)
    return parsed


def _description_matches_pdf_scope(prompt: str, description: str) -> bool:
    """Small offline proxy for guarding distinctive trigger vocabulary."""

    markers = (
        "pdf",
        "年报",
        "财务报告",
        "研究报告",
        "合同",
        "手册",
        "annual report",
        "financial report",
        "research report",
        "contract",
        "manual",
    )
    normalized_prompt = prompt.casefold()
    normalized_description = description.casefold()
    return any(
        marker in normalized_prompt and marker in normalized_description
        for marker in markers
    )


def test_skill_metadata_supports_explicit_and_implicit_invocation() -> None:
    metadata = _frontmatter()
    openai_metadata = yaml.safe_load(
        (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    )

    assert metadata["name"] == "deep-pdf-reader"
    assert openai_metadata["policy"]["allow_implicit_invocation"] is True
    assert "$deep-pdf-reader" in openai_metadata["interface"]["default_prompt"]


def test_trigger_description_is_discriminating() -> None:
    description = str(_frontmatter()["description"])
    trigger_prompt = "分析这份 300 页年报里经营现金流下降的原因，并给出具体页码依据。"
    non_trigger_prompt = "帮我修复这个 Python unit test。"

    assert _description_matches_pdf_scope(trigger_prompt, description) is True
    assert _description_matches_pdf_scope(non_trigger_prompt, description) is False
    assert "Do not use for unrelated work" in description


def test_skill_references_are_linked_and_present() -> None:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    links = set(re.findall(r"\]\((references/[^)]+)\)", content))

    assert links == {
        "references/evidence-policy.md",
        "references/retrieval-policy.md",
    }
    assert all((SKILL_ROOT / link).is_file() for link in links)


def test_skill_mode_uses_primitives_instead_of_standalone_ask() -> None:
    content = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    bash_blocks = "\n".join(
        re.findall(r"```bash\s*(.*?)```", content, flags=re.DOTALL)
    )

    assert "deep-pdf-reader build-map" in bash_blocks
    assert "deep-pdf-reader search" in bash_blocks
    assert "deep-pdf-reader render" in bash_blocks
    assert "deep-pdf-reader ask" not in bash_blocks


def test_skill_permits_a_bounded_retrieval_loop_without_crossing_trust_boundary() -> None:
    retrieval_policy = (
        SKILL_ROOT / "references" / "retrieval-policy.md"
    ).read_text(encoding="utf-8")
    evidence_policy = (
        SKILL_ROOT / "references" / "evidence-policy.md"
    ).read_text(encoding="utf-8")

    assert "search -> select -> render -> inspect -> sufficiency decision" in retrieval_policy
    assert "second search" in retrieval_policy
    assert "3-8 unique pages" in retrieval_policy
    assert "The rendered image of the original PDF page is authoritative" in evidence_policy
    assert "Never cite a number or relationship solely from the map" in evidence_policy
