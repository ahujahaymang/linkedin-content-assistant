"""Quality Critique Agent for scoring and improving LinkedIn drafts.

This agent acts as a demanding editor. It scores a drafted post against a
value-focused rubric (specificity, authenticity, insight density, etc.) and
returns actionable revision guidance. The orchestrator uses this to decide
whether to re-draft a post before it is delivered, so generic "fluff" content
is caught and rewritten instead of shipped.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .base import (
    LinkedInAgent, AgentType, AgentOutput, ValidationResult,
    ValidationStatus, ProfileContext, StatelessAgentMixin
)
from ..llm.factory import LLMFactory
from ..llm.base import LLMError

logger = logging.getLogger(__name__)


# Scoring dimensions and their weights (must sum to 1.0). Specificity,
# authenticity and insight density are weighted highest because they are what
# separate valuable posts from generic ones.
CRITIQUE_DIMENSIONS: Dict[str, float] = {
    "specificity": 0.25,        # concrete examples, numbers, named situations
    "authenticity": 0.20,       # first-hand voice, opinions only this author could hold
    "insight_density": 0.25,    # non-obvious takeaways vs restating common knowledge
    "hook_strength": 0.10,      # opening earns the next line
    "positioning_alignment": 0.10,  # fits the profile's domains/positioning
    "readability": 0.10,        # scannable, well-structured, right length
}


@dataclass
class QualityCritique:
    """Structured critique of a LinkedIn draft."""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]  # each 0-100
    passes: bool
    strengths: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    revision_guidance: str = ""
    verdict: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "passes": self.passes,
            "strengths": self.strengths,
            "issues": self.issues,
            "revision_guidance": self.revision_guidance,
            "verdict": self.verdict,
        }


class QualityCritiqueAgent(StatelessAgentMixin, LinkedInAgent):
    """Agent that critiques a LinkedIn draft and scores it for real value."""

    # Drafts scoring below this overall value are sent back for revision.
    PASS_THRESHOLD = 72.0

    def __init__(self, llm_factory: LLMFactory):
        super().__init__(AgentType.QUALITY_CRITIQUE)
        self.llm_factory = llm_factory

    async def execute(
        self,
        context: ProfileContext,
        memory: Any,
        post_content: str = "",
        hashtags: Optional[List[str]] = None,
    ) -> AgentOutput:
        """Critique a drafted post.

        Args:
            context: Profile context (for positioning alignment)
            memory: Unused, kept for agent-interface consistency
            post_content: The drafted LinkedIn post body
            hashtags: Optional hashtags on the draft

        Returns:
            AgentOutput whose content is a ``QualityCritique`` dict
        """
        try:
            system_prompt = self._build_system_prompt(context)
            user_prompt = self._build_user_prompt(post_content, hashtags or [])

            response = await self.llm_factory.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,  # critique should be consistent, not creative
                max_tokens=1200,
            )

            critique = self._parse_response(response.content)

            return AgentOutput(
                agent_type=self.agent_type,
                content=critique.to_dict(),
                metadata={
                    "llm_provider": response.provider.value,
                    "llm_model": response.model,
                    "profile_id": context.profile_id,
                    "overall_score": critique.overall_score,
                    "passes": critique.passes,
                },
                requires_approval=False,
                confidence_score=critique.overall_score / 100.0,
            )

        except Exception as e:
            logger.error(f"Quality Critique Agent execution failed: {e}")
            raise

    def validate_output(self, output: AgentOutput) -> ValidationResult:
        """Validate that the critique has the expected structure."""
        errors: List[str] = []
        warnings: List[str] = []

        content = output.content
        if "overall_score" not in content:
            errors.append("Missing overall_score in critique output")
        if "dimension_scores" not in content:
            warnings.append("Missing dimension_scores in critique output")

        status = ValidationStatus.INVALID if errors else ValidationStatus.VALID
        return ValidationResult(status, errors, warnings)

    def _build_system_prompt(self, context: ProfileContext) -> str:
        identity = context.identity
        dims = "\n".join(
            f"  - {name} (weight {int(weight * 100)}%)"
            for name, weight in CRITIQUE_DIMENSIONS.items()
        )
        return f"""You are a demanding LinkedIn content editor. Your job is to \
