"""Claude API integration for generating content ideas"""

import anthropic
from analyzer import get_pattern_summary


def generate_ideas(outperformers: list, api_key: str) -> str:
    """
    Send top outperformers to Claude and get content ideas.

    Returns Claude's generated content ideas as a string.
    """
    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_prompt(outperformers)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text


def build_prompt(outperformers: list) -> str:
    """Build the prompt for Claude"""

    # Get pattern/theme summary
    summary = get_pattern_summary(outperformers)

    # Format outperformers
    outperformer_text = ""
    for i, op in enumerate(outperformers[:10], 1):
        outperformer_text += f"""
{i}. "{op.video.title}"
   Channel: {op.channel.name} ({op.channel.category})
   Subscribers: {op.channel.subscribers:,} | Views: {op.video.views:,}
   Ratio: {op.ratio:.1f}x
   Themes: {', '.join(op.themes) if op.themes else 'none'}
   Patterns: {', '.join(op.title_patterns) if op.title_patterns else 'none'}
"""

    # Format trending themes
    themes_text = ""
    for theme, count in summary["themes"].items():
        themes_text += f"  • {theme}: {count} videos\n"

    # Format trending patterns
    patterns_text = ""
    for pattern, count in summary["patterns"].items():
        patterns_text += f"  • {pattern}: {count} videos\n"

    prompt = f"""You are a content strategist for Overtime, a sports media company targeting Gen Z audiences.

I've analyzed recent YouTube videos that significantly outperformed their channel's subscriber count (views > subscribers). Here are the top performers and trending patterns:

## TOP OUTPERFORMING VIDEOS
{outperformer_text}

## TRENDING THEMES (across all outperformers)
{themes_text if themes_text else "  No clear theme patterns"}

## TRENDING TITLE PATTERNS (across all outperformers)
{patterns_text if patterns_text else "  No clear title patterns"}

Based on these insights, generate 5 specific content ideas for Overtime's properties:
- **Overtime** (main brand): Gen Z sports culture, viral moments, athlete lifestyle
- **Overtime Elite (OTE)**: Professional basketball development league for elite high school players
- **OT7**: 7-on-7 football league
- **OT Select**: Women's basketball content

For each idea, provide:
1. **Ready-to-use title** (incorporate winning patterns)
2. **Property**: Which Overtime property this is for
3. **Format/Length**: Short-form (<60s), mid-form (2-5min), or long-form (10+min)
4. **Why it works**: Connect to the patterns and themes that are performing
5. **Talent/Assets needed**: What's required to produce this

Focus on ideas that:
- Leverage the patterns that are clearly working (first-person action, expose/truth, challenge formats)
- Can realistically be produced with Overtime's existing talent and access
- Feel authentic to Gen Z audiences
- Have viral potential based on what's already working"""

    return prompt
