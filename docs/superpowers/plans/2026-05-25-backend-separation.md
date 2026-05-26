# InputLab Backend Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate `D:\Downloads\InputLab\app.py` into UI, backend runtime services, centralized state, and a transport-safe API boundary so the current desktop app can keep working while preparing for a future Tauri or Electron UI.

**Architecture:** Keep Python as the source of truth for runtime behavior. Extract non-UI logic behind service modules and a typed application state store, then add an adapter layer that the current CustomTkinter UI uses first. After that, a future Tauri or Electron frontend can talk to the same Python backend through IPC without changing macro/controller behavior.

**Tech Stack:** Python 3.10, CustomTkinter, `keyboard`, `vgamepad`, `pystray`, `urllib`, JSON config, future-compatible IPC via local process transport.

---

## Target File Structure

### Existing files to keep
- `D:\Downloads\InputLab\app.py`
- `D:\Downloads\InputLab\requirements.txt`
- `D:\Downloads\InputLab\installer.iss`
- `D:\Downloads\InputLab\update.json`
- `D:\Downloads\InputLab\assets\...`

### New backend package
- `D:\Downloads\InputLab\backend\__init__.py`
- `D:\Downloads\InputLab\backend\models.py`
- `D:\Downloads\InputLab\backend\state.py`
- `D:\Downloads\InputLab\backend\config_store.py`
- `D:\Downloads\InputLab\backend\profiles.py`
- `D:\Downloads\InputLab\backend\hotkeys.py`
- `D:\Downloads\InputLab\backend\controller_service.py`
- `D:\Downloads\InputLab\backend\macro_service.py`
- `D:\Downloads\InputLab\backend\keyboard_hold_service.py`
- `D:\Downloads\InputLab\backend\updates.py`
- `D:\Downloads\InputLab\backend\overlay_service.py`
- `D:\Downloads\InputLab\backend\tray_service.py`
- `D:\Downloads\InputLab\backend\events.py`
- `D:\Downloads\InputLab\backend\app_service.py`
- `D:\Downloads\InputLab\backend\ipc_contract.py`

### New UI adapter package
- `D:\Downloads\InputLab\ui\__init__.py`
- `D:\Downloads\InputLab\ui\bindings.py`
- `D:\Downloads\InputLab\ui\presenters.py`
- `D:\Downloads\InputLab\ui\view_models.py`

### New tests
- `D:\Downloads\InputLab\tests\test_config_store.py`
- `D:\Downloads\InputLab\tests\test_profiles.py`
- `D:\Downloads\InputLab\tests\test_macro_service.py`
- `D:\Downloads\InputLab\tests\test_keyboard_hold_service.py`
- `D:\Downloads\InputLab\tests\test_app_service.py`
- `D:\Downloads\InputLab\tests\test_ipc_contract.py`

## Boundary Rules

1. `app.py` may own widget creation, visual state, and Tk event wiring only.
2. All runtime behavior must move to backend services.
3. `StringVar`, `CTkEntry`, `CTkTextbox`, `CTkButton`, and Tk callbacks must never appear in backend modules.
4. Backend modules may expose Python methods now, but all public service calls must be shaped so they can later become IPC calls.
5. UI must consume immutable snapshots or event payloads, not reach into service internals.

## Proposed Runtime Ownership

### Backend owns
- keyboard hold runtime
- macro runtime and loop execution
- controller creation and button dispatch
- hotkey registration
- profile CRUD and normalization
- config read/write
- updater fetch/install workflow
- overlay/tray orchestration state
- active status, progress, and error events

### UI owns
- widget tree
- theme and view rendering
- form input capture
- mapping backend state to labels/buttons/cards
- view switching and layout

---

### Task 1: Create the backend package skeleton

**Files:**
- Create: `D:\Downloads\InputLab\backend\__init__.py`
- Create: `D:\Downloads\InputLab\backend\models.py`
- Create: `D:\Downloads\InputLab\backend\events.py`
- Create: `D:\Downloads\InputLab\backend\ipc_contract.py`

- [ ] **Step 1: Define core data models**

Create dataclasses or typed dictionaries for:
- macro profile
- run condition
- profile statistics
- keyboard hold state
- macro progress state
- updater status
- application state snapshot

Minimum model set:
- `MacroProfile`
- `RunCondition`
- `ProfileStats`
- `KeyboardHoldState`
- `MacroRuntimeState`
- `UpdateState`
- `AppStateSnapshot`

