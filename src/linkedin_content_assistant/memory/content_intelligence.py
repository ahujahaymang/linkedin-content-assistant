"""Content Intelligence - Extract strategic insights from historical posts.

This module analyzes historical posts to derive:
- Content themes and topic clusters
- Engagement patterns and what resonates
- Knowledge gaps and unexplored angles
- Content evolution and progression
- Audience response patterns
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentIntelligence:
    """Analyzes historical posts to extract strategic content insights."""
    
    def __init__(self):
        """Initialize content intelligence analyzer."""
        pass
    
    def analyze_content_landscape(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform comprehensive analysis of historical content.
        
        Args:
            posts: List of historical post dictionaries
            
        Returns:
            Dictionary with strategic content insights
        """
        if not posts:
            return self._empty_analysis()
        
        logger.info(f"Analyzing content landscape from {len(posts)} posts")
        
        analysis = {
            "total_posts_analyzed": len(posts),
            "themes": self._extract_themes(posts),
            "engagement_patterns": self._analyze_engagement(posts),
            "content_evolution": self._track_content_evolution(posts),
            "knowledge_domains": self._identify_knowledge_domains(posts),
            "audience_insights": self._extract_audience_insights(posts),
            "content_gaps": self._identify_content_gaps(posts),
            "successful_patterns": self._identify_successful_patterns(posts),
            "key_messages": self._extract_key_messages(posts),
            "content_progression": self._analyze_content_progression(posts)
        }
        
        return analysis
    
    def _extract_themes(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract main themes and topic clusters from posts."""
        themes = defaultdict(list)
        theme_keywords = {
            "career_growth": ["career", "transition", "growth", "level up", "promotion", "senior"],
            "data_engineering": ["data", "pipeline", "etl", "spark", "airflow", "kafka", "streaming"],
            "software_development": ["code", "software", "development", "architecture", "design", "backend"],
            "distributed_systems": ["distributed", "scalability", "performance", "latency", "throughput"],
            "learning": ["learn", "study", "course", "tutorial", "practice", "skill"],
            "production": ["production", "deployment", "monitoring", "incident", "failure", "reliability"],
            "aws": ["aws", "cloud", "s3", "lambda", "ec2", "dynamodb"],
            "leadership": ["team", "leadership", "mentor", "management", "collaboration"],
            "problem_solving": ["problem", "solution", "debug", "troubleshoot", "fix", "resolve"]
        }
        
        for post in posts:
            content = post.get('content', '').lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in content for keyword in keywords):
                    themes[theme].append({
                        "preview": content[:150],
                        "engagement": post.get('engagement', {}),
                        "length": post.get('length', 0)
                    })
        
        # Calculate theme statistics
        theme_stats = {}
        for theme, posts_list in themes.items():
            total_engagement = sum(
                int(p.get('engagement', {}).get('likes', '0') or '0') 
                for p in posts_list
            )
            theme_stats[theme] = {
                "post_count": len(posts_list),
                "total_engagement": total_engagement,
                "avg_engagement": total_engagement / len(posts_list) if posts_list else 0,
                "coverage_percentage": (len(posts_list) / len(posts)) * 100
            }
        
        # Sort by post count
        sorted_themes = sorted(
            theme_stats.items(), 
            key=lambda x: x[1]['post_count'], 
            reverse=True
        )
        
        return {
            "theme_distribution": dict(sorted_themes[:10]),
            "dominant_themes": [t[0] for t in sorted_themes[:3]],
            "underexplored_themes": [t[0] for t in sorted_themes if t[1]['post_count'] <= 2]
        }
    
    def _analyze_engagement(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what content gets the most engagement."""
        engagement_data = []
        
        for post in posts:
            engagement = post.get('engagement', {})
            # Remove commas from numbers before converting to int
            likes_str = str(engagement.get('likes', '0') or '0').replace(',', '')
            comments_str = str(engagement.get('comments', '0') or '0').replace(',', '')
            
            try:
                likes = int(likes_str)
                comments = int(comments_str)
            except ValueError:
                # Skip posts with invalid engagement data
                continue
            
            if likes > 0 or comments > 0:
                engagement_data.append({
                    "content_preview": post.get('content', '')[:200],
                    "likes": likes,
                    "comments": comments,
                    "length": post.get('length', 0),
                    "has_question": '?' in post.get('content', ''),
                    "has_list": any(marker in post.get('content', '') for marker in ['•', '→', '✓', '1.', '2.'])
                })
        
        if not engagement_data:
            return {"message": "No engagement data available"}
        
        # Sort by total engagement
        engagement_data.sort(key=lambda x: x['likes'] + x['comments'] * 2, reverse=True)
        
        top_posts = engagement_data[:5]
        
        # Identify patterns in high-engagement posts
        patterns = {
            "avg_length_high_engagement": sum(p['length'] for p in top_posts) / len(top_posts) if top_posts else 0,
            "questions_in_top_posts": sum(1 for p in top_posts if p['has_question']),
            "lists_in_top_posts": sum(1 for p in top_posts if p['has_list']),
            "top_performing_previews": [p['content_preview'] for p in top_posts[:3]]
        }
        
        return patterns
    
    def _track_content_evolution(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Track how content has evolved over time."""
        # Group posts by time periods (if timestamps available)
        # For now, analyze progression by position in list
        
        if len(posts) < 10:
            return {"message": "Not enough posts to track evolution"}
        
        early_posts = posts[-10:]  # Oldest
        recent_posts = posts[:10]   # Newest
        
        early_themes = self._get_dominant_keywords(early_posts)
        recent_themes = self._get_dominant_keywords(recent_posts)
        
        return {
            "early_focus": early_themes[:5],
            "recent_focus": recent_themes[:5],
            "emerging_topics": [t for t in recent_themes if t not in early_themes][:5],
            "declining_topics": [t for t in early_themes if t not in recent_themes][:5]
        }
    
    def _identify_knowledge_domains(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify areas of expertise demonstrated in posts."""
        domains = {
            "technical_skills": set(),
            "tools_technologies": set(),
            "concepts": set(),
            "methodologies": set()
        }
        
        # Technical skills patterns
        tech_patterns = {
            "technical_skills": [
                r'\b(python|java|scala|sql|javascript|typescript|go|rust)\b',
                r'\b(api|rest|graphql|grpc)\b',
                r'\b(testing|debugging|profiling|optimization)\b'
            ],
            "tools_technologies": [
                r'\b(spark|kafka|airflow|flink|hadoop)\b',
                r'\b(aws|azure|gcp|kubernetes|docker)\b',
                r'\b(postgres|mysql|mongodb|dynamodb|redis)\b'
            ],
            "concepts": [
                r'\b(distributed systems|microservices|event-driven|streaming)\b',
                r'\b(scalability|performance|reliability|availability)\b',
                r'\b(data modeling|schema design|partitioning)\b'
            ],
            "methodologies": [
                r'\b(agile|scrum|devops|ci/cd)\b',
                r'\b(design patterns|solid|dry|kiss)\b',
                r'\b(monitoring|observability|alerting)\b'
            ]
        }
        
        all_content = ' '.join(post.get('content', '').lower() for post in posts)
        
        for domain, patterns in tech_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, all_content, re.IGNORECASE)
                domains[domain].update(matches)
        
        return {
            domain: sorted(list(items))[:10] 
            for domain, items in domains.items()
        }
    
    def _extract_audience_insights(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract insights about target audience and their interests."""
        audience_signals = {
            "career_stage": Counter(),
            "pain_points": [],
            "aspirations": []
        }
        
        # Career stage indicators
        career_patterns = {
            "junior": ["junior", "entry-level", "beginner", "learning", "first job"],
            "mid_level": ["mid-level", "experienced", "senior", "lead"],
            "senior": ["senior", "staff", "principal", "architect", "expert"]
        }
        
        # Pain points indicators
        pain_point_keywords = [
            "struggle", "challenge", "difficult", "problem", "issue",
            "confused", "stuck", "frustrated", "overwhelmed"
        ]
        
        # Aspiration indicators
        aspiration_keywords = [
            "want to", "goal", "aspire", "dream", "achieve",
            "level up", "grow", "advance", "transition"
        ]
        
        for post in posts:
            content = post.get('content', '').lower()
            
            # Detect career stage mentions
            for stage, keywords in career_patterns.items():
                if any(kw in content for kw in keywords):
                    audience_signals["career_stage"][stage] += 1
            
            # Extract pain points (sentences with pain keywords)
            sentences = content.split('.')
            for sentence in sentences:
                if any(kw in sentence for kw in pain_point_keywords):
                    audience_signals["pain_points"].append(sentence.strip()[:100])
            
            # Extract aspirations
            for sentence in sentences:
                if any(kw in sentence for kw in aspiration_keywords):
                    audience_signals["aspirations"].append(sentence.strip()[:100])
        
        return {
            "primary_audience_stage": audience_signals["career_stage"].most_common(1)[0][0] if audience_signals["career_stage"] else "unknown",
            "audience_distribution": dict(audience_signals["career_stage"]),
            "common_pain_points": audience_signals["pain_points"][:5],
            "common_aspirations": audience_signals["aspirations"][:5]
        }
    
    def _identify_content_gaps(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify topics that haven't been covered or need more depth."""
        covered_topics = self._get_dominant_keywords(posts, top_n=50)
        
        # Potential topics based on domain
        potential_topics = {
            "technical_depth": [
                "system design", "architecture patterns", "performance optimization",
                "database internals", "networking fundamentals", "security best practices"
            ],
            "career_development": [
                "salary negotiation", "interview preparation", "resume building",
                "networking strategies", "personal branding", "work-life balance"
            ],
            "practical_guides": [
                "step-by-step tutorials", "debugging strategies", "code review tips",
                "testing strategies", "deployment practices", "monitoring setup"
            ],
            "industry_insights": [
                "tech trends", "tool comparisons", "case studies",
                "lessons learned", "failure stories", "success stories"
            ]
        }
        
        gaps = {}
        for category, topics in potential_topics.items():
            uncovered = []
            for topic in topics:
                # Check if topic keywords appear in covered topics
                topic_words = set(topic.lower().split())
                if not any(word in covered_topics for word in topic_words):
                    uncovered.append(topic)
            
            if uncovered:
                gaps[category] = uncovered[:3]
        
        return gaps
    
    def _identify_successful_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identify patterns in successful posts."""
        patterns = {
            "opening_styles": Counter(),
            "content_structures": Counter(),
            "closing_styles": Counter()
        }
        
        opening_patterns = {
            "question": r'^(what|why|how|when|where|who|have you|do you|are you)',
            "statement": r'^(i|we|my|the|in|at)',
            "statistic": r'^\d+%?',
            "quote": r'^"',
            "story": r'^(once|last|yesterday|recently)'
        }
        
        for post in posts:
            content = post.get('content', '').strip().lower()
            if not content:
                continue
            
            # Analyze opening
            first_line = content.split('\n')[0]
            for pattern_name, pattern in opening_patterns.items():
                if re.match(pattern, first_line):
                    patterns["opening_styles"][pattern_name] += 1
                    break
            
            # Analyze structure
            if '•' in content or '→' in content or '✓' in content:
                patterns["content_structures"]["bullet_list"] += 1
            elif re.search(r'\d+\.', content):
                patterns["content_structures"]["numbered_list"] += 1
            elif content.count('\n\n') >= 3:
                patterns["content_structures"]["multi_paragraph"] += 1
            else:
                patterns["content_structures"]["single_flow"] += 1
            
            # Analyze closing
            last_line = content.split('\n')[-1] if '\n' in content else content[-100:]
            if '?' in last_line:
                patterns["closing_styles"]["question"] += 1
            elif any(word in last_line for word in ["share", "comment", "thoughts", "discuss"]):
                patterns["closing_styles"]["call_to_engage"] += 1
            elif any(word in last_line for word in ["link", "read", "check out", "learn more"]):
                patterns["closing_styles"]["call_to_action"] += 1
        
        return {
            "most_used_opening": patterns["opening_styles"].most_common(1)[0] if patterns["opening_styles"] else ("unknown", 0),
            "most_used_structure": patterns["content_structures"].most_common(1)[0] if patterns["content_structures"] else ("unknown", 0),
            "most_used_closing": patterns["closing_styles"].most_common(1)[0] if patterns["closing_styles"] else ("unknown", 0),
            "all_patterns": {
                "openings": dict(patterns["opening_styles"]),
                "structures": dict(patterns["content_structures"]),
                "closings": dict(patterns["closing_styles"])
            }
        }
    
    def _extract_key_messages(self, posts: List[Dict[str, Any]]) -> List[str]:
        """Extract key messages and core beliefs from posts."""
        key_messages = []
        
        # Look for strong statements (sentences with emphasis)
        emphasis_patterns = [
            r'[A-Z][A-Z\s]{10,}',  # ALL CAPS phrases
            r'→.*\n',  # Arrow points
            r'✓.*\n',  # Checkmark points
            r'•.*\n',  # Bullet points
        ]
        
        for post in posts:
            content = post.get('content', '')
            for pattern in emphasis_patterns:
                matches = re.findall(pattern, content)
                key_messages.extend([m.strip() for m in matches if len(m.strip()) > 20])
        
        # Deduplicate and return top messages
        unique_messages = list(dict.fromkeys(key_messages))
        return unique_messages[:10]
    
    def _analyze_content_progression(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how content builds on previous posts."""
        if len(posts) < 5:
            return {"message": "Not enough posts to analyze progression"}
        
        # Analyze if posts reference previous content
        references = {
            "callbacks": 0,  # References to previous posts
            "series": 0,     # Part of a series
            "expansions": 0  # Expanding on previous topics
        }
        
        callback_keywords = ["as i mentioned", "in my last post", "previously", "earlier"]
        series_keywords = ["part", "issue", "episode", "chapter"]
        
        for post in posts:
            content = post.get('content', '').lower()
            
            if any(kw in content for kw in callback_keywords):
                references["callbacks"] += 1
            if any(kw in content for kw in series_keywords):
                references["series"] += 1
        
        return {
            "uses_callbacks": references["callbacks"] > 0,
            "has_series_content": references["series"] > 0,
            "callback_frequency": f"{(references['callbacks'] / len(posts)) * 100:.1f}%",
            "series_frequency": f"{(references['series'] / len(posts)) * 100:.1f}%",
            "recommendation": self._get_progression_recommendation(references, len(posts))
        }
    
    def _get_progression_recommendation(self, references: Dict[str, int], total_posts: int) -> str:
        """Get recommendation for content progression strategy."""
        if references["series"] > total_posts * 0.3:
            return "Strong series content - continue building connected narratives"
        elif references["callbacks"] > total_posts * 0.2:
            return "Good content continuity - keep referencing previous insights"
        else:
            return "Consider creating more connected content - reference previous posts to build narrative"
    
    def _get_dominant_keywords(self, posts: List[Dict[str, Any]], top_n: int = 20) -> List[str]:
        """Extract dominant keywords from posts."""
        # Combine all content
        all_text = ' '.join(post.get('content', '').lower() for post in posts)
        
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your',
            'his', 'her', 'its', 'our', 'their', 'me', 'him', 'us', 'them'
        }
        
        # Extract words
        words = re.findall(r'\b[a-z]{4,}\b', all_text)
        filtered_words = [w for w in words if w not in stop_words]
        
        # Count and return top keywords
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(top_n)]
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure."""
        return {
            "total_posts_analyzed": 0,
            "message": "No posts available for analysis"
        }
    
    def generate_content_direction(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate strategic direction for new content based on analysis.
        
        Args:
            analysis: Content landscape analysis
            
        Returns:
            Strategic recommendations for future content
        """
        if analysis.get("total_posts_analyzed", 0) == 0:
            return {"message": "No analysis available"}
        
        recommendations = {
            "priority_topics": self._recommend_priority_topics(analysis),
            "content_angles": self._recommend_content_angles(analysis),
            "audience_alignment": self._recommend_audience_focus(analysis),
            "format_suggestions": self._recommend_formats(analysis),
            "strategic_gaps": analysis.get("content_gaps", {}),
            "build_on_success": self._recommend_success_patterns(analysis)
        }
        
        return recommendations
    
    def _recommend_priority_topics(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Recommend priority topics for next posts."""
        recommendations = []
        
        # Underexplored themes with potential
        underexplored = analysis.get("themes", {}).get("underexplored_themes", [])
        for theme in underexplored[:3]:
            recommendations.append({
                "topic": theme,
                "reason": "Underexplored area - opportunity to establish expertise",
                "priority": "high"
            })
        
        # Content gaps
        gaps = analysis.get("content_gaps", {})
        for category, topics in list(gaps.items())[:2]:
            if topics:
                recommendations.append({
                    "topic": topics[0],
                    "reason": f"Gap in {category} - audience likely interested",
                    "priority": "medium"
                })
        
        return recommendations[:5]
    
    def _recommend_content_angles(self, analysis: Dict[str, Any]) -> List[str]:
        """Recommend content angles based on successful patterns."""
        angles = []
        
        successful_patterns = analysis.get("successful_patterns", {})
        opening_style = successful_patterns.get("most_used_opening", ("unknown", 0))[0]
        
        if opening_style == "question":
            angles.append("Continue using question-based openings - they engage readers")
        elif opening_style == "statement":
            angles.append("Strong declarative statements work well - keep using them")
        
        # Based on audience insights
        audience = analysis.get("audience_insights", {})
        pain_points = audience.get("common_pain_points", [])
        if pain_points:
            angles.append(f"Address pain point: {pain_points[0][:80]}")
        
        return angles[:3]
    
    def _recommend_audience_focus(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend audience focus based on insights."""
        audience = analysis.get("audience_insights", {})
        
        return {
            "primary_audience": audience.get("primary_audience_stage", "unknown"),
            "recommendation": f"Continue targeting {audience.get('primary_audience_stage', 'unknown')} professionals",
            "expand_to": "Consider occasional content for adjacent career stages"
        }
    
    def _recommend_formats(self, analysis: Dict[str, Any]) -> List[str]:
        """Recommend content formats based on successful patterns."""
        patterns = analysis.get("successful_patterns", {}).get("all_patterns", {})
        structures = patterns.get("structures", {})
        
        recommendations = []
        if structures.get("bullet_list", 0) > structures.get("numbered_list", 0):
            recommendations.append("Bullet lists perform well - use for key points")
        else:
            recommendations.append("Numbered lists work well - use for step-by-step content")
        
        return recommendations
    
    def _recommend_success_patterns(self, analysis: Dict[str, Any]) -> List[str]:
        """Recommend patterns to replicate from successful posts."""
        engagement = analysis.get("engagement_patterns", {})
        
        recommendations = []
        
        if engagement.get("questions_in_top_posts", 0) > 3:
            recommendations.append("Top posts include questions - continue asking audience for input")
        
        if engagement.get("lists_in_top_posts", 0) > 3:
            recommendations.append("Lists drive engagement - use structured formats")
        
        avg_length = engagement.get("avg_length_high_engagement", 0)
        if avg_length > 0:
            recommendations.append(f"High-engagement posts average {int(avg_length)} characters - aim for similar length")
        
        return recommendations
