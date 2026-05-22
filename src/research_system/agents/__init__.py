"""Agent implementations."""

from research_system.agents.base import Agent, StructuredLLM, Tool
from research_system.agents.critic import CriticAgent
from research_system.agents.planner import PlannerAgent
from research_system.agents.researcher import ResearcherAgent, create_default_researchers
from research_system.agents.synthesizer import SynthesizerAgent, briefing_to_markdown
from research_system.agents.verifier import VerifierAgent

__all__ = [
    "Agent",
    "CriticAgent",
    "PlannerAgent",
    "ResearcherAgent",
    "StructuredLLM",
    "SynthesizerAgent",
    "Tool",
    "VerifierAgent",
    "briefing_to_markdown",
    "create_default_researchers",
]
