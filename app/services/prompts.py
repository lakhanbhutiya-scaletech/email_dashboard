"""The JSON-emitting analysis prompt pinned at agent-creation time (spec §6)."""

SYSTEM_PROMPT = """\
You are a sales-mailbox analyst. Use the tools outlook_list_messages and \
outlook_get_message to read the user's Outlook inbox AND their Sent items for the \
requested time window, so you can see both the client's message and how the user \
replied to it.

Then reply with ONLY a single JSON object — no prose, no explanations, no markdown \
code fences — matching EXACTLY this schema:

{
  "window_hours": number,
  "incoming_count": number,
  "replied_count": number,
  "avg_response_minutes": number | null,
  "high_priority_count": number,
  "sentiment_summary": string,
  "threads": [
    {
      "from": string,                 // sender name <email>
      "subject": string,
      "received_at": string,          // ISO-8601 of the incoming message
      "priority": "high" | "medium" | "low",
      "priority_reason": string,      // one short phrase explaining the priority
      "incoming_excerpt": string,     // 1-2 sentence paraphrase of what the client asked
      "status": "awaiting" | "replied",
      "reply_excerpt": string | null, // 1-2 sentence paraphrase of the reply the user sent, or null if still awaiting
      "replied_at": string | null     // ISO-8601 of the reply, or null
    }
  ]
}

Priority rules:
- "high": an explicit deadline, money/contract/pricing/renewal, an upset or churning \
customer, or a hot prospect waiting on the user. These need attention now.
- "medium": normal business conversation.
- "low": FYI, newsletters, automated/no-action-needed mail.

Rules:
- Output must be valid JSON and nothing else. Do not wrap it in ``` fences.
- Include EVERY thread that had activity in the window — both those already replied \
to and those still awaiting a reply — most important first.
- high_priority_count = number of threads with priority "high" that are still "awaiting".
- excerpts must be short paraphrases (never full email bodies) and must not invent content.
- If the inbox has no messages in the window, return zeros/empty arrays, not prose.
- received_at / replied_at must be ISO-8601 timestamps.
- Keep sentiment_summary to one or two sentences.
"""

# Message sent for a run covering a specific elapsed span since the last capture
# (cron tick or manual "run now") — phrased in minutes below one hour so short
# re-sync gaps still get a precise, non-overlapping window.
SINCE_LAST_MESSAGE_MINUTES = (
    "Analyze the last {minutes} minute(s) of my Outlook inbox and reply with "
    "ONLY the JSON object described in your instructions."
)
SINCE_LAST_MESSAGE_HOURS = (
    "Analyze the last {hours} hour(s) of my Outlook inbox and reply with "
    "ONLY the JSON object described in your instructions."
)


def build_agent_payload(
    email: str,
    model: str,
    temperature: float,
    max_tokens: int,
    memory_window: int,
) -> dict:
    """AgentCreate payload for the org's ONE shared analyzer agent (spec §3 step 0).

    `email` is an org label (domain or company name), not an employee address —
    which mailbox gets read is resolved per-request from the API key's owner.
    """
    return {
        "name": f"Outlook Analyzer — {email}",
        "model": model,
        "system_prompt": SYSTEM_PROMPT,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "tools": ["outlook_list_messages", "outlook_get_message"],
        "memory_window": memory_window,
    }


def since_last_message(minutes: int) -> str:
    """Message for a window covering exactly the elapsed time since the last
    successful capture — minutes phrasing below an hour so short re-sync gaps
    still get a precise ask, hours phrasing above it."""
    if minutes < 60:
        return SINCE_LAST_MESSAGE_MINUTES.format(minutes=minutes)
    hours = round(minutes / 60, 2)
    return SINCE_LAST_MESSAGE_HOURS.format(hours=hours)
