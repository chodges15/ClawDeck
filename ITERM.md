# iTerm2 Python API Reference Guide

Complete reference for the iTerm2 Python API, enabling automation and scripting of the iTerm2 terminal emulator.

Source: https://iterm2.com/python-api/

---

## Table of Contents

- [Getting Started](#getting-started)
- [Connection](#connection)
- [App](#app)
- [Window](#window)
- [Tab](#tab)
- [Session](#session)
- [Screen](#screen)
- [Selection](#selection)
- [Profile](#profile)
- [Color & Color Presets](#color--color-presets)
- [Alert](#alert)
- [Focus](#focus)
- [Keyboard](#keyboard)
- [Prompt](#prompt)
- [Lifecycle Monitors](#lifecycle-monitors)
- [Variables](#variables)
- [Broadcast](#broadcast)
- [Status Bar](#status-bar)
- [Registration & RPCs](#registration--rpcs)
- [Custom Control Sequences](#custom-control-sequences)
- [Main Menu](#main-menu)
- [Arrangement](#arrangement)
- [Transaction](#transaction)
- [Tmux](#tmux)
- [Tool (Toolbelt)](#tool-toolbelt)
- [Utilities](#utilities)
- [Preferences](#preferences)
- [Examples Index](#examples-index)

---

## Getting Started

### Script Types
- **Simple scripts** - Execute operations (e.g., create windows) then terminate
- **Long-running daemons** - Persist indefinitely, monitoring events or running periodic tasks

### Creating a Script
1. Go to **Scripts > New Python Script**
2. Choose environment: **basic** (built-in modules only) or **full environment**
3. Choose type: **simple script** or **long-running daemon**
4. Save and edit the template code

### Basic Script Pattern
```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    window = app.current_window
    # ... do things ...

iterm2.run_until_complete(main)
```

### Daemon Pattern
```python
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    # ... set up monitors, register RPCs, etc ...
    await iterm2.async_wait_forever()

iterm2.run_forever(main)
```

---

## Connection

Manages the websocket connection between scripts and iTerm2.

### Functions

#### `run_until_complete(coro, retry=False, debug=False)`
Runs an async function that accepts a `Connection` parameter. Returns when the coroutine finishes.

#### `run_forever(coro, retry=False, debug=False)`
Runs an async function with a `Connection` parameter. Never returns.

**Parameters for both:**
- `coro` - Async function accepting one `Connection` argument
- `retry` (bool) - Enable persistent reconnection attempts
- `debug` (bool) - Enable debug mode

### Class: Connection

Represents a loopback connection from script to iTerm2.

#### `Connection.async_create() -> Connection` (static)
Creates a new connection for use in the apython REPL. Does not initialize an asyncio event loop.

---

## App

Entry point to the iTerm2 application hierarchy.

### Functions

#### `async_get_app(connection, create_if_needed=True) -> App`
Returns the application singleton.

#### `async_invoke_function(connection, invocation, timeout=-1)`
Invokes an RPC in the global application context. Raises `RPCException` on failure.

### Class: App

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `async_activate` | `(raise_all_windows=True, ignoring_other_apps=False)` | Give app keyboard focus |
| `async_get_theme` | `() -> List[str]` | Returns theme attributes: `light`, `dark`, `automatic`, `minimal`, `highContrast` |
| `async_get_variable` | `(name) -> Any` | Get a variable from global context |
| `async_set_variable` | `(name, value)` | Set user-defined variable (name must start with `user.`) |
| `get_session_by_id` | `(session_id, include_buried=True) -> Session` | Find session by ID |
| `get_tab_by_id` | `(tab_id) -> Tab` | Find tab by ID |
| `get_window_by_id` | `(window_id) -> Window` | Find window by ID |
| `get_window_and_tab_for_session` | `(session) -> (Window, Tab)` | Get owning window and tab |
| `get_window_for_tab` | `(tab_id) -> Window` | Find window containing tab |
| `pretty_str` | `() -> str` | Human-readable window hierarchy |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `broadcast_domains` | `List[BroadcastDomain]` | Current broadcast domains |
| `buried_sessions` | `List[Session]` | All buried sessions |
| `current_window` | `Optional[Window]` | Currently focused window |

### Exceptions
- `CreateWindowException` - Raised on window creation failure

---

## Window

Represents a terminal window. Obtain via `App` or create with `Window.async_create()`.

### Static Methods

#### `Window.async_create(connection, profile=None, command=None, profile_customizations=None) -> Window`
Creates a new window. `command` and `profile_customizations` are mutually exclusive. Raises `CreateWindowException`.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `async_activate` | `()` | Bring window to front and focus |
| `async_close` | `(force=False)` | Close window |
| `async_create_tab` | `(profile=None, command=None, index=None, profile_customizations=None) -> Tab` | Create new tab |
| `async_create_tmux_tab` | `(tmux_connection) -> Tab` | Create tmux tab (not in Transaction) |
| `async_get_frame` | `() -> Frame` | Get window frame |
| `async_get_fullscreen` | `() -> bool` | Check fullscreen state |
| `async_invoke_function` | `(invocation, timeout=-1)` | Invoke RPC in window context |
| `async_restore_window_arrangement` | `(name)` | Restore arrangement |
| `async_save_window_as_arrangement` | `(name)` | Save as arrangement |
| `async_set_frame` | `(frame)` | Set window frame |
| `async_set_fullscreen` | `(fullscreen)` | Toggle fullscreen |
| `async_set_tabs` | `(tabs)` | Reorder/move tabs |
| `async_set_variable` | `(name, value)` | Set user variable |
| `pretty_str` | `(indent='') -> str` | Formatted description |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `current_tab` | `Optional[Tab]` | Current tab |
| `tabs` | `List[Tab]` | All tabs |
| `window_id` | `str` | Unique identifier |

### Exceptions
- `CreateTabException`, `SetPropertyException`, `GetPropertyException`, `SavedArrangementException`

---

## Tab

Represents a tab within a window. Obtain via `App` or `Window`.

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `async_activate` | `(order_window_front=True)` | Select this tab |
| `async_close` | `(force=False)` | Close tab |
| `async_get_variable` | `(name) -> Any` | Get tab variable |
| `async_invoke_function` | `(invocation, timeout=-1)` | Invoke RPC in tab context |
| `async_move_to_window` | `() -> Window` | Move tab to new window |
| `async_select_pane_in_direction` | `(direction: NavigationDirection) -> str` | Activate adjacent pane (3.3.2+) |
| `async_set_title` | `(title)` | Set tab title (interpolated string) |
| `async_set_variable` | `(name, value)` | Set user variable |
| `async_update_layout` | `()` | Adjust layout after changing `Session.preferred_size` |
| `pretty_str` | `(indent='') -> str` | Formatted description |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `current_session` | `Optional[Session]` | Active session |
| `root` | `Splitter` | Root of session tree |
| `sessions` | `List[Session]` | Visible split panes |
| `tab_id` | `str` | Unique identifier |
| `tmux_window_id` | `Optional[str]` | Tmux window ID (None if not tmux) |
| `window` | `Optional[Window]` | Parent window |

---

## Session

Represents a terminal session (a single pane).

### Static Methods

- `Session.active_proxy(connection)` - Register notifications for active session
- `Session.all_proxy(connection)` - Register notifications for all sessions (including future)

### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `async_activate` | `(select_tab=True, order_window_front=True)` | Activate session |
| `async_add_annotation` | `(range: CoordRange, text: str)` | Add annotation |
| `async_close` | `(force=False)` | Close session |
| `async_get_contents` | `(first_line, number_of_lines) -> List[LineContents]` | Get screen contents (use in Transaction) |
| `async_get_coprocess` | `() -> Optional[str]` | Get running coprocess command |
| `async_get_line_info` | `() -> SessionLineInfo` | Get line geometry info |
| `async_get_profile` | `() -> Profile` | Get session profile |
| `async_get_screen_contents` | `() -> ScreenContents` | Get mutable screen area |
| `async_get_selection` | `() -> Selection` | Get selected regions |
| `async_get_selection_text` | `(selection) -> str` | Get text of selection |
| `async_get_variable` | `(name) -> Any` | Get session variable |
| `async_inject` | `(data: bytes)` | Inject data as program output |
| `async_invoke_function` | `(invocation, timeout=-1)` | Invoke RPC in session context |
| `async_restart` | `(only_if_exited=False)` | Restart session |
| `async_run_coprocess` | `(command_line) -> bool` | Launch coprocess |
| `async_run_tmux_command` | `(command, timeout=-1) -> str` | Run tmux command |
| `async_send_text` | `(text, suppress_broadcast=False)` | Send text as typed input |
| `async_set_buried` | `(buried: bool)` | Bury/disinter session |
| `async_set_grid_size` | `(size: Size)` | Set visible size in cells |
| `async_set_name` | `(name)` | Set session name |
| `async_set_profile` | `(profile)` | Change session profile |
| `async_set_profile_properties` | `(write_only_profile)` | Modify profile for session only |
| `async_set_selection` | `(selection)` | Set selection regions |
| `async_set_variable` | `(name, value)` | Set user variable (name starts with `user.`) |
| `async_split_pane` | `(vertical=False, before=False, profile=None, profile_customizations=None) -> Session` | Split pane |
| `async_stop_coprocess` | `() -> bool` | Stop coprocess |
| `get_screen_streamer` | `(want_contents=True) -> ScreenStreamer` | Get screen update stream |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `grid_size` | `Size` | Visible size in cells |
| `preferred_size` | `Size` | Size for layout updates |
| `session_id` | `str` | Unique identifier |
| `tab` | `Optional[Tab]` | Containing tab |
| `window` | `Optional[Window]` | Containing window |

### ScreenStreamer Usage
```python
async with session.get_screen_streamer() as streamer:
    while condition():
        contents = await streamer.async_get()
        do_something(contents)
```

### Related Classes

#### `SessionLineInfo`
Properties: `first_visible_line_number`, `mutable_area_height`, `overflow`, `scrollback_buffer_height`

#### `Splitter`
Container for split panes. Properties: `children` (list of Session/Splitter), `sessions`, `vertical` (bool).

### Exceptions
- `InvalidSessionId`, `SplitPaneException`

---

## Screen

### Class: ScreenStreamer
Async context manager for monitoring screen changes. Access via `Session.get_screen_streamer()`.

#### `async_get(style=False) -> ScreenContents`
Blocks until screen changes. Set `style=True` to include style info.

### Class: ScreenContents

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `cursor_coord` | `Point` | Cursor location |
| `number_of_lines` | `int` | Total lines |
| `number_of_lines_above_screen` | `int` | Lines in scrollback |
| `line(index)` | `LineContents` | Get line at index |

### Class: LineContents

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `hard_eol` | `bool` | True if hard newline |
| `string` | `str` | Line text |
| `string_at(x)` | `str` | Character at cell x |

---

## Selection

### SelectionMode (Enum)
- `CHARACTER = 0`, `WORD = 1`, `LINE = 2`, `SMART = 3`, `BOX = 4`, `WHOLE_LINE = 5`

### Class: SubSelection
```python
SubSelection(windowed_coord_range: WindowedCoordRange, mode: SelectionMode, connected: bool)
```
- `async_get_string(connection, session_id) -> str` - Get text of sub-selection
- Properties: `mode`, `windowed_coord_range`

### Class: Selection
```python
Selection(sub_selections: List[SubSelection])
```
- `async_get_string(connection, session_id, width) -> str` - Get selected text
- Property: `sub_selections`

---

## Profile

Represents an iTerm2 terminal profile.

### Static Methods

- `Profile.async_get(connection, guids=None) -> List[Profile]` - Get profiles by GUID (or all)
- `Profile.async_get_default(connection) -> Profile` - Get default profile

### Instance Methods

- `async_make_default()` - Make this profile the default

### Property Categories

**Colors:** `foreground_color`, `background_color`, `bold_color`, `cursor_color`, `cursor_text_color`, `link_color`, `selected_text_color`, `selection_color`, `tab_color`, `badge_color`, `cursor_guide_color`, `underline_color`, `ansi_0_color` through `ansi_15_color`

**Fonts:** `normal_font`, `non_ascii_font`, `ascii_ligatures`, `non_ascii_ligatures`, `use_bold_font`, `use_italic_font`, `use_built_in_powerline_glyphs`

**Cursor:** `cursor_type` (CursorType enum), `blinking_cursor`, `smart_cursor_color`, `cursor_boost`, `use_cursor_guide`

**Window:** `name`, `guid`, `command`, `use_custom_command`, `initial_directory_mode`, `custom_directory`, `transparency`, `blend`, `blur`, `blur_radius`, `background_image_location`, `background_image_mode`

**Badge:** `badge_text`, `badge_font`, `badge_max_width`, `badge_max_height`, `badge_top_margin`, `badge_right_margin`

**Scrollback:** `scrollback_lines`, `unlimited_scrollback`, `scrollback_in_alternate_screen`

**Title:** `title_components`, `title_function`, `use_custom_window_title`, `custom_window_title`

**Terminal:** `character_encoding`, `mouse_reporting`, `option_key_sends`, `unicode_normalization`, `unicode_version`, `use_csi_u`

**Advanced:** `triggers`, `smart_selection_rules`, `key_mappings`, `semantic_history`, `automatic_profile_switching_rules`

### Async Setters

All properties have corresponding `async_set_<property_name>(value)` methods:
```python
await profile.async_set_foreground_color(iterm2.Color(255, 255, 255))
await profile.async_set_normal_font("Monaco 12")
await profile.async_set_cursor_type(iterm2.CursorType.VERTICAL_BAR)
```

### Class: LocalWriteOnlyProfile

Modify session properties without changing the underlying profile. All setters are synchronous (no `async_`):

```python
change = iterm2.LocalWriteOnlyProfile()
change.set_foreground_color(iterm2.Color(255, 0, 0))
change.set_tab_color(iterm2.Color(0, 255, 0))
await session.async_set_profile_properties(change)
```

### Profile Enums

- `CursorType` - `CURSOR_TYPE_UNDERLINE`, `CURSOR_TYPE_VERTICAL`, `CURSOR_TYPE_BOX`
- `ThinStrokes` - Thin stroke rendering options
- `InitialWorkingDirectory` - `INITIAL_WORKING_DIRECTORY_CUSTOM`, `INITIAL_WORKING_DIRECTORY_HOME`, etc.
- `IconMode` - Icon display modes
- `TitleComponents` - Components to include in title
- `OptionKeySends` - Option key behavior modes
- `BackgroundImageMode` - Background image display modes
- `CharacterEncoding` - Character encoding options
- `UnicodeNormalization` - Unicode normalization forms

---

## Color & Color Presets

### Class: Color
```python
Color(r=0, g=0, b=0, a=255, color_space=ColorSpace.SRGB)
```
Properties: `red`, `green`, `blue`, `alpha`, `color_space`

### ColorSpace (Enum)
- `SRGB = 'sRGB'`
- `CALIBRATED = 'Calibrated'`

### Class: ColorPreset
A named collection of terminal colors.

- `ColorPreset.async_get(connection, name) -> ColorPreset` - Get preset by name
- `ColorPreset.async_get_list(connection) -> List[str]` - List all preset names
- Property: `values: List[ColorPreset.Color]` - Colors in the preset

### Class: ColorPreset.Color
Inherits from `Color`. Additional property: `key` (str) - identifies which terminal attribute this color affects.

### Exceptions
- `ListPresetsException`, `GetPresetException`

---

## Alert

### Class: Alert
```python
Alert(title: str, subtitle: str, window_id: Optional[str] = None)
```
- `add_button(title)` - Add button
- `async_run(connection) -> int` - Show alert, returns button index + 1000

### Class: TextInputAlert
```python
TextInputAlert(title, subtitle, placeholder, default_value, window_id=None)
```
- `async_run(connection) -> Optional[str]` - Show alert, returns entered text or None if cancelled

### Class: PolyModalAlert
```python
PolyModalAlert(title, subtitle, window_id=None)
```
Rich alert with multiple UI elements:
- `add_button(title)` - Add button
- `add_checkbox_item(item_text, item_default=0)` - Add checkbox
- `add_checkboxes(items, defaults)` - Add multiple checkboxes
- `add_combobox(items, default=None)` - Add combobox
- `add_combobox_item(item_text, is_default=False)` - Add combobox item
- `add_text_field(placeholder, default)` - Add text field
- `async_run(connection) -> PolyModalResult` - Show alert

---

## Focus

### Class: FocusMonitor
```python
async with iterm2.FocusMonitor(connection) as monitor:
    while True:
        update = await monitor.async_get_next_update()
        if update.selected_tab_changed:
            print(f"Active tab: {update.selected_tab_changed.tab_id}")
```

### Class: FocusUpdate
At most one property is non-None per update:
- `application_active: FocusUpdateApplicationActive` - App activated/deactivated
- `window_changed: FocusUpdateWindowChanged` - Window focus changed
- `selected_tab_changed: FocusUpdateSelectedTabChanged` - Tab selection changed
- `active_session_changed: FocusUpdateActiveSessionChanged` - Active session changed

### FocusUpdateWindowChanged.Reason (Enum)
- `TERMINAL_WINDOW_BECAME_KEY = 0`
- `TERMINAL_WINDOW_IS_CURRENT = 1`
- `TERMINAL_WINDOW_RESIGNED_KEY = 2`

---

## Keyboard

### Class: KeystrokeMonitor
```python
KeystrokeMonitor(connection, session=None, advanced=False)
```
- `async_get() -> Keystroke` - Wait for next keystroke

```python
async with iterm2.KeystrokeMonitor(connection) as mon:
    while True:
        keystroke = await mon.async_get()
        print(keystroke.characters, keystroke.modifiers)
```

### Class: KeystrokeFilter
```python
KeystrokeFilter(connection, patterns: List[KeystrokePattern], session=None)
```
Context manager that disables normal handling for matched keystrokes.

### Class: Keystroke
Properties: `characters`, `characters_ignoring_modifiers`, `keycode` (Keycode enum), `modifiers` (List[Modifier])

### Class: KeystrokePattern
Properties (all lists for matching): `characters`, `characters_ignoring_modifiers`, `keycodes`, `required_modifiers`, `forbidden_modifiers`

### Modifier (Enum)
`CONTROL = 1`, `OPTION = 2`, `COMMAND = 3`, `SHIFT = 4`, `FUNCTION = 5`, `NUMPAD = 6`

### Keycode (Enum)
Full ANSI keycode enumeration: `ANSI_A` through `ANSI_Z`, `ANSI_0` through `ANSI_9`, `F1` through `F20`, `ESCAPE`, `TAB`, `SPACE`, `RETURN`, `DELETE`, arrow keys, keypad keys, etc.

---

## Prompt

Requires Shell Integration. Monitors shell prompt state changes.

### PromptState (Enum)
- `EDITING = 0` - User editing command
- `RUNNING = 1` - Command executing
- `FINISHED = 3` - Command finished, no new prompt yet
- `UNKNOWN = -1` - Not reported

### Class: Prompt
Properties: `command`, `command_range` (CoordRange), `output_range` (CoordRange), `prompt_range` (CoordRange), `working_directory`

### Class: PromptMonitor
```python
PromptMonitor(connection, session_id, modes=None)
```

#### PromptMonitor.Mode (Enum)
- `PROMPT = 1` - New prompt detected
- `COMMAND_START = 2` - Command begins
- `COMMAND_END = 3` - Command finishes

```python
async with iterm2.PromptMonitor(connection, session.session_id) as mon:
    while True:
        await mon.async_get()
        print("New prompt!")
```

### Functions
- `async_get_last_prompt(connection, session_id) -> Prompt` - Get most recent prompt
- `async_get_prompt_by_id(connection, session_id, prompt_unique_id) -> Prompt` - Get prompt by ID

---

## Lifecycle Monitors

### SessionTerminationMonitor
```python
async with iterm2.SessionTerminationMonitor(connection) as mon:
    while True:
        session_id = await mon.async_get()
        print(f"Session {session_id} closed")
```

### LayoutChangeMonitor
Detects session/tab/window arrangement changes (movement, reordering, resizing, burial).
```python
async with iterm2.LayoutChangeMonitor(connection) as mon:
    while True:
        await mon.async_get()
        print("Layout changed")
```

### NewSessionMonitor
```python
async with iterm2.NewSessionMonitor(connection) as mon:
    while True:
        session_id = await mon.async_get()
        print(f"New session: {session_id}")
```

### EachSessionOnceMonitor
Runs a task once per session (existing and future), auto-cancels on termination.
```python
async def my_task(session_id):
    # do something with each session
    pass

await iterm2.EachSessionOnceMonitor.async_foreach_session_create_task(app, my_task)
```

---

## Variables

### Class: VariableMonitor
```python
VariableMonitor(connection, scope: VariableScopes, name: str, identifier: Optional[str])
```
- `scope` - Where to evaluate: `VariableScopes.SESSION`, `TAB`, `WINDOW`, `APP`
- `identifier` - ID for the scope, `None` for APP, `"all"` or `"active"` for SESSION/WINDOW

```python
async with iterm2.VariableMonitor(
        connection, iterm2.VariableScopes.SESSION,
        "jobName", session.session_id) as mon:
    while True:
        new_value = await mon.async_get()
        print(f"Job changed to: {new_value}")
```

### VariableScopes (Enum)
`SESSION = 1`, `TAB = 2`, `WINDOW = 3`, `APP = 4`

---

## Broadcast

Broadcast keyboard input across multiple sessions.

### Class: BroadcastDomain
- `add_session(session)` - Add session to domain
- Property: `sessions: List[Session]` - Sessions in domain

### Function
```python
await iterm2.async_set_broadcast_domains(connection, [domain1, domain2])
```
Sets all broadcast domains. Domains are mutually exclusive (disjoint).

---

## Status Bar

### Class: StatusBarComponent
```python
StatusBarComponent(
    short_description, detailed_description, knobs,
    exemplar, update_cadence, identifier,
    icons=[], format=Format.PLAIN_TEXT
)
```
- `identifier` - Reverse DNS format (e.g., `com.example.calculator`)
- `update_cadence` - Seconds between updates, or None
- `knobs` - List of configuration knobs

#### Methods
- `async_open_popover(session_id, html, size: Size)` - Show HTML popover
- `async_register(connection, coro, timeout=None, onclick=None)` - Register component

### Knob Types
- `CheckboxKnob(name, default_value: bool, key)`
- `StringKnob(name, placeholder, default_value, key)`
- `PositiveFloatingPointKnob(name, default_value: float, key)`
- `ColorKnob(name, default_value: Color, key)`

### Icon
```python
StatusBarComponent.Icon(scale: float, base64_data: str)
```
Icons should be 16x17 points. Use `scale=2` for retina.

### Example
```python
component = iterm2.StatusBarComponent(
    short_description="Session ID",
    detailed_description="Show session identifier",
    knobs=[], exemplar="[session ID]",
    update_cadence=None,
    identifier="com.example.session-id")

@iterm2.StatusBarRPC
async def coro(knobs, session_id=iterm2.Reference("id")):
    return session_id

await component.async_register(connection, coro)
```

---

## Registration & RPCs

### Class: Reference
```python
Reference(name)
```
References a variable for use in RPC decorators. Use `iterm2.Reference("id")` to get session ID.

### Decorators

#### `@iterm2.RPC`
Register a function callable from iTerm2.
```python
@iterm2.RPC
async def my_func(session_id=iterm2.Reference("id"), n=1):
    session = app.get_session_by_id(session_id)
    for i in range(n):
        await session.async_split_pane()

await my_func.async_register(connection)
```

#### `@iterm2.TitleProviderRPC`
Register a dynamic session title provider.
```python
@iterm2.TitleProviderRPC
async def upper_title(auto_name=iterm2.Reference("autoName?")):
    return auto_name.upper() if auto_name else ""

await upper_title.async_register(
    connection,
    display_name="Upper-case Title",
    unique_identifier="com.example.title-provider")
```

#### `@iterm2.StatusBarRPC`
Register a status bar component. Must accept `knobs` parameter.
```python
@iterm2.StatusBarRPC
async def my_status(knobs, session_id=iterm2.Reference("id")):
    return session_id
```
Register via `StatusBarComponent.async_register(connection, coro, onclick=handler)`.

#### `@iterm2.ContextMenuProviderRPC`
Register a context menu item.
```python
await my_func.async_register(
    connection,
    display_name="My Action",
    unique_identifier="com.example.my-action")
```

---

## Custom Control Sequences

### Class: CustomControlSequenceMonitor
```python
CustomControlSequenceMonitor(connection, identity: str, regex: str, session_id=None)
```
- `identity` - Shared secret string
- `regex` - Pattern to match against payload
- `session_id` - None to monitor all sessions

```python
async with iterm2.CustomControlSequenceMonitor(
        connection, "shared-secret", r'^create-window$') as mon:
    while True:
        match = await mon.async_get()
        await iterm2.Window.async_create(connection)
```

---

## Main Menu

### Class: MainMenu (static methods)

- `async_get_menu_item_state(connection, identifier) -> MenuItemState` - Query menu item state
- `async_select_menu_item(connection, identifier)` - Select/click menu item

### Class: MenuItemState
- `checked: bool` - Has checkmark
- `enabled: bool` - Can be selected

### Exceptions
- `MenuItemException`

---

## Arrangement

Saved window arrangements.

### Class: Arrangement (static methods)

- `async_list(connection) -> List[str]` - List saved arrangements (requires 3.4.0+)
- `async_restore(connection, name, window_id=None)` - Restore arrangement. Pass `window_id` to restore as tabs in existing window.
- `async_save(connection, name)` - Save all windows as arrangement (overwrites existing)

### Exceptions
- `SavedArrangementException`

---

## Transaction

Ensures atomic API call sequences.

```python
async with iterm2.Transaction(connection):
    contents = await session.async_get_contents(0, 10)
    await session.async_send_text("hello")
```

**Note:** Some APIs cannot be used within transactions (those that lack synchronous completion).

---

## Tmux

### Functions

- `async_get_tmux_connections(connection) -> List[TmuxConnection]` - Get all tmux connections (not in Transaction)
- `async_get_tmux_connection_by_connection_id(connection, connection_id) -> TmuxConnection`

### Class: TmuxConnection

| Method/Property | Description |
|-----------------|-------------|
| `async_create_window() -> Window` | Create tmux window (not in Transaction) |
| `async_send_command(command) -> str` | Send command to tmux server |
| `async_set_tmux_window_visible(tmux_window_id, visible)` | Show/hide tmux window (not in Transaction) |
| `connection_id: str` | Unique connection ID |
| `owning_session: Optional[Session]` | Gateway session where `tmux -CC` was run |

### Exceptions
- `TmuxException`

---

## Tool (Toolbelt)

### `async_register_web_view_tool(connection, display_name, identifier, reveal_if_already_registered, url)`
Register a toolbelt tool showing a webview.
- `identifier` - Unique ID (only one per identifier)
- `reveal_if_already_registered` - Show tool on duplicate registration
- `url` - URL to display

---

## Utilities

### Class: Size
```python
Size(width: int, height: int)
```
Properties: `width`, `height`, `json`

### Class: Point
```python
Point(x: int, y: int)
```
Properties: `x`, `y`, `json`

### Class: Frame
```python
Frame(origin: Point, size: Size)
```
Properties: `origin`, `size`, `json`. Origin (0,0) is bottom-left of main screen.

### Class: CoordRange
```python
CoordRange(start: Point, end: Point)
```
`end` is the first point NOT in the range.

### Class: Range
```python
Range(location: int, length: int)
```

### Class: WindowedCoordRange
```python
WindowedCoordRange(coordRange: CoordRange, columnRange: Optional[Range] = None)
```
Coordinate range optionally constrained to columns.

### Functions
- `frame_str(frame) -> str` - Human-readable frame
- `size_str(size) -> str` - Human-readable size

---

## Preferences

### `async_get_preference(connection, key: PreferenceKey) -> Any`
Get a preference value. Returns None if unset.

### `async_set_preference(connection, key, value)`
Set a preference. Pass None to unset.

### PreferenceKey (Enum)
100+ keys including: `ACTIONS`, `AUTO_COMMAND_HISTORY`, `COPY_TO_PASTEBOARD_ON_SELECTION`, `DIM_BACKGROUND_WINDOWS`, `ENABLE_SEMANTIC_HISTORY`, `FOCUS_FOLLOWS_MOUSE`, `USE_METAL`, `THEME`, `WORD_CHARACTERS`, and many more.

---

## Examples Index

### Status Bar Components
- Status Bar Component, Escape Key Indicator, JSON Pretty Printer, Mouse Mode, GMT Clock, Free Disk Space, Unread Count, Web-Based Status Bar, Python Virtual Environment

### Monitoring Events
- Random Color Preset, Per-Host Colors, Change Color Presets On Theme Change, Preserve Tab Color, Tab Title, Alert on Long-Running Jobs, Set Tab Color from Current App, Sync Pane Title to Tab

### Profiles and Color Presets
- Get Selected Color Preset, Modify Background Image Blending, Set Tab Color, Increase Font Size, Resize Font in All Sessions, Change Default Profile

### Windows and Tabs
- Move Tab To Next/Previous Window, Sort Tabs, Persistent MRU Tabs, Select MRU On Close, Find Pane with Process

### Broadcasting Input
- Enable Broadcasting Input, Asymmetric Broadcast Input

### Standalone Scripts
- Launch iTerm2 and Set Session Title, Launch iTerm2 and Run Command, Run a Command and Return Output

### Tmux
- Tmux Integration, Tile tmux Window Panes

### Session Title Providers
- George's Title Algorithm, Badge or Window Name in Tab Title

### Other
- Close Tabs to the Right, Change Color Preset by Time of Day, Targeted Input, Sum Selection, Zoom on Screen, Clear All Sessions, Custom Escape Sequences, One-Shot Alert
