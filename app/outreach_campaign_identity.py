"""Stable identity for a Connect campaign without a separate campaign table."""

from uuid import NAMESPACE_URL, uuid5


def campaign_id_for_name(name: str | None, *, connect_batch_id: str = "") -> str:
    """Give named campaigns one UUID; identify old unnamed runs separately."""
    normalized = " ".join(str(name or "").split()).casefold()
    if normalized:
        return str(uuid5(NAMESPACE_URL, f"linkedin-daily-scanner/campaign/{normalized}"))
    batch_id = str(connect_batch_id or "").strip()
    if batch_id:
        return str(uuid5(NAMESPACE_URL, f"linkedin-daily-scanner/legacy-connect-batch/{batch_id}"))
    return ""
