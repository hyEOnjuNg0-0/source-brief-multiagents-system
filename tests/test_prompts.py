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


def test_role_prompts_use_behavioral_workflows():
    prompt_names = [
        "planner.md",
        "researcher_a.md",
        "researcher_b.md",
        "researcher_c.md",
        "critic.md",
        "verifier.md",
        "synthesizer.md",
    ]
    banned_phrases = [
        "act as an expert",
        "you are an expert",
        "expert in",
    ]

    for name in prompt_names:
        content = (PROMPT_DIR / name).read_text(encoding="utf-8")
        lowered = content.lower()
        assert "Workflow:" in content
        assert "Quality bar:" in content
        for phrase in banned_phrases:
            assert phrase not in lowered
