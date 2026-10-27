# WorkBuddy Desktop Pet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows x64 desktop pet driven by real WorkBuddy lifecycle events, with status animation, user-action reminders, completion notifications, and click-to-open behavior.

**Architecture:** A dependency-light hook collector writes projected events to a bounded local spool. A pure reducer derives per-session and aggregate state; a separate PySide6 UI presents that state. WorkBuddy plugin compatibility is established by live probes before integration is claimed as working.

**Tech Stack:** Python 3.12+, PySide6 >=6.8,<7, pytest, PyInstaller; Windows 10/11 x64.

**Spec:** `docs/plans/2026-10-27-workbuddy-desktop-pet-design.md`

## Global Constraints

- WorkBuddy only; no Codex integration.
- Seven business states: `idle`, `thinking`, `working`, `waiting`, `review`, `done`, `failed`; connectivity is a separate `disconnected` / `stale` indicator.
- Windows 11 / Windows 10 x64; Chinese product copy.
- Raw hook input at most 64 KiB; projected event at most 4 KiB; schema version 1.
- Per-session spool file names use the first 24 hexadecimal characters of SHA-256 of the session identifier. Keep at most two 2 MiB files per session and at most 32 sessions.
- Collector lock acquisition is bounded to 50 ms; collector failure never supplies a tool approval or rejection decision.
- Retain only event shape, identifiers, timestamp, tool category, and notification category. No prompts, replies, tool arguments, titles, file bodies, credentials, or personal paths.
- Running states with no event for 120 seconds show a stale indicator; waiting/review and terminal states are not converted into successful completion by a timer.
- Display priority: `review > waiting > failed > working > thinking > unread done > idle`.
- Drag threshold is 6 logical pixels. Startup-at-login defaults to off. Runtime state is under `%LOCALAPPDATA%/WorkBuddyDesktopPet`.
- No redistribution of white-dragon character assets. No auto-approval, chat, billing estimates, cloud sync, or session deep links in the first release.

## Review Focus

1. Events from a previous turn arrive after a new turn: reject by verified turn identity or source timestamp; disclose limitations where source metadata is absent. Owned by Task 3.
2. WorkBuddy already has unrelated hooks/plugins, or the user changes configuration after installation: preserve unrelated changes on install and uninstall. Owned by Task 1.
3. Concurrent hooks and spool rotation interleave with a partial or malformed line: bound collector latency and continue reading valid subsequent records. Owned by Task 2.
4. A child session finishes while its parent is still active: no parent completion notification. Owned by Task 3.
5. A saved position belongs to a removed monitor or the selected executable is missing: restore a visible position and report the invalid path without shell interpolation. Owned by Task 4.

---

## File Structure

```text
src/workbuddy_pet/
  cli.py                # CLI dispatch without eager Qt import
  events.py             # Event data and whitelist projection
  spool.py              # Bounded writer and incremental reader
  state.py              # Pure session reducer and aggregate display
  integration.py        # Owned plugin configuration and backups
  windows.py            # Executable validation and foreground behavior
  settings.py           # Atomic local settings and position clamping
  ui/pet.py             # Transparent window and original basic mascot
  ui/tray.py            # Tray actions and notification presentation
  ui/settings.py        # Path, scale, connection status, notification settings
integrations/workbuddy/ # Verified formal plugin template and instructions
tests/                  # Synthetic protocol/state/configuration/GUI tests
docs/compatibility.md   # Actual desktop-version probe results
tools/build_windows.py  # Directory-based Windows packaging
.github/workflows/ci.yml
pyproject.toml
```

## Task 1: Validate WorkBuddy Hooks and Preserve User Configuration

**Files:** Create `src/workbuddy_pet/integration.py`, `integrations/workbuddy/README.md`, `docs/compatibility.md`, `tests/test_integration.py`, and `pyproject.toml`. Add plugin manifest/configuration files only after verifying their required locations and schema.

**Interfaces:** Produce `merge_plugin_config(existing: dict, plugin_id: str, entry: dict) -> dict`, `remove_plugin_config(existing: dict, plugin_id: str, installed_entry: dict) -> dict`, and `probe_compatibility(workbuddy_exe: Path) -> CompatibilityReport`. `CompatibilityReport` records app version, verified events, unverified events, and non-content diagnostic codes.

- [ ] Write `test_merge_preserves_unrelated_hooks` and `test_uninstall_preserves_changes_after_install`: unrelated plugin/hook values must remain exactly equal; removing our plugin must preserve entries added after installation.
- [ ] Run `python -m pytest tests/test_integration.py -q`; confirm the unimplemented interfaces fail.
- [ ] Implement owned-entry merge/removal, atomic replacement, and a backup whose contents are never added to Git.
- [ ] Read the installed WorkBuddy version and verify the formal plugin format against the current official documentation and a live registration probe. Do not change WorkBuddy security or permission policy.
- [ ] Use a simple user-triggered task to verify candidate events; write only version, event names, structural field names, and support results into `docs/compatibility.md`. Mark unobserved events unverified; never fabricate successful probes.
- [ ] Run the configuration tests and check that no real local configuration or event payload was staged. Commit as `feat: validate WorkBuddy hook integration`.

