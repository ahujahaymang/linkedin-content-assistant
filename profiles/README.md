# Profile Configuration Guide

This directory contains profile configurations for the LinkedIn Content Assistant. Each profile defines a professional persona with specific identity characteristics and behavioral patterns that guide content generation.

## Overview

Profiles are stored as YAML files and consist of two main sections:
- **Identity**: Immutable professional characteristics (who you are)
- **Behavior**: Adaptive patterns that can evolve (how you communicate)

## Quick Start

1. Copy one of the example profiles (`example-senior-engineer.yaml` or `example-tech-lead.yaml`)
2. Rename it to your desired profile ID (e.g., `my-profile.yaml`)
3. Customize the identity and behavior sections
4. Place it in the `profiles/active/` directory to activate it

## Profile Structure

### Metadata Fields

```yaml
profile_id: "unique-identifier"        # Required: Alphanumeric, hyphens, underscores only
name: "Display Name"                   # Required: Human-readable profile name
description: "Profile description"     # Optional: Detailed description of the profile
version: 1                             # Required: Version number (auto-incremented on updates)
enabled: true                          # Required: Whether profile is active
created_at: "2024-01-15T10:00:00"     # Required: ISO timestamp of creation
last_updated: "2024-01-15T10:00:00"   # Required: ISO timestamp of last update
```

**Field Rules:**
- `profile_id`: Must be unique, lowercase, alphanumeric with hyphens/underscores
- `version`: Automatically incremented when behavior is updated
- `created_at` and `last_updated`: ISO 8601 format timestamps

---

## Identity Configuration

The identity section defines your immutable professional characteristics. These fields should rarely change as they represent your core professional identity.

### identity.headline

**Type:** String (1-220 characters)  
**Required:** Yes  
**Description:** Your LinkedIn headline that summarizes your professional identity

**Examples:**
```yaml
headline: "Senior Software Engineer | Cloud Architecture | Distributed Systems"
headline: "Tech Lead | Engineering Manager | Building High-Performing Teams"
headline: "Principal Engineer | AI/ML | Scalable Systems"
```

### identity.seniority

**Type:** Enum  
**Required:** Yes  
**Valid Values:** `entry`, `junior`, `mid`, `senior`, `staff`, `principal`, `director`, `vp`, `c_level`  
**Description:** Your professional seniority level

**Examples:**
```yaml
seniority: "senior"      # Senior individual contributor
seniority: "staff"       # Staff/tech lead level
seniority: "principal"   # Principal engineer
```

### identity.primary_domains

**Type:** List of strings (1-5 items)  
**Required:** Yes  
**Description:** Your core areas of expertise that guide content relevance

**Examples:**
```yaml
primary_domains:
  - "Cloud Computing"
  - "Distributed Systems"
  - "Software Architecture"
```

**Best Practices:**
- List 2-4 domains for focused content
- Use broad categories that encompass multiple topics
- Order by importance (most important first)

### identity.target_audience

**Type:** String  
**Required:** Yes  
**Description:** Who you're writing for - defines content tone and complexity

**Examples:**
```yaml
target_audience: "Software engineers and technical leads interested in scalable systems"
target_audience: "Engineering leaders and aspiring managers"
target_audience: "Data scientists and ML engineers building production systems"
```

### identity.positioning

**Type:** String  
**Required:** Yes  
**Description:** Your unique value proposition - what makes your perspective valuable

**Examples:**
```yaml
positioning: "Sharing practical lessons from building and scaling distributed systems in production"
positioning: "Helping technical leaders build better teams and make smarter architectural decisions"
positioning: "Demystifying machine learning deployment for software engineers"
```

### identity.excluded_topics

**Type:** List of strings  
**Required:** No (defaults to empty list)  
**Description:** Topics to avoid in generated content

**Examples:**
```yaml
excluded_topics:
  - "Politics"
  - "Religion"
  - "Controversial social issues"
  - "Personal life details"
  - "Salary discussions"
  - "Company-specific internal matters"
```

---

## Behavior Configuration

The behavior section defines adaptive patterns that guide how content is created. These can evolve based on engagement and style learning.

### behavior.active_topics

**Type:** List of strings  
**Required:** No (defaults to empty list)  
**Description:** Specific topics you're currently interested in writing about

**Examples:**
```yaml
active_topics:
  - "AWS architecture patterns"
  - "Microservices design"
  - "Database optimization"
  - "CI/CD best practices"
```

**Best Practices:**
- List 5-10 specific topics
- Update periodically to keep content fresh
- Be more specific than primary_domains

### behavior.hook_patterns

**Type:** List of strings  
**Required:** No (defaults to empty list)  
**Description:** Preferred ways to open posts and grab attention

