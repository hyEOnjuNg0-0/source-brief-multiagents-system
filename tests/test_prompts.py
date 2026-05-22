from pathlib import Path


PROMPT_DIR = Path("src/research_system/prompts")


def test_role_prompts_exist_and_define_output_contracts():
    prompt_names = [
        "planner.md",
        "researcher_a.md",
        "researcher_b.md",
        "researcher_c.md",
        "critic.md",
        "verifier.md",
        "synthesizer.md",
    ]

    for name in prompt_names:
        content = (PROMPT_DIR / name).read_text(encoding="utf-8")
        assert "Return only JSON" in content
        assert len(content.splitlines()) >= 8
