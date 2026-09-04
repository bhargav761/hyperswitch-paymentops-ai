from typing import Any


def build_grounded_prompt(
    *,
    user_prompt: str,
    context: dict[str, Any],
) -> str:
    """Build an LLM prompt that explicitly constrains reasoning to trusted context."""

    guidance = context.get("recovery_guidance", [])

    guidance_text = "\n".join(
        (
            f"- [{item.get('id')}] {item.get('title')}: "
            f"{item.get('guidance')}"
        )
        for item in guidance
    )

    if not guidance_text:
        guidance_text = "- No matching recovery guidance was retrieved."

    return (
        "You are the PaymentOps AI advisory layer.\n"
        "Use the supplied PaymentOps context as the primary source of truth.\n"
        "Do not invent payment facts, incidents, recovery policies, or evidence.\n"
        "If the supplied context is insufficient, explicitly say so.\n"
        "Do not execute actions or bypass deterministic policy, security, "
        "or approval controls.\n\n"
        "PaymentOps recovery guidance:\n"
        f"{guidance_text}\n\n"
        "User request:\n"
        f"{user_prompt}\n\n"
        "Return an advisory response grounded in the supplied context."
    )
