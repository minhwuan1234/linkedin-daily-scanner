# PATCH FOR linkedin_worker.py

# 1) Add import:
from app.worker_command_store import WorkerCommandStore

# 2) In __init__, after self.events = ... add:
self.commands = WorkerCommandStore(
    settings=settings,
    worker_id=self.health.worker_id,
)
self._scan_paused = False
self._kill_current_requested = False
self._active_account_id: str | None = None

# 3) Add this method inside RoundRobinLinkedInWorker:

def _process_control_commands(self) -> None:
    while True:
        command = self.commands.claim_next_command()

        if command is None:
            return

        try:
            if command.command == "stop_scan":
                self._scan_paused = True
                self._set_live_health_state(
                    status="paused",
                    account_id=None,
                    source_id=None,
                )
                self.health.heartbeat(
                    status="paused"
                )

            elif command.command == "resume_scan":
                self._scan_paused = False
                self._set_live_health_state(
                    status="idle",
                    account_id=None,
                    source_id=None,
                )
                self.health.heartbeat(
                    status="idle"
                )

            elif command.command == "kill_current":
                self._kill_current_requested = True

                if self._active_account_id:
                    self.queue.release_account_sources(
                        account_id=self._active_account_id,
                        reason=(
                            "Current scan was killed "
                            "from the operations dashboard."
                        ),
                    )

                self.request_stop()

            else:
                raise ValueError(
                    "Unsupported worker command: "
                    f"{command.command}"
                )

            self.commands.complete(
                command_id=command.id
            )

        except Exception as exc:
            self.commands.fail(
                command_id=command.id,
                error=exc,
            )
            raise

# 4) In run_forever(), at the start of while not self._stop_requested:
self._process_control_commands()

if self._scan_paused:
    self._set_live_health_state(
        status="paused",
        account_id=None,
        source_id=None,
    )
    self.health.heartbeat(
        status="paused"
    )
    self._sleep_interruptibly(2)
    continue

# 5) At the start of run_account_turn():
self._active_account_id = account.account_id

# 6) In run_account_turn() finally block, after browser.stop():
self._active_account_id = None

# 7) At the start of each source loop, before scanning:
self._process_control_commands()

if self._kill_current_requested:
    self.queue.release_account_sources(
        account_id=account.account_id,
        reason=(
            "Current scan was killed "
            "from the operations dashboard."
        ),
    )
    break

if self._scan_paused:
    self.queue.release_account_sources(
        account_id=account.account_id,
        reason=(
            "Scanner paused from "
            "the operations dashboard."
        ),
    )
    break

# 8) In _sleep_interruptibly(), call command polling each second:
try:
    self._process_control_commands()
except Exception as exc:
    print(
        "Could not process worker command: "
        f"{type(exc).__name__}: {exc}",
        file=sys.stderr,
    )
