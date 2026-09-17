from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


PlatformType = Literal[
    "linkedin",
    "youtube",
]

JobType = Literal[
    "linkedin_profile_scan",
    "youtube_scan",
]


@dataclass(frozen=True)
class RoutedJob:
    """
    Kết quả sau khi một request được Job Router phân loại.
    """

    platform: PlatformType
    job_type: JobType
    required_capability: str
    input_payload: dict[str, Any]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "job_type": self.job_type,
            "required_capability": (
                self.required_capability
            ),
            "input_payload": dict(
                self.input_payload
            ),
        }


class JobRouter:
    """
    Xác định request thuộc LinkedIn hay YouTube.
    """

    LINKEDIN_PROFILE_SCAN = (
        "linkedin_profile_scan"
    )

    YOUTUBE_SCAN = "youtube_scan"

    def route(
        self,
        *,
        platform: str,
        payload: dict[str, Any],
    ) -> RoutedJob:
        cleaned_platform = str(
            platform or ""
        ).strip().lower()

        if cleaned_platform == "linkedin":
            return self._route_linkedin(
                payload=payload
            )

        if cleaned_platform == "youtube":
            return self._route_youtube(
                payload=payload
            )

        raise ValueError(
            f"Unsupported platform: {platform}"
        )

    def _route_linkedin(
        self,
        *,
        payload: dict[str, Any],
    ) -> RoutedJob:
        linkedin_url = str(
            payload.get("linkedin_url") or ""
        ).strip()

        if not linkedin_url:
            raise ValueError(
                "linkedin_url is required"
            )

        return RoutedJob(
            platform="linkedin",
            job_type="linkedin_profile_scan",
            required_capability=(
                self.LINKEDIN_PROFILE_SCAN
            ),
            input_payload={
                "linkedin_url": linkedin_url,
            },
        )

    def _route_youtube(
        self,
        *,
        payload: dict[str, Any],
    ) -> RoutedJob:
        keyword = str(
            payload.get("keyword") or ""
        ).strip()

        if not keyword:
            raise ValueError(
                "keyword is required"
            )

        filters = payload.get("filters")

        if filters is None:
            filters = {}

        if not isinstance(filters, dict):
            raise ValueError(
                "filters must be an object"
            )

        max_results_raw = payload.get(
            "max_results",
            40,
        )

        try:
            max_results = int(
                max_results_raw
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "max_results must be an integer"
            ) from exc

        if max_results < 1:
            raise ValueError(
                "max_results must be at least 1"
            )

        if max_results > 40:
            raise ValueError(
                "max_results cannot exceed 40"
            )

        return RoutedJob(
            platform="youtube",
            job_type="youtube_scan",
            required_capability=(
                self.YOUTUBE_SCAN
            ),
            input_payload={
                "keyword": keyword,
                "max_results": max_results,
                "filters": filters,
            },
        )
