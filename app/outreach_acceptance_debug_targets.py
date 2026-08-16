from app.outreach_acceptance_store import (
    load_acceptance_targets,
)


def print_acceptance_targets(
    source_job_id: str,
) -> None:
    targets = load_acceptance_targets(
        source_job_id=source_job_id
    )

    print("")
    print("ACCEPTANCE TARGETS")
    print("==================")
    print("source_job_id:", source_job_id)
    print("count:", len(targets))

    for index, target in enumerate(
        targets,
        start=1,
    ):
        print("")
        print(
            f"[{index}/{len(targets)}]"
        )
        print(
            "target_id:",
            target.get("target_id"),
        )
        print(
            "account_id:",
            target.get("account_id"),
        )
        print(
            "target_status:",
            target.get("target_status"),
        )
        print(
            "connect_status:",
            target.get("connect_status"),
        )
        print(
            "acceptance_status:",
            target.get("acceptance_status"),
        )
        print(
            "linkedin_url:",
            target.get("linkedin_url"),
        )