- [ ] **Step 2: Define event types**

Create explicit event payloads for:
- `macro_status_changed`
- `macro_progress_changed`
- `keyboard_hold_changed`
- `profiles_changed`
- `update_status_changed`
- `overlay_state_changed`
- `tray_state_changed`

- [ ] **Step 3: Define the future IPC contract**

In `ipc_contract.py`, define request/response names and payload shapes for:
- `get_state`
- `apply_keyboard_mapping`
- `toggle_keyboard_hold`
- `apply_macro_profile`
- `start_macro`
- `stop_macro`
- `add_profile`
- `duplicate_profile`
- `delete_profile`
- `import_profiles`
- `export_profiles`
- `check_for_updates`
- `download_update`

This file is the stable contract for either:
- Tauri invoking Python
- Electron invoking Python

- [ ] **Step 4: Commit**

```bash
git add backend/__init__.py backend/models.py backend/events.py backend/ipc_contract.py
git commit -m "refactor: add backend contract skeleton"
```

### Task 2: Extract configuration and profile persistence

**Files:**
- Create: `D:\Downloads\InputLab\backend\config_store.py`
- Create: `D:\Downloads\InputLab\backend\profiles.py`
- Modify: `D:\Downloads\InputLab\app.py`
- Test: `D:\Downloads\InputLab\tests\test_config_store.py`
- Test: `D:\Downloads\InputLab\tests\test_profiles.py`

- [ ] **Step 1: Move config file IO out of `app.py`**

Extract logic from:
- `load_config`
- `load_config_file`
- `write_config_payload`
- `save_config`

Target responsibilities:
- `config_store.py`: file paths, JSON load/save, migration from legacy config
- `profiles.py`: profile normalization, defaults, unique naming, import/export shaping

- [ ] **Step 2: Preserve current config schema exactly**

Do not change:
- `toggle_hotkey`
- `target_key`
- `theme_name`
- `performance_mode`
- `overlay_enabled`
- `close_to_tray`
- `minimize_to_tray`
- `selected_macro_profile_id`
- `macro_profiles`

- [ ] **Step 3: Add tests for config and profile normalization**

Cover:
- missing config file
- legacy config migration
- invalid/missing macro profile fields
- import payload list vs object
- hotkey collision fallback
- default selected profile behavior

- [ ] **Step 4: Replace direct config logic in `app.py` with service calls**

`app.py` should stop owning JSON parsing details and only call backend persistence helpers.

- [ ] **Step 5: Commit**

```bash
git add backend/config_store.py backend/profiles.py tests/test_config_store.py tests/test_profiles.py app.py
git commit -m "refactor: extract config and profile persistence"
```

### Task 3: Centralize application state

**Files:**
- Create: `D:\Downloads\InputLab\backend\state.py`
- Modify: `D:\Downloads\InputLab\app.py`
- Test: `D:\Downloads\InputLab\tests\test_app_service.py`

- [ ] **Step 1: Introduce a backend-owned state container**

Move runtime state out of widget-adjacent fields where possible:
- holding/running flags
- active profile id
- macro loop counters
- progress labels
- updater status
- overlay enabled
- tray flags

State container should expose:
- `get_snapshot()`
- `patch(...)`
- `subscribe(callback)`
- `unsubscribe(callback)`

- [ ] **Step 2: Keep Tk variables as view mirrors only**

`StringVar` values should be updated from backend state snapshots or backend events. They should no longer be the primary source of truth for runtime state.

- [ ] **Step 3: Ensure snapshot shape matches future IPC contract**

The state snapshot returned here should be the same shape later returned by `get_state` over IPC.

- [ ] **Step 4: Commit**

```bash
git add backend/state.py tests/test_app_service.py app.py
git commit -m "refactor: centralize application state"
```

### Task 4: Extract keyboard hold runtime

**Files:**
- Create: `D:\Downloads\InputLab\backend\keyboard_hold_service.py`
- Modify: `D:\Downloads\InputLab\app.py`
- Test: `D:\Downloads\InputLab\tests\test_keyboard_hold_service.py`

- [ ] **Step 1: Move keyboard hold runtime out of UI class**

Extract from `app.py`:
- `register_key_hold_hotkey`
- `toggle_hold`
- `force_release`
- hold status mutation logic

- [ ] **Step 2: Keep service UI-agnostic**