**Examples:**
```yaml
hook_patterns:
  - "Personal debugging story"
  - "Production incident lesson"
  - "Contrarian technical take"
  - "Before/after comparison"
  - "Common mistake to avoid"
  - "Question to spark discussion"
  - "Framework or mental model"
```

**Common Hook Patterns:**
- Personal experience story
- Contrarian or unpopular opinion
- Practical tip or lesson learned
- Question to audience
- Before/after transformation
- Common mistake to avoid
- Framework or mental model
- Data or statistics
- Industry trend observation

### behavior.posting_windows

**Type:** List of time windows  
**Required:** No (defaults to empty list)  
**Description:** Preferred times for content generation (in 24-hour format)

**Structure:**
```yaml
posting_windows:
  - start_hour: 9    # 0-23
    end_hour: 11     # Must be greater than start_hour
  - start_hour: 14
    end_hour: 16
```

**Best Practices:**
- Choose 1-2 windows per day
- Morning windows (8-11) often get good engagement
- Afternoon windows (14-17) catch different time zones
- Consider your target audience's time zones

### behavior.emoji_frequency

**Type:** Enum  
**Required:** No (defaults to "moderate")  
**Valid Values:** `none`, `low`, `moderate`, `high`  
**Description:** How often to use emojis in posts

**Guidelines:**
- `none`: No emojis (very formal/academic)
- `low`: 1-2 emojis per post (professional)
- `moderate`: 3-5 emojis per post (balanced)
- `high`: 6+ emojis per post (casual/expressive)

**Examples:**
```yaml
emoji_frequency: "low"       # Technical/formal content
emoji_frequency: "moderate"  # Professional but approachable
emoji_frequency: "high"      # Casual, personal brand
```

### behavior.comment_depth

**Type:** Enum  
**Required:** No (defaults to "detailed")  
**Valid Values:** `brief`, `moderate`, `detailed`  
**Description:** How much detail to include in engagement and responses

**Guidelines:**
- `brief`: Short, concise responses (1-2 sentences)
- `moderate`: Balanced responses (2-4 sentences)
- `detailed`: Thorough, comprehensive responses (4+ sentences)

**Examples:**
```yaml
comment_depth: "brief"     # Quick, punchy style
comment_depth: "detailed"  # Thoughtful, comprehensive style
```

### behavior.vocabulary_bias

**Type:** Enum  
**Required:** No (defaults to "professional")  
**Valid Values:** `casual`, `professional`, `technical`, `academic`  
**Description:** Overall vocabulary and language style

**Guidelines:**
- `casual`: Conversational, everyday language
- `professional`: Business-appropriate, polished
- `technical`: Industry jargon, technical terms
- `academic`: Formal, research-oriented

**Examples:**
```yaml
vocabulary_bias: "technical"     # For deep technical content
vocabulary_bias: "professional"  # For leadership content
vocabulary_bias: "casual"        # For personal brand building
```

### behavior.engagement_style

**Type:** Enum  
**Required:** No (defaults to "thoughtful")  
**Valid Values:** `reactive`, `thoughtful`, `proactive`  
**Description:** How you engage with your audience

**Guidelines:**
- `reactive`: Responds to trends and current events
- `thoughtful`: Measured, reflective content
- `proactive`: Forward-thinking, trend-setting

**Examples:**
```yaml
engagement_style: "thoughtful"  # Measured, reflective posts
engagement_style: "proactive"   # Thought leadership
```

---

## Example Profiles

### Senior Engineer (Technical Focus)

```yaml
profile_id: "example-senior-engineer"
name: "Senior Software Engineer Profile"
description: "Technical-focused profile for senior engineers"
version: 1
enabled: true
created_at: "2024-01-15T10:00:00"
last_updated: "2024-01-15T10:00:00"

identity:
  headline: "Senior Software Engineer | Cloud Architecture | Distributed Systems"
  seniority: "senior"
  primary_domains:
    - "Cloud Computing"
    - "Distributed Systems"
    - "Software Architecture"
  target_audience: "Software engineers and architects"
  positioning: "Sharing practical lessons from building scalable systems"
  excluded_topics:
    - "Politics"
    - "Religion"

behavior:
  active_topics:
    - "AWS architecture patterns"
    - "Microservices design"
    - "Database optimization"
  hook_patterns:
    - "Personal debugging story"
    - "Production incident lesson"
  posting_windows:
    - start_hour: 9
      end_hour: 11
  emoji_frequency: "low"
  comment_depth: "detailed"
  vocabulary_bias: "technical"
  engagement_style: "thoughtful"
```

### Tech Lead (Leadership Focus)

