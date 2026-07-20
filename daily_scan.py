from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

# Đổi đúng tên file nếu runner sync Sheet hiện tại
# của bạn có tên khác.
SHEET_SYNC_SCRIPT = PROJECT_ROOT / "sync_sources.py"

UNSCANNED_SCAN_SCRIPT = (
    PROJECT_ROOT / "scan_unscanned_profiles.py"
)


def print_separator() -> None:
    print("")
    print("=" * 70)
    print("")


def run_python_script(
    script_path: Path,
    step_name: str,
) -> None:
    if not script_path.exists():
        raise FileNotFoundError(
            f"{step_name} script does not exist: "
            f"{script_path}"
        )

    print_separator()
    print(f"Starting: {step_name}")
    print(f"Script: {script_path.name}")
    print_separator()

    process = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=str(PROJECT_ROOT),
        check=False,
    )

    if process.returncode != 0:
        raise RuntimeError(
            f"{step_name} failed with exit code "
            f"{process.returncode}."
        )

    print("")
    print(f"Completed: {step_name}")


def main() -> int:
    started_at = datetime.now()

    print("")
    print("LinkedIn daily pipeline started.")
    print(
        "Started at: "
        f"{started_at.isoformat(timespec='seconds')}"
    )

    try:
        # Bước 1:
        # Đọc Google Sheet và đồng bộ URL mới
        # sang bảng linkedin_sources.
        run_python_script(
            script_path=SHEET_SYNC_SCRIPT,
            step_name="Google Sheet source sync",
        )

        # Bước 2:
        # Lấy các source enabled có
        # last_scanned_at IS NULL rồi xử lý.
        run_python_script(
            script_path=UNSCANNED_SCAN_SCRIPT,
            step_name="Unscanned LinkedIn profiles",
        )

        finished_at = datetime.now()
        duration = finished_at - started_at

        print_separator()
        print("LinkedIn daily pipeline completed.")
        print(
            "Finished at: "
            f"{finished_at.isoformat(timespec='seconds')}"
        )
        print(
            "Duration: "
            f"{duration}"
        )

        return 0

    except Exception as exc:
        finished_at = datetime.now()
        duration = finished_at - started_at

        print_separator()
        print(
            "LinkedIn daily pipeline failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        print(
            "Finished at: "
            f"{finished_at.isoformat(timespec='seconds')}",
            file=sys.stderr,
        )
        print(
            f"Duration: {duration}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
