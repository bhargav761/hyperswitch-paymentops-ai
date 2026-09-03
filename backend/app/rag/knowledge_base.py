KNOWLEDGE_BASE = [
    {
        "id": "network_failure",
        "title": "Network Failure Recovery",
        "keywords": ["network", "timeout", "connection", "unavailable"],
        "guidance": "Prefer retry or connector rerouting when the failure is transient. Avoid repeated retries when provider health is degraded.",
    },
    {
        "id": "issuer_decline",
        "title": "Issuer Decline",
        "keywords": ["issuer", "decline", "insufficient_funds", "do_not_honor"],
        "guidance": "Do not repeatedly retry issuer declines. Prefer an alternative payment method or customer action.",
    },
    {
        "id": "pending_payment",
        "title": "Pending Payment",
        "keywords": ["pending", "processing", "unknown"],
        "guidance": "Reconcile the provider payment state before attempting another recovery action.",
    },
    {
        "id": "authentication_failure",
        "title": "Authentication Failure",
        "keywords": ["authentication", "auth_failed", "3ds", "authentication_failed"],
        "guidance": "Prefer customer re-authentication or an alternative payment method rather than blind retries.",
    },
]


def get_knowledge_base():
    return KNOWLEDGE_BASE.copy()