```yaml
profile_id: "example-tech-lead"
name: "Tech Lead Profile"
description: "Leadership-focused profile for tech leads"
version: 1
enabled: true
created_at: "2024-01-15T10:00:00"
last_updated: "2024-01-15T10:00:00"

identity:
  headline: "Tech Lead | Engineering Manager | Building High-Performing Teams"
  seniority: "staff"
  primary_domains:
    - "Engineering Leadership"
    - "Team Building"
    - "Technical Strategy"
  target_audience: "Engineering leaders and aspiring managers"
  positioning: "Helping technical leaders build better teams"
  excluded_topics:
    - "Politics"
    - "Salary discussions"

behavior:
  active_topics:
    - "Team leadership strategies"
    - "Code review best practices"
    - "Mentorship and coaching"
  hook_patterns:
    - "Leadership lesson learned"
    - "Question to spark discussion"
  posting_windows:
    - start_hour: 8
      end_hour: 10
  emoji_frequency: "moderate"
  comment_depth: "detailed"
  vocabulary_bias: "professional"
  engagement_style: "thoughtful"
```

---

## Profile Management

### Directory Structure

```
profiles/
├── README.md                          # This file
├── example-senior-engineer.yaml       # Example: Technical focus
├── example-tech-lead.yaml            # Example: Leadership focus
├── active/                           # Active profiles used by the system
│   └── my-profile.yaml
├── backups/                          # Automatic backups
│   └── my-profile_20240115_100000.yaml
└── versions/                         # Version history
    └── my-profile_v1.yaml
```

### Creating a New Profile

1. Start with an example profile that matches your style
2. Copy it to a new file with your desired profile ID
3. Customize all fields to match your professional identity
4. Validate the profile (the system will check on load)
5. Move it to `profiles/active/` to activate

### Updating a Profile

**Identity Changes** (rare):
- Manually edit the YAML file
- Increment the version number
- Update the `last_updated` timestamp

**Behavior Changes** (common):
- The system can learn and update behavior automatically
- Manual updates are also supported
- Version is auto-incremented on behavior updates

### Validation Rules

The system validates profiles on load:

1. **Required Fields**: All required fields must be present
2. **Field Types**: Values must match expected types
3. **Enums**: Enum values must be from valid options
4. **Ranges**: Numeric values must be within valid ranges
5. **Timestamps**: Must be valid ISO 8601 format
6. **Profile ID**: Must be unique and valid format

---

## Best Practices

### Identity Configuration

1. **Be Specific**: Clear, specific identity helps generate relevant content
2. **Stay Consistent**: Identity should rarely change
3. **Know Your Audience**: Target audience drives tone and complexity
4. **Define Boundaries**: Use excluded_topics to avoid unwanted content

### Behavior Configuration

1. **Start Conservative**: Begin with moderate settings, adjust based on results
2. **Update Regularly**: Refresh active_topics every few weeks
3. **Match Your Style**: Choose vocabulary_bias that matches your natural voice
4. **Test Hook Patterns**: Try different hooks to see what resonates

### Content Quality

1. **Authenticity**: Configure behavior to match your real writing style
2. **Consistency**: Keep settings consistent with your professional brand
3. **Engagement**: Choose posting_windows when your audience is active
4. **Evolution**: Let behavior adapt based on what works

---

## Troubleshooting

### Profile Won't Load

**Error**: "Profile file not found"
- Check file is in correct directory
- Verify filename matches profile_id

**Error**: "Invalid YAML format"
- Check YAML syntax (indentation, colons, quotes)
- Validate with a YAML linter

**Error**: "Validation failed"
- Check all required fields are present
- Verify enum values are valid
- Ensure timestamps are ISO 8601 format

### Content Not Matching Style

1. Review vocabulary_bias setting
2. Check hook_patterns are appropriate
3. Verify active_topics are specific enough
4. Consider running style learning on your past posts

### Low Engagement

1. Adjust posting_windows to better times
2. Try different hook_patterns
3. Make active_topics more specific
4. Review target_audience definition

---

## Advanced Configuration

### Multiple Profiles

You can maintain multiple profiles for different personas:

```
profiles/active/
├── technical-expert.yaml      # Deep technical content
├── team-leader.yaml          # Leadership content
└── industry-thought.yaml     # Thought leadership
```

Switch between profiles by enabling/disabling them or configuring which profile the system uses.

### Style Learning

The system can analyze your past LinkedIn posts to automatically configure behavior settings:

1. Provide 10-20 of your recent posts
2. System extracts vocabulary patterns, hooks, emoji usage
3. Behavior configuration is updated automatically
4. Review and adjust as needed

### Version History

The system maintains version history in `profiles/versions/`:
- Each behavior update creates a new version
- Versions are timestamped
- You can rollback to previous versions if needed

---

## Support

For issues or questions:
1. Check validation error messages
2. Review example profiles
3. Verify YAML syntax
4. Check system logs for detailed errors

## Related Documentation

- [Requirements Document](../.kiro/specs/linkedin-content-assistant/requirements.md)
- [Design Document](../.kiro/specs/linkedin-content-assistant/design.md)
- [Configuration Guide](../config/README.md)