## Task 2: Implement the Minimal Collector and Bounded Event Spool

**Files:** Create `src/workbuddy_pet/events.py`, `src/workbuddy_pet/spool.py`, `src/workbuddy_pet/cli.py`, `tests/test_events.py`, `tests/test_spool.py`; extend `pyproject.toml` with package and test metadata.

**Interfaces:** `Event` contains schema/id/time/session/kind and the optional structural fields from the spec. Produce `project_event(event_name: str, payload: Mapping[str, object], now: float) -> Event | None`, `write_event(root: Path, event: Event) -> bool`, `SpoolReader(root: Path).poll() -> list[Event]`, and `hook_main(event_name: str, stdin: BinaryIO, root: Path) -> int`.

- [ ] Write `test_projection_excludes_content`: include fake prompts, tool arguments, paths and secret-looking strings in synthetic input; assert none appear in the serialized event. Add size-boundary tests at 64 KiB and 4 KiB and rejection of incorrect field types.
- [ ] Write `test_reader_keeps_partial_line`, `test_reader_skips_malformed_line`, `test_reader_handles_rotation_and_truncation`, and `test_concurrent_writer_lock_timeout`: each complete valid record is read once, malformed records do not block later events, and lock acquisition does not exceed the bounded collector budget.
- [ ] Run `python -m pytest tests/test_events.py tests/test_spool.py -q`; confirm meaningful failures before implementing the collector.
- [ ] Implement field projection, safe hashed queue names, per-session locking, bounded files/session count, incremental reads and deduplication. Dispatch `--hook EVENT` before importing PySide6; output no approval JSON.
- [ ] Re-run tests, invoke the collector with a synthetic input file, and confirm normal exit plus an event that fits the whitelist. Commit as `feat: collect bounded WorkBuddy lifecycle events`.

## Task 3: Implement Session State and Reminder Decisions

**Files:** Create `src/workbuddy_pet/state.py` and `tests/test_state.py`.

**Interfaces:** Produce `SessionState`, `Reminder(id: str, session_id: str, kind: str)`, `DisplayState`, `reduce_event(sessions: Mapping[str, SessionState], event: Event) -> dict[str, SessionState]`, `derive_display(sessions: Mapping[str, SessionState], now: float) -> DisplayState`, and `acknowledge(sessions: Mapping[str, SessionState], reminder_id: str) -> dict[str, SessionState]`. `DisplayState` separates business state, connection status and unread reminders.

- [ ] Write a table-driven test for each verified event mapping and the exact display priority from the spec. Include two sessions whose active states differ.
- [ ] Write `test_subagent_stop_does_not_complete_parent`, `test_duplicate_stop_notifies_once`, `test_late_tool_event_does_not_reopen_terminal_turn`, and `test_old_turn_event_after_new_prompt_is_ignored_when_identified`.
- [ ] Write `test_running_state_stales_at_120_seconds` and `test_waiting_or_completed_state_does_not_time_out_to_success`; compare 119.999 and 120 seconds without sleeping.
- [ ] Run `python -m pytest tests/test_state.py -q`, implement pure transitions and acknowledgement, and re-run until all assertions pass. Where the probe lacks turn metadata, add an explicit diagnostic rather than claiming perfect attribution.
- [ ] Confirm the reducer has no Qt or filesystem dependencies. Commit as `feat: derive desktop pet state and reminders`.

## Task 4: Implement Windows Paths, Settings and the Desktop Pet

**Files:** Create `src/workbuddy_pet/windows.py`, `src/workbuddy_pet/settings.py`, `src/workbuddy_pet/ui/pet.py`, `src/workbuddy_pet/ui/tray.py`, `src/workbuddy_pet/ui/settings.py`, `tests/test_windows.py`, `tests/test_settings.py`, and `tests/test_ui.py`.

**Interfaces:** Produce `validate_workbuddy_path(path: Path) -> Path`, `open_workbuddy(path: Path) -> bool`, `clamp_position(position: tuple[int, int], size: tuple[int, int], screens: Sequence[Rect]) -> tuple[int, int]`, `load_settings(root: Path) -> Settings`, and `save_settings(root: Path, value: Settings) -> None`. `PetWindow.set_display(state: DisplayState) -> None` consumes Task 3 output; `PetWindow` emits open/acknowledge/settings requests without directly changing reducer data.