protect the author's credibility by rejecting generic, low-value content.

AUTHOR PROFILE (judge alignment against this):
- Identity: {identity.get('headline', 'Professional')}
- Seniority: {identity.get('seniority', 'Unknown')}
- Primary Domains: {', '.join(identity.get('primary_domains', []))}
- Positioning: {identity.get('positioning', 'Industry professional')}
- Target Audience: {identity.get('target_audience', 'Professional network')}

You score a draft from 0-100 on these dimensions:
{dims}

BE STRICT. Penalize heavily:
- Generic advice anyone could write ("communication is key", "always keep learning")
- Buzzword soup and empty corporate speak
- Restating well-known facts without a fresh angle
- Vague claims with no concrete example, analogy, number, or named situation
- Hooks that don't earn attention
- "AI-sounding" filler and listicles with no substance
- Complex jargon where a simple word or everyday analogy would land harder

Reward:
- A vivid real-world analogy that makes the idea click and stick in memory
- Simple, plain language that still respects an expert reader
- Concrete detail - whether from first-hand experience OR a sharp, well-argued
  observation. A post does NOT have to reference the author's own work to score
  well; an observational or analogy-led post is great if the idea is genuinely
  insightful.
- Non-obvious insights or contrarian-but-defensible takes
- A clear point of view and one memorable core idea
- Personality and range (witty, warm, provocative are all fine)
- Tight, scannable writing

Score "specificity" on concrete detail of ANY kind (example, analogy, number,
named situation) - not only personal anecdotes. Score "authenticity" on a
distinct, credible point of view, not on whether it is autobiographical.

OUTPUT FORMAT: Return ONLY a valid JSON object, no other text:
{{
    "dimension_scores": {{
        "specificity": 0-100,
        "authenticity": 0-100,
        "insight_density": 0-100,
        "hook_strength": 0-100,
        "positioning_alignment": 0-100,
        "readability": 0-100
    }},
    "strengths": ["what genuinely works"],
    "issues": ["specific, concrete problems"],
    "revision_guidance": "Direct, actionable instructions for rewriting this post to add real value. Reference specific fixes, not vague encouragement.",
    "verdict": "one-sentence overall judgment"
}}"""

    def _build_user_prompt(self, post_content: str, hashtags: List[str]) -> str:
        tags = " ".join(f"#{h.lstrip('#')}" for h in hashtags) if hashtags else "(none)"
        return f"""Critique this LinkedIn draft. Score each dimension and give \
concrete revision guidance.

DRAFT:
\"\"\"
{post_content}
\"\"\"

HASHTAGS: {tags}
CHARACTER COUNT: {len(post_content)}

Return only the JSON critique."""

    def _parse_response(self, response_content: str) -> QualityCritique:
        """Parse the LLM critique JSON into a QualityCritique."""
        content = response_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            # Fail open: don't block the pipeline on a malformed critique.
            logger.warning(f"Failed to parse critique JSON, treating as neutral pass: {e}")
            return QualityCritique(
                overall_score=self.PASS_THRESHOLD,
                dimension_scores={},
                passes=True,
                verdict="Critique unavailable (parse error); accepted by default.",
            )

        dimension_scores = data.get("dimension_scores", {}) or {}
        overall = self._weighted_score(dimension_scores)

        return QualityCritique(
            overall_score=round(overall, 1),
            dimension_scores={k: float(v) for k, v in dimension_scores.items() if _is_number(v)},
            passes=overall >= self.PASS_THRESHOLD,
            strengths=data.get("strengths", []) or [],
            issues=data.get("issues", []) or [],
            revision_guidance=data.get("revision_guidance", "") or "",
            verdict=data.get("verdict", "") or "",
        )

    def _weighted_score(self, dimension_scores: Dict[str, Any]) -> float:
        """Compute overall score as the weighted average of known dimensions."""
        total_weight = 0.0
        weighted_sum = 0.0
        for name, weight in CRITIQUE_DIMENSIONS.items():
            value = dimension_scores.get(name)
            if _is_number(value):
                weighted_sum += float(value) * weight
                total_weight += weight
        if total_weight == 0.0:
            return self.PASS_THRESHOLD  # no usable scores -> neutral pass
        return weighted_sum / total_weight


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