Service API should look like:
- `configure_hotkey(hotkey: str, target_key: str)`
- `toggle()`
- `release()`
- `shutdown()`
- `get_state()`

- [ ] **Step 3: Emit state events instead of touching Tk**

The service should publish:
- hold started
- hold released
- hotkey registration failure

- [ ] **Step 4: Commit**

```bash
git add backend/keyboard_hold_service.py tests/test_keyboard_hold_service.py app.py
git commit -m "refactor: extract keyboard hold service"
```

### Task 5: Extract controller and macro runtime

**Files:**
- Create: `D:\Downloads\InputLab\backend\controller_service.py`
- Create: `D:\Downloads\InputLab\backend\macro_service.py`
- Modify: `D:\Downloads\InputLab\app.py`
- Test: `D:\Downloads\InputLab\tests\test_macro_service.py`

- [ ] **Step 1: Move controller ownership into `controller_service.py`**

This service should own:
- `vgamepad` initialization
- virtual controller lifetime
- button press/release operations
- driver-required errors

- [ ] **Step 2: Move macro loop execution into `macro_service.py`**

Extract from `app.py`:
- `start_macro`
- `stop_macro`
- runtime loop behavior
- per-step execution
- loop counters
- progress update payload creation
- recorder state if keeping recorder as backend logic

- [ ] **Step 3: Keep threading fully inside the backend**

The UI should not manage the macro worker thread directly. It should only:
- call start/stop/apply methods
- receive state updates

- [ ] **Step 4: Define service API**

Target methods:
- `apply_profile(profile: MacroProfile)`
- `start(profile_id: str, from_hotkey: bool = False)`
- `stop()`
- `toggle(profile_id: str)`
- `record_start()`
- `record_stop()`
- `get_runtime_state()`

- [ ] **Step 5: Preserve current behavior**

Do not change:
- loop interval semantics
- step hold/delay semantics
- progress text content
- run-condition checks
- recorder mappings

- [ ] **Step 6: Commit**

```bash
git add backend/controller_service.py backend/macro_service.py tests/test_macro_service.py app.py
git commit -m "refactor: extract controller and macro runtime"
```

### Task 6: Extract global hotkey management

**Files:**
- Create: `D:\Downloads\InputLab\backend\hotkeys.py`
- Modify: `D:\Downloads\InputLab\app.py`

- [ ] **Step 1: Move hotkey registration out of `app.py`**

Extract:
- macro hotkey registration
- key-hold hotkey registration
- recorder hook registration
- capture hook registration

- [ ] **Step 2: Make hotkey service callback-based**

The service should not know about Tk. It should emit callbacks or events like:
- `on_key_hold_toggle`
- `on_macro_toggle(profile_id)`
- `on_capture_event`
- `on_recorder_event`

- [ ] **Step 3: Ensure clean shutdown**

All `keyboard` hooks and hotkeys must be removable by one backend shutdown path.

- [ ] **Step 4: Commit**

```bash
git add backend/hotkeys.py app.py
git commit -m "refactor: extract hotkey registration service"
```

### Task 7: Extract updater, overlay, and tray orchestration

**Files:**
- Create: `D:\Downloads\InputLab\backend\updates.py`
- Create: `D:\Downloads\InputLab\backend\overlay_service.py`
- Create: `D:\Downloads\InputLab\backend\tray_service.py`
- Modify: `D:\Downloads\InputLab\app.py`

- [ ] **Step 1: Move updater network/install logic out of UI**

Extract:
- `run_update_check`
- manifest parsing
- download/install handoff
- updater state transitions

- [ ] **Step 2: Separate shell features from UI rendering**

Overlay and tray are not core macro logic, but they are also not page layout. Move the coordination logic into services so a future desktop host can replace them if needed.

- [ ] **Step 3: Keep current behavior**

Do not change:
- update source
- tray behavior
- overlay contents
- close/minimize semantics

- [ ] **Step 4: Commit**

```bash
git add backend/updates.py backend/overlay_service.py backend/tray_service.py app.py
git commit -m "refactor: extract updater tray and overlay services"
```

### Task 8: Add a backend application service façade

**Files:**
- Create: `D:\Downloads\InputLab\backend\app_service.py`
- Modify: `D:\Downloads\InputLab\app.py`
- Test: `D:\Downloads\InputLab\tests\test_app_service.py`

- [ ] **Step 1: Create one façade that composes all backend services**

