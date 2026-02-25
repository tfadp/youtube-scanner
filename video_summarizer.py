"""AI-powered video summarization using Claude API"""

import re
import anthropic


def generate_summaries(outperformers: list, api_key: str) -> list:
    """
    Generate 1-2 sentence summaries for each outperformer.
    Includes brief context about the YouTuber.

    Batches all videos into a single Claude call for cost efficiency.
    Returns the same list with .summary populated on each outperformer.
    """
    if not outperformers:
        return outperformers

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_summary_prompt(outperformers)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    _parse_and_attach_summaries(message.content[0].text, outperformers)

    return outperformers


def _build_summary_prompt(outperformers: list) -> str:
    """Build batch summarization prompt."""
    video_blocks = []
    for i, op in enumerate(outperformers, 1):
        channel_about = ""
        if op.channel.about:
            channel_about = f"\n   Channel About: {op.channel.about[:300]}"

        video_blocks.append(f"""[{i}]
   Title: {op.video.title}
   Channel: {op.channel.name} ({op.channel.category}, {op.channel.subscribers:,} subscribers){channel_about}
   Description: {op.video.description[:400] if op.video.description else '(none)'}""")

    videos_text = "\n\n".join(video_blocks)

    return f"""For each numbered video below, provide:
1. A 1-2 sentence summary of what the video is about based on its title and description.
2. A brief note about who the YouTuber/channel is.

Combine both into a single concise paragraph (max 3 sentences total).
If the description is empty, summarize based on the title alone.
Do not speculate about content not mentioned in the title or description.

Format your response as:
[1] <summary>
[2] <summary>
...

VIDEOS:

{videos_text}"""


def _parse_and_attach_summaries(response_text: str, outperformers: list):
    """Parse Claude's numbered response and attach to outperformers."""
    pattern = r'\[(\d+)\]\s*(.*?)(?=\[\d+\]|\Z)'
    matches = re.findall(pattern, response_text, re.DOTALL)

    summary_map = {}
    for num_str, summary in matches:
        idx = int(num_str) - 1
        summary_map[idx] = summary.strip()

    for i, op in enumerate(outperformers):
        if i in summary_map:
            op.summary = summary_map[i]
