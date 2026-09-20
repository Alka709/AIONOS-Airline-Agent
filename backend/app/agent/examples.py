"""The three supplied sample conversations.

They are used only as style and tone examples for the response generator.
They are not customer data, not bookings, and not policy. No flight, name or
entitlement mentioned here may be treated as a fact about a real customer.
"""

from __future__ import annotations

from typing import Dict, List

SAMPLE_CONVERSATIONS: List[Dict[str, str]] = [
    {
        "id": "A",
        "customer": "My flight got cancelled and no one told me anything!",
        "agent": (
            "I completely understand the frustration — I can see flight SK-190 was cancelled "
            "due to operational reasons. I can rebook you on the next available flight at no "
            "extra cost, or process a full refund. Which would you prefer?"
        ),
    },
    {
        "id": "B",
        "customer": "I want compensation, this delay ruined my whole day.",
        "agent": (
            "I'm sorry for the disruption. Your flight was delayed 3 hours 40 minutes, which "
            "qualifies for a meal voucher and lounge access under our policy. I've applied both "
            "to your account now."
        ),
    },
    {
        "id": "C",
        "customer": (
            "This is unacceptable, I'm going to file a formal complaint and consider legal "
            "action over this."
        ),
        "agent": (
            "I hear you, and I'm sorry this has been such a frustrating experience. I want to "
            "make sure this gets the right attention — I'm escalating this to our specialist "
            "support team right now, and they'll reach out to you directly."
        ),
    },
]


def format_examples() -> str:
    """Render the samples for use inside a prompt."""
    blocks = []
    for sample in SAMPLE_CONVERSATIONS:
        blocks.append(
            f"Example {sample['id']}\n"
            f"Customer: {sample['customer']}\n"
            f"Agent: {sample['agent']}"
        )
    return "\n\n".join(blocks)
