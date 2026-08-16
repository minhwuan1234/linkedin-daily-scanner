from __future__ import annotations


DEFAULT_MESSAGE_TEMPLATE = """Hi {first_name},

I wanted to reach out regarding...
"""


def build_message(
    first_name: str,
    template: str | None = None,
) -> str:
    """
    STEP 3B — personalize a message.

    Current supported variable:
        {first_name}

    This function only returns text.
    It does NOT interact with LinkedIn.
    """

    cleaned_first_name = (
        str(
            first_name
            or ""
        )
        .strip()
    )

    if not cleaned_first_name:
        raise ValueError(
            "First name cannot be empty."
        )

    active_template = (
        template
        if template is not None
        else DEFAULT_MESSAGE_TEMPLATE
    )

    if not str(
        active_template
        or ""
    ).strip():
        raise ValueError(
            "Message template cannot be empty."
        )

    try:
        message = (
            active_template
            .format(
                first_name=(
                    cleaned_first_name
                )
            )
        )

    except KeyError as exc:
        raise ValueError(
            "Unsupported template variable: "
            f"{exc}"
        ) from exc

    return message
