from app.rag.knowledge_base import get_knowledge_base


def retrieve_recovery_guidance(
    *,
    failure_code: str | None = None,
    failure_reason: str | None = None,
    status: str | None = None,
    limit: int = 3,
) -> list[dict]:
    text = " ".join(
        value.lower()
        for value in (failure_code, failure_reason, status)
        if value
    )

    matches = []

    for document in get_knowledge_base():
        score = sum(
            1 for keyword in document["keywords"]
            if keyword.lower() in text
        )

        if score:
            matches.append((score, document))

    matches.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "id": document["id"],
            "title": document["title"],
            "guidance": document["guidance"],
            "score": score,
        }
        for score, document in matches[:limit]
    ]