- [ ] Test invalid/missing executable paths, paths containing spaces and shell metacharacters, malformed settings, and a saved position on a disconnected monitor. Expected results: no shell execution, safe defaults or a clear path error, and a visible restored position.
- [ ] Test clicks below the 6-pixel threshold and drags above it, repeated UI updates without duplicate reminders, and notification-disabled behavior with the in-window unread indicator preserved.
- [ ] Run `python -m pytest tests/test_windows.py tests/test_settings.py tests/test_ui.py -q`; implement the APIs and re-run.
- [ ] Draw an original basic mascot with seven distinguishable states, a transparent window, drag/position handling and tray actions. Keep animation on the Qt event loop; spool I/O must not block painting.
- [ ] Verify a real installed WorkBuddy window can be restored to the foreground, and document Windows foreground restrictions if the OS refuses focus. Confirm the settings window can close without terminating the pet and that the tray exit stops the app cleanly.
- [ ] Commit as `feat: add Windows desktop pet and tray interface`.

## Task 5: Integrate the Application and Verify Real Tasks

**Files:** Extend `src/workbuddy_pet/cli.py`, add `src/workbuddy_pet/app.py`, `tests/test_app.py`, and update `README.md`, `docs/compatibility.md`, and `integrations/workbuddy/README.md`.

**Interfaces:** Produce `run_app(root: Path, demo: bool = False) -> int` and `diagnose(root: Path) -> DiagnosticReport`. Diagnostics expose only app version, event counts, support states and safe error codes. `--demo` displays an explicit Chinese “演示” marker and uses synthetic events.

- [ ] Write an integration test that feeds a synthetic submit/tool/stop sequence through collector, spool and reducer and observes exactly one unread completion. Add a scenario with a child session stopping first.
- [ ] Write a test in which integration fails: the hook still exits normally and no tool approval/rejection payload is produced. Test missing plugin, waiting for first event, and stale-running diagnostics separately.
- [ ] Run `python -m pytest tests/test_app.py -q`, implement application wiring and re-run all tests.
- [ ] Complete real Windows checks for task submission, tool execution, a completion reminder, waiting for approval if the event is supported, clicking to open WorkBuddy, and exiting the pet. Record the actual version and result for each item.
- [ ] Update the README to separate implemented, live-verified and unsupported capabilities. Commit as `feat: connect the desktop pet to live WorkBuddy tasks`.

## Task 6: Package and Publish the Windows Build

**Files:** Create `tools/build_windows.py`, `.github/workflows/ci.yml`, `docs/releasing.md`; update dependency lock data and `README.md`.

**Interfaces:** `python tools/build_windows.py` produces `dist/WorkBuddyDesktopPet/WorkBuddyDesktopPet.exe` and its directory dependencies. `WorkBuddyDesktopPet.exe --hook EVENT` and `--diagnose` retain the collector-first behavior from Task 2. CI runs the same tests on Windows x64 without real WorkBuddy data.

- [ ] Run the complete synthetic test suite on Windows CI with the supported Python version and locked dependency versions.
- [ ] Build a directory-based PyInstaller artifact and run its diagnostic and synthetic-hook modes. Verify that the Hook path does not create a GUI window or unpack Qt on every invocation.
- [ ] Start the packaged desktop pet, test the real WorkBuddy integration and exit behavior, and check that runtime files remain outside the program directory.
- [ ] Inspect the tracked tree and packaged artifact for accidental local settings, prompts, logs, tokens and unlicensed assets. Produce SHA-256 checksums for the distributable.
- [ ] Document installation, plugin registration/reload, diagnostics and uninstall behavior; publish a prerelease only when the live capability record supports its claims. Commit as `build: package and verify the Windows desktop pet`.

## Plan Review and Execution

The user approved direct implementation in the current session on 2026-10-27. No subagents were used. The optional execution skills named in the standard header were unavailable; implementation was performed directly as requested.

Execution results:

- Collector, spool, state reducer, configuration transactions, desktop UI, tray, settings, diagnostics and packaging implemented.
- 36 local automated tests passed, including malformed input, queue rotation, lock contention, multi-session state, acknowledgement, offscreen UI and configuration preservation.
- Formal plugin and marketplace manifests passed the validator shipped with WorkBuddy 5.9.2 / Agent CLI 2.165.0.
- Packaged collector, PowerShell stdin/argument forwarding, GUI startup and capture passed after correcting an ICU packaging collision.
- The user triggered a real command task; SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop and Notification events were observed. The live pet reached done/connected with one unread completion, and a subsequent prompt changed it to thinking.
- Waiting/review, failure and child-session transitions have synthetic coverage; corresponding live desktop events remain unverified. See `docs/compatibility.md`.
- GitHub Actions is configured to run tests, build and verify the executable. Its remote outcome must be reported separately after the workflow actually runs.

The unchecked task steps above are retained as the original plan, not an assertion that every live capability was observed. Current verification evidence is summarized here and in the compatibility record.
