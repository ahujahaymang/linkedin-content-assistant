"""Profile Evaluator - turn a profile + its post performance into a strategy brief.

Content intelligence (``memory/content_intelligence.py``) looks only at what has
been posted. This evaluator adds the missing half: it compares the profile's
*stated* positioning (identity, domains, target audience) against what the
content actually delivers and what resonates, then produces a concise,
actionable strategy brief.

The brief is designed to be injected into content generation so new posts are
grounded in a real assessment of the person rather than generic prompting.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProfileStrategyBrief:
    """Actionable strategy brief derived from a profile and its post history."""
    profile_id: str
    positioning_assessment: str = ""      # stated vs. actual positioning
    alignment_score: float = 0.0          # 0-100, how well content matches positioning
    refined_positioning: str = ""         # a sharpened one-line positioning statement
    what_resonates: List[str] = field(default_factory=list)     # engagement-backed wins
    alignment_gaps: List[str] = field(default_factory=list)     # stated-but-underserved areas
    audience_fit: str = ""                # how well content serves the target audience
    content_pillars: List[Dict[str, str]] = field(default_factory=list)  # {name, why}
    next_directions: List[str] = field(default_factory=list)    # concrete content directions
    avoid: List[str] = field(default_factory=list)              # what to stop doing
    generated_at: str = ""
    posts_evaluated: int = 0
    source: str = "llm"                   # "llm" or "rule_based"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "positioning_assessment": self.positioning_assessment,
            "alignment_score": self.alignment_score,
            "refined_positioning": self.refined_positioning,
            "what_resonates": self.what_resonates,
            "alignment_gaps": self.alignment_gaps,
            "audience_fit": self.audience_fit,
            "content_pillars": self.content_pillars,
            "next_directions": self.next_directions,
            "avoid": self.avoid,
            "generated_at": self.generated_at,
            "posts_evaluated": self.posts_evaluated,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileStrategyBrief":
        return cls(
            profile_id=data.get("profile_id", ""),
            positioning_assessment=data.get("positioning_assessment", ""),
            alignment_score=float(data.get("alignment_score", 0.0) or 0.0),
            refined_positioning=data.get("refined_positioning", ""),
            what_resonates=data.get("what_resonates", []) or [],
            alignment_gaps=data.get("alignment_gaps", []) or [],
            audience_fit=data.get("audience_fit", ""),
            content_pillars=data.get("content_pillars", []) or [],
            next_directions=data.get("next_directions", []) or [],
            avoid=data.get("avoid", []) or [],
            generated_at=data.get("generated_at", ""),
            posts_evaluated=int(data.get("posts_evaluated", 0) or 0),
            source=data.get("source", "llm"),
        )


class ProfileEvaluator:
    """Evaluates a profile against its content to produce a strategy brief."""

    def __init__(self, llm_factory=None):
        self.llm_factory = llm_factory

    async def evaluate(
        self,
        profile: Any,
        profile_store: Any,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Evaluate a profile and return (and cache) a strategy brief.

        Args:
            profile: ProfileConfig for the profile
            profile_store: ProfileMemoryStore for posts / intelligence / caching
            refresh: If True, regenerate even if a cached brief exists

        Returns:
            Strategy brief dictionary
        """
        profile_id = profile.profile_id

        if not refresh:
            cached = profile_store.get_strategy_brief(profile_id)
            if cached:
                logger.info(f"Using cached strategy brief for {profile_id}")
                return cached

        posts = profile_store.get_historical_posts(profile_id) or []
        intelligence = None
        try:
            intelligence = profile_store.get_content_intelligence(profile_id)
        except Exception as e:  # non-fatal
            logger.warning(f"Could not load content intelligence for {profile_id}: {e}")

        if self.llm_factory and posts:
            try:
                brief = await self._llm_evaluate(profile, posts, intelligence)
            except Exception as e:
                logger.warning(f"LLM profile evaluation failed, using rule-based: {e}")
                brief = self._rule_based_evaluate(profile, posts, intelligence)
        else:
            brief = self._rule_based_evaluate(profile, posts, intelligence)

        brief_dict = brief.to_dict()
        profile_store.store_strategy_brief(profile_id, brief_dict)
        return brief_dict

    # ------------------------------------------------------------------ LLM

    async def _llm_evaluate(
        self,
        profile: Any,
        posts: List[Dict[str, Any]],
        intelligence: Optional[Dict[str, Any]],
    ) -> ProfileStrategyBrief:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(profile, posts, intelligence)

        response = await self.llm_factory.generate_with_system(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2000,
        )
        return self._parse_response(response.content, profile.profile_id, len(posts))

    def _build_system_prompt(self) -> str:
        return """You are a LinkedIn personal-brand strategist. You assess how \
well a professional's actual posting matches their stated positioning, what \
genuinely resonates with their audience, and where the biggest content \
opportunities are.

You are candid and specific. Avoid generic advice. Base every judgment on the \
evidence provided (the stated profile, the posts, engagement, and the content \
analysis).

OUTPUT FORMAT: Return ONLY a valid JSON object:
{
    "positioning_assessment": "2-4 sentences: does the content deliver on the stated positioning? Where does it drift?",
    "alignment_score": 0-100,
    "refined_positioning": "one sharpened sentence capturing what this person should be known for",
    "what_resonates": ["specific, evidence-backed observations about what works"],
    "alignment_gaps": ["stated domains/positioning that are underserved by actual content"],
    "audience_fit": "1-2 sentences on how well the content serves the stated target audience",
    "content_pillars": [{"name": "pillar", "why": "why it fits this person and audience"}],
    "next_directions": ["3-6 concrete, specific post directions grounded in this person's expertise"],
    "avoid": ["patterns or topics to stop doing"]
}

Provide 3-5 content_pillars and 3-6 next_directions. Be concrete."""

    def _build_user_prompt(
        self,
        profile: Any,
        posts: List[Dict[str, Any]],
        intelligence: Optional[Dict[str, Any]],
    ) -> str:
        identity = profile.identity
        behavior = profile.behavior

        prompt = f"""Evaluate this professional's LinkedIn strategy.

STATED PROFILE:
- Headline: {identity.headline}
- Seniority: {getattr(identity.seniority, 'value', identity.seniority)}
- Primary Domains: {', '.join(identity.primary_domains)}
- Target Audience: {identity.target_audience}
- Positioning: {identity.positioning}
- Excluded Topics: {', '.join(identity.excluded_topics) or 'none'}
- Active Topics: {', '.join(behavior.active_topics) or 'n/a'}
"""

        # Engagement-ranked sample of posts (most-engaged first, capped)
        sample = self._top_posts_by_engagement(posts, limit=15)
        prompt += f"\nACTUAL POSTS (sample of {len(sample)} of {len(posts)}, higher-engagement first):\n"
        for i, post in enumerate(sample, 1):
            content = (post.get("content", "") or "")[:280]
            eng = post.get("engagement", {}) or {}
            likes = eng.get("likes", "?")
            comments = eng.get("comments", "?")
            prompt += f"\n[{i}] (likes={likes}, comments={comments})\n{content}\n"

        # Fold in existing content-intelligence signals if available
        if intelligence:
            landscape = intelligence.get("landscape_analysis", {})
            themes = landscape.get("themes", {})
            if themes:
                prompt += "\nCONTENT ANALYSIS SIGNALS:\n"
                prompt += f"- Dominant themes: {', '.join(themes.get('dominant_themes', [])[:5])}\n"
                prompt += f"- Underexplored themes: {', '.join(themes.get('underexplored_themes', [])[:5])}\n"
            audience = landscape.get("audience_insights", {})
            if audience:
                prompt += f"- Detected audience stage: {audience.get('primary_audience_stage', 'unknown')}\n"

        prompt += "\nReturn only the JSON strategy brief."
        return prompt

    def _parse_response(
        self, response_content: str, profile_id: str, posts_count: int
    ) -> ProfileStrategyBrief:
        content = response_content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        return ProfileStrategyBrief(
            profile_id=profile_id,
            positioning_assessment=data.get("positioning_assessment", ""),
            alignment_score=float(data.get("alignment_score", 0.0) or 0.0),
            refined_positioning=data.get("refined_positioning", ""),
            what_resonates=data.get("what_resonates", []) or [],
            alignment_gaps=data.get("alignment_gaps", []) or [],
            audience_fit=data.get("audience_fit", ""),
            content_pillars=data.get("content_pillars", []) or [],
            next_directions=data.get("next_directions", []) or [],
            avoid=data.get("avoid", []) or [],
            generated_at=datetime.utcnow().isoformat(),
            posts_evaluated=posts_count,
            source="llm",
        )

    # ----------------------------------------------------------- rule-based

    def _rule_based_evaluate(
        self,
        profile: Any,
        posts: List[Dict[str, Any]],
        intelligence: Optional[Dict[str, Any]],
    ) -> ProfileStrategyBrief:
        """Deterministic fallback when no LLM is available."""
        identity = profile.identity
        pillars = [
            {"name": d, "why": f"Core stated domain: {d}"}
            for d in identity.primary_domains[:5]
        ]

        gaps: List[str] = []
        resonates: List[str] = []
        directions: List[str] = []

        if intelligence:
            landscape = intelligence.get("landscape_analysis", {})
            themes = landscape.get("themes", {})
            underexplored = themes.get("underexplored_themes", [])
            gaps = [f"Underexplored theme: {t}" for t in underexplored[:3]]
            engagement = landscape.get("engagement_patterns", {})
            previews = engagement.get("top_performing_previews", [])
            resonates = [p[:120] for p in previews[:3]]

        # Directions from stated domains not obviously covered
        for domain in identity.primary_domains:
            directions.append(f"Share a concrete, first-hand lesson in {domain}")

        return ProfileStrategyBrief(
            profile_id=profile.profile_id,
            positioning_assessment=(
                "Rule-based assessment (no LLM). Verify content aligns with the "
                f"stated positioning: {identity.positioning}"
            ),
            alignment_score=50.0,
            refined_positioning=identity.positioning,
            what_resonates=resonates,
            alignment_gaps=gaps,
            audience_fit=f"Target audience: {identity.target_audience}",
            content_pillars=pillars,
            next_directions=directions[:6],
            avoid=[],
            generated_at=datetime.utcnow().isoformat(),
            posts_evaluated=len(posts),
            source="rule_based",
        )

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _top_posts_by_engagement(
        posts: List[Dict[str, Any]], limit: int = 15
    ) -> List[Dict[str, Any]]:
        def score(post: Dict[str, Any]) -> int:
            eng = post.get("engagement", {}) or {}
            try:
                likes = int(str(eng.get("likes", "0") or "0").replace(",", ""))
                comments = int(str(eng.get("comments", "0") or "0").replace(",", ""))
            except ValueError:
                return 0
            return likes + comments * 2

        ranked = sorted(posts, key=score, reverse=True)
        return ranked[:limit]

    @staticmethod
    def brief_to_prompt_context(brief: Dict[str, Any]) -> str:
        """Render a strategy brief as compact text for injection into prompts."""
        if not brief:
            return ""
        lines: List[str] = ["PROFILE STRATEGY BRIEF (ground content in this):"]
        if brief.get("refined_positioning"):
            lines.append(f"- Be known for: {brief['refined_positioning']}")
        pillars = brief.get("content_pillars", [])
        if pillars:
            names = ", ".join(p.get("name", "") for p in pillars if p.get("name"))
            lines.append(f"- Content pillars: {names}")
        if brief.get("what_resonates"):
            lines.append(f"- What resonates: {'; '.join(brief['what_resonates'][:3])}")
        if brief.get("alignment_gaps"):
            lines.append(f"- Underserved areas to lean into: {'; '.join(brief['alignment_gaps'][:3])}")
        if brief.get("next_directions"):
            lines.append("- Prioritized directions:")
            for d in brief["next_directions"][:5]:
                lines.append(f"    • {d}")
        if brief.get("avoid"):
            lines.append(f"- Avoid: {'; '.join(brief['avoid'][:3])}")
        return "\n".join(lines)
