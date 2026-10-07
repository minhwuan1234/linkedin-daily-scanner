"""Conservative sender classification for LinkedIn conversation snapshots."""

import unicodedata
from urllib.parse import unquote, urlparse


def profile_slug_key(linkedin_url: object) -> str:
    """Compare absolute or relative LinkedIn member links without tracking."""
    try:
        value = str(linkedin_url or "").strip()
        parsed = urlparse(value)
        if parsed.hostname:
            hostname = parsed.hostname.casefold()
            if hostname != "linkedin.com" and not hostname.endswith(".linkedin.com"):
                return ""
        elif not value.startswith("/"):
            return ""
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2 or parts[0].casefold() != "in":
            return ""
        return unquote(parts[1]).casefold()
    except Exception:
        return ""


def sent_target_from_own_messages(
    events: list[dict], sent_profiles: list[dict],
) -> dict | None:
    """Match a thread only to a unique, sufficiently specific sent message."""
    by_text: dict[str, list[dict]] = {}
    for profile in sent_profiles:
        text = " ".join(str(profile.get("message_text") or "").split())
        if len(text) >= 20:
            by_text.setdefault(text, []).append(profile)
    for event in events:
        if not event.get("is_own_message"):
            continue
        text = " ".join(str(event.get("text") or "").split())
        candidates = by_text.get(text, [])
        if not candidates:
            continue
        profile_keys = {
            profile_slug_key(candidate.get("linkedin_url"))
            for candidate in candidates
        }
        if len(profile_keys) == 1 and next(iter(profile_keys), ""):
            return candidates[0]
    return None


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
