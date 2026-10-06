"""Conservative sender classification for LinkedIn conversation snapshots."""

import unicodedata


def _name_tokens(value: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", str(value or ""))
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return sorted(plain.casefold().split())


def same_person_name(left: str, right: str) -> bool:
    left_tokens = _name_tokens(left)
    right_tokens = _name_tokens(right)
    return bool(left_tokens and right_tokens and left_tokens == right_tokens)


def classify_message_direction(
    *,
    class_evidence: str,
    author: str,
    account_name: str,
    unread_name: str,
    text_value: str,
    sent_message_text: str,
) -> str:
    """Return own, incoming, or unknown; unknown is never a verified reply."""
    classes = class_evidence.casefold().split()
    if any(
        token.endswith(("--is-me", "--from-me", "--outgoing", "--is-self"))
        or token == "from-me"
        for token in classes
    ):
        return "own"
    if same_person_name(author, account_name):
        return "own"
    if sent_message_text and text_value == sent_message_text:
        return "own"
    if any(token.endswith(("--is-other", "--incoming")) for token in classes):
        return "incoming"
    if same_person_name(author, unread_name):
        return "incoming"
    return "unknown"