`app_service.py` should own:
- config store
- profile manager
- state store
- keyboard hold service
- hotkey service
- controller service
- macro service
- updates service
- overlay/tray service

- [ ] **Step 2: Make `app.py` talk only to the façade**

The UI should call methods such as:
- `initialize()`
- `shutdown()`
- `get_snapshot()`
- `apply_keyboard_mapping(...)`
- `apply_macro_profile(...)`
- `start_macro(...)`
- `stop_macro()`
- `check_for_updates()`

- [ ] **Step 3: UI event subscription**

`app.py` should subscribe to backend events and update:
- `StringVar`s
- labels
- badges
- progress cards

It should stop directly mutating backend runtime state.

- [ ] **Step 4: Commit**

```bash
git add backend/app_service.py tests/test_app_service.py app.py
git commit -m "refactor: add backend application facade"
```

### Task 9: Add a UI adapter layer

**Files:**
- Create: `D:\Downloads\InputLab\ui\bindings.py`
- Create: `D:\Downloads\InputLab\ui\presenters.py`
- Create: `D:\Downloads\InputLab\ui\view_models.py`
- Modify: `D:\Downloads\InputLab\app.py`

- [ ] **Step 1: Introduce view model mapping**

Map backend snapshot/event payloads into UI-friendly data:
- status strings
- badge colors
- profile tab labels
- progress metrics
- update button states

- [ ] **Step 2: Stop reading backend state directly from widgets**

The UI should:
- collect user intent from widgets
- call backend façade
- render returned state/event payloads

- [ ] **Step 3: Keep this adapter Python-only**

This layer exists so the same backend behavior can later be exposed either to:
- the current Tk UI
- a future webview frontend

- [ ] **Step 4: Commit**

```bash
git add ui/bindings.py ui/presenters.py ui/view_models.py app.py
git commit -m "refactor: add UI adapter layer"
```

### Task 10: Lock the future IPC boundary

**Files:**
- Modify: `D:\Downloads\InputLab\backend\ipc_contract.py`
- Test: `D:\Downloads\InputLab\tests\test_ipc_contract.py`

- [ ] **Step 1: Define transport-neutral command set**

Choose JSON-safe command/event payloads only. No Tk objects, callbacks, `StringVar`s, or Python object references.

- [ ] **Step 2: Freeze payload naming**

Use stable names so a future Tauri or Electron frontend can consume the backend without changing backend semantics.

- [ ] **Step 3: Add contract tests**

Test:
- snapshot serialization
- event payload serialization
- request validation
- response validation

- [ ] **Step 4: Commit**

```bash
git add backend/ipc_contract.py tests/test_ipc_contract.py
git commit -m "refactor: finalize backend IPC contract"
```

---

## Migration Readiness Criteria

The refactor is complete when all of these are true:

1. `app.py` no longer contains runtime loop logic, hotkey registration logic, updater networking, or profile persistence internals.
2. `app.py` is mostly widget construction, event wiring, and rendering.
3. Backend services can run without importing `customtkinter`.
4. App state can be serialized into a JSON-safe snapshot.
5. User actions map to façade commands that could later become IPC messages.
6. Existing desktop behavior remains unchanged.

## Notes on Tauri/Electron Compatibility

This plan supports either future target because it assumes:
- Python remains the runtime authority
- UI becomes a client of `backend.app_service`
- IPC layer is defined before transport is implemented

At migration time:
- **Electron** can spawn the Python backend process and speak the contract over stdio, localhost HTTP, or WebSocket.
- **Tauri** can do the same through Rust-managed process launch and the same contract.

The transport should not be chosen during this refactor. Only the contract should be stabilized.

## Risks to watch during refactor

- accidental behavior changes from moving logic out of `app.py`
- introducing state duplication between Tk variables and backend state
- partial extraction that leaves services still depending on widgets
- recorder/capture hooks remaining coupled to UI callbacks
- updater/tray logic mixing shell concerns with view concerns

## Recommended execution order

1. config/profiles
2. centralized state
3. keyboard hold service
4. controller + macro runtime
5. hotkey service
6. updater/overlay/tray services
7. app façade
8. UI adapters
9. IPC contract hardening

## Current `app.py` areas this plan targets first

- `load_config`, `save_config`, `sync_config_from_ui`
- `register_key_hold_hotkey`, `register_macro_hotkeys`
- `start_macro`, `stop_macro`, recorder logic
- `run_update_check`
- tray and overlay helpers
- runtime progress/state mutation paths

