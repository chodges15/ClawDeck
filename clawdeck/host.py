"""Host integration helpers for iTerm, Accessibility, and TTY writes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .app_logging import logger
from .constants import ITERM_APP_NAME, SESSIONS
from .layout import session_label_key


KSDIFF_PATH = "/Applications/Kaleidoscope.app/Contents/MacOS/ksdiff"


def normalize_tty_name(tty_name):
    """Normalize `/dev/...` TTY names to the bare device identifier."""
    if tty_name is None:
        return None
    tty_name = str(tty_name).strip()
    if not tty_name:
        return None
    if tty_name.startswith("/dev/"):
        tty_name = tty_name[5:]
    return tty_name or None


def session_pattern(config, session):
    """Return the configured match pattern for a logical session row."""
    session_map = config.get("session_map", {})
    pattern = str(session_map.get(session, "")).strip()
    if pattern:
        return pattern

    # Fresh installs start with an empty session_map. In that case,
    # fall back to literal T1/T2/T3 matching so a plainly named iTerm
    # session works without extra setup. Once any custom mapping exists,
    # blank entries remain intentionally unmapped.
    if any(str(session_map.get(name, "")).strip() for name in SESSIONS):
        return ""
    return session


def match_session_name(config, session_name):
    """Map a raw iTerm session name back to a logical ClawDeck session."""
    if not session_name:
        return None
    lowered = session_name.lower()
    for session in SESSIONS:
        pattern = session_pattern(config, session)
        if pattern and pattern.lower() in lowered:
            return session
    return None


def session_matches_pattern(pattern, info):
    """Return whether a row pattern matches an iTerm tab title or session name."""
    if not pattern:
        return False
    for key in ("tab_title", "name"):
        value = info.get(key)
        if value and pattern.lower() in value.lower():
            return True
    return False


def match_session_info(config, info):
    """Map iTerm session metadata back to a logical ClawDeck session."""
    if not info:
        return None
    for session in SESSIONS:
        pattern = session_pattern(config, session)
        if session_matches_pattern(pattern, info):
            return session
    return None


class HostIntegration:
    """Perform macOS and iTerm boundary operations for the controller."""

    def check_accessibility(self):
        """Check if Accessibility permissions are granted for this terminal app."""
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to get name of first process',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True

        print()
        print("━━━ Accessibility Permission Required ━━━")
        print("  Your terminal app needs Accessibility access for")
        print("  session activation and keystroke sending.")
        print()
        print("  Opening System Settings now...")
        print("  → Toggle ON your terminal app, then press Enter here.")
        print()

        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ],
            capture_output=True,
        )

        while True:
            try:
                input("  Press Enter after granting permission...")
            except (KeyboardInterrupt, EOFError):
                sys.exit(1)

            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of first process',
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print("  Accessibility permission granted!")
                return True
            print("  Not yet — make sure your terminal app is toggled ON, then try again.")

    def get_iterm_sessions(self):
        """Return iTerm2 sessions with session, tab, and window metadata."""
        script = r'''
tell application "iTerm2"
    if not running then return ""
    set fieldSep to ASCII character 31
    set output to ""
    repeat with w in windows
        repeat with t in tabs of w
            repeat with s in sessions of t
                set sessionName to ""
                set sessionTTY to ""
                set tabTitle to ""
                set tabIndex to ""
                set sessionID to ""
                set profileName to ""
                set isProcessing to ""
                set isAtPrompt to ""
                set sessionColumns to ""
                set sessionRows to ""
                set windowID to ""
                set windowIndex to ""
                set windowName to ""
                set windowFrontmost to ""

                try
                    set sessionName to name of s
                end try
                try
                    set sessionTTY to tty of s
                end try
                try
                    set tabTitle to title of t
                end try
                try
                    set tabIndex to index of t as text
                end try
                try
                    set sessionID to id of s
                end try
                try
                    set profileName to profile name of s
                end try
                try
                    set isProcessing to is processing of s as text
                end try
                try
                    set isAtPrompt to is at shell prompt of s as text
                end try
                try
                    set sessionColumns to columns of s as text
                end try
                try
                    set sessionRows to rows of s as text
                end try
                try
                    set windowID to id of w as text
                end try
                try
                    set windowIndex to index of w as text
                end try
                try
                    set windowName to name of w
                end try
                try
                    set windowFrontmost to frontmost of w as text
                end try

                if sessionName is not "" and sessionTTY is not "" then
                    set fields to {sessionName, sessionTTY, tabTitle, (tabIndex as text), sessionID, profileName, (isProcessing as text), (isAtPrompt as text), (sessionColumns as text), (sessionRows as text), (windowID as text), (windowIndex as text), windowName, (windowFrontmost as text)}
                    set AppleScript's text item delimiters to fieldSep
                    set output to output & (fields as text) & linefeed
                    set AppleScript's text item delimiters to ""
                end if
            end repeat
        end repeat
    end repeat
    return output
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return []
        except Exception:
            logger.warning("Failed to read iTerm2 sessions", exc_info=True)
            return []

        sessions = []
        for line in result.stdout.splitlines():
            parts = line.split("\x1f")
            if len(parts) < 14:
                continue
            (
                name,
                tty,
                tab_title,
                tab_index,
                session_id,
                profile_name,
                is_processing,
                is_at_shell_prompt,
                columns,
                rows,
                window_id,
                window_index,
                window_name,
                window_frontmost,
            ) = parts[:14]
            tty = normalize_tty_name(tty)
            if name.strip() and tty:
                sessions.append(
                    {
                        "name": name.strip(),
                        "tty": tty,
                        "tab_title": tab_title.strip() or None,
                        "tab_index": int(tab_index) if tab_index.strip() else None,
                        "session_id": session_id.strip() or None,
                        "profile_name": profile_name.strip() or None,
                        "is_processing": is_processing.strip().lower() == "true",
                        "is_at_shell_prompt": is_at_shell_prompt.strip().lower() == "true",
                        "columns": int(columns) if columns.strip() else None,
                        "rows": int(rows) if rows.strip() else None,
                        "window_id": int(window_id) if window_id.strip() else None,
                        "window_index": int(window_index) if window_index.strip() else None,
                        "window_name": window_name.strip() or None,
                        "window_frontmost": window_frontmost.strip().lower() == "true",
                    }
                )
        return sessions

    def resolve_tty_cwd(self, tty_name):
        """Get the working directory of the most recent shell on a TTY."""
        try:
            result = subprocess.run(
                ["ps", "-t", tty_name, "-o", "pid=,comm="],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            shell_pid = None
            for line in result.stdout.strip().split("\n"):
                parts = line.strip().split(None, 1)
                if len(parts) == 2:
                    comm = parts[1].strip().lstrip("-")
                    if comm in ("zsh", "bash", "fish"):
                        shell_pid = parts[0].strip()
            if not shell_pid:
                return None

            result = subprocess.run(
                ["lsof", "-a", "-p", shell_pid, "-d", "cwd", "-Fn"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None

            for line in result.stdout.strip().split("\n"):
                if line.startswith("n"):
                    return line[1:]
            return None
        except Exception:
            logger.debug("Failed to resolve CWD for %s", tty_name, exc_info=True)
            return None

    def resolve_git_branch(self, path):
        """Return the current git branch name for a working directory, if any."""
        if not path:
            return None
        try:
            result = subprocess.run(
                ["git", "-C", path, "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            branch = result.stdout.strip()
            return branch or None
        except Exception:
            logger.debug("Failed to resolve git branch for %s", path, exc_info=True)
            return None

    def build_tty_map(self, config):
        """Resolve configured sessions into deck-slot TTY and CWD maps."""
        tty_map = {}
        cwd_map = {}
        sessions = self.get_iterm_sessions()

        for session in SESSIONS:
            pattern = session_pattern(config, session)
            if not pattern:
                continue
            for info in sessions:
                if pattern.lower() in info["name"].lower():
                    label_key = session_label_key(session)
                    tty_map[label_key] = info["tty"]
                    cwd = self.resolve_tty_cwd(info["tty"])
                    if cwd:
                        cwd_map[label_key] = cwd
                    break

        logger.debug("TTY map: %s", tty_map)
        logger.debug(
            "CWD map: %s",
            {slot: Path(cwd).name for slot, cwd in cwd_map.items()},
        )
        return tty_map, cwd_map

    def frontmost_session_name(self):
        """Return the name of the currently focused iTerm session."""
        script = r'''
tell application "iTerm2"
    if not running then return ""
    try
        return name of current session of current tab of current window
    on error
        return ""
    end try
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            name = result.stdout.strip()
            return name or None
        except Exception:
            logger.debug("Failed to detect frontmost iTerm2 session", exc_info=True)
            return None

    def frontmost_session_info(self):
        """Return tab/session metadata for the currently focused iTerm session."""
        script = r'''
tell application "iTerm2"
    if not running then return ""
    set fieldSep to ASCII character 31
    try
        set tabTitle to ""
        set sessionName to ""
        try
            set tabTitle to title of current tab of current window
        end try
        try
            set sessionName to name of current session of current tab of current window
        end try
        set AppleScript's text item delimiters to fieldSep
        return ({tabTitle, sessionName} as text)
    on error
        return ""
    end try
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return None
            parts = result.stdout.strip().split("\x1f", 1)
            tab_title = parts[0].strip() if parts else ""
            session_name = parts[1].strip() if len(parts) > 1 else ""
            if not tab_title and not session_name:
                return None
            return {
                "tab_title": tab_title or None,
                "name": session_name or None,
            }
        except Exception:
            logger.debug("Failed to detect frontmost iTerm2 session info", exc_info=True)
            return None

    def get_frontmost_slot(self, config):
        """Resolve the frontmost iTerm session into a deck label key."""
        session = match_session_info(config, self.frontmost_session_info())
        return session_label_key(session) if session else None

    def activate_session(self, config, session):
        """Focus the configured iTerm session for the given logical row."""
        pattern = session_pattern(config, session)
        if not pattern:
            return False

        pattern_json = json.dumps(pattern)
        script = f'''
set matchPattern to {pattern_json}
tell application "{ITERM_APP_NAME}"
    if not running then return "not-running"
    repeat with w in windows
        repeat with t in tabs of w
            set tabTitle to ""
            set sessionName to missing value
            try
                set tabTitle to title of t
            end try
            try
                set sessionName to name of current session of t
            end try
            if sessionName is missing value then
                set sessionName to ""
            end if
            ignoring case
                if tabTitle contains matchPattern or sessionName contains matchPattern then
                    try
                        tell t to select
                        tell w
                            if is hotkey window then
                                reveal hotkey window
                            else
                                select
                            end if
                        end tell
                        activate
                        return "ok"
                    on error errMsg number errNum
                        return "error " & errNum & ": " & errMsg
                    end try
                end if
            end ignoring
        end repeat
    end repeat
    return "no-match"
end tell
'''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception:
            logger.warning("Failed to activate session %s", session, exc_info=True)
            return False

        status = result.stdout.strip()
        ok = result.returncode == 0 and status == "ok"
        if not ok:
            logger.warning(
                "Failed to activate session %s: status=%r stderr=%r",
                session,
                status or None,
                result.stderr.strip() or None,
            )
        return ok

    def approve_permission(self, tty_name):
        """Write `y` to the TTY backing a permission prompt."""
        tty_path = f"/dev/{tty_name}"
        fd = None
        try:
            fd = os.open(tty_path, os.O_WRONLY | os.O_NOCTTY)
            os.write(fd, b"y\n")
            return True
        except OSError:
            logger.warning("Failed to approve permission via %s", tty_path, exc_info=True)
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    logger.debug("Failed to close TTY %s", tty_path, exc_info=True)

    def write_tty_text(self, tty_name, text):
        """Write arbitrary text to a mapped TTY device."""
        if not tty_name or text is None:
            return False
        tty_path = f"/dev/{tty_name}"
        payload = text.encode("utf-8")
        fd = None
        try:
            fd = os.open(tty_path, os.O_WRONLY | os.O_NOCTTY)
            os.write(fd, payload)
            return True
        except OSError:
            logger.warning("Failed to write text via %s", tty_path, exc_info=True)
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    logger.debug("Failed to close TTY %s", tty_path, exc_info=True)

    def open_vscode(self, path):
        """Open VS Code pointed at the provided directory path."""
        if not path:
            return False
        try:
            result = subprocess.run(
                ["open", "-a", "Visual Studio Code", path],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            logger.warning("Failed to open VS Code for %s", path, exc_info=True)
            return False

        ok = result.returncode == 0
        if not ok:
            logger.warning(
                "Failed to open VS Code for %s: stderr=%r",
                path,
                result.stderr.strip() or None,
            )
        return ok

    def open_kaleidoscope_review(self, path):
        """Open a Kaleidoscope review for tracked uncommitted changes in a repo."""
        if not path:
            return "failed"
        if not Path(KSDIFF_PATH).exists():
            logger.warning("Kaleidoscope command-line tool not found at %s", KSDIFF_PATH)
            return "missing_ksdiff"

        try:
            repo_result = subprocess.run(
                ["git", "-C", path, "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if repo_result.returncode != 0:
                return "no_repo"
            repo_root = repo_result.stdout.strip()
            if not repo_root:
                return "no_repo"

            diff_result = subprocess.run(
                ["git", "-C", repo_root, "diff", "--name-status", "-M", "--relative", "HEAD", "--"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if diff_result.returncode != 0:
                return "failed"

            entries = []
            for line in diff_result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split("\t")
                status = parts[0]
                if status.startswith("R") and len(parts) >= 3:
                    entries.append(
                        {
                            "display_path": parts[2],
                            "head_path": parts[1],
                            "worktree_path": parts[2],
                        }
                    )
                elif len(parts) >= 2:
                    rel_path = parts[1]
                    entries.append(
                        {
                            "display_path": rel_path,
                            "head_path": rel_path,
                            "worktree_path": rel_path,
                        }
                    )

            untracked_result = subprocess.run(
                ["git", "-C", repo_root, "ls-files", "--others", "--exclude-standard"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if untracked_result.returncode != 0:
                return "failed"
            for line in untracked_result.stdout.splitlines():
                rel_path = line.strip()
                if not rel_path:
                    continue
                entries.append(
                    {
                        "display_path": rel_path,
                        "head_path": None,
                        "worktree_path": rel_path,
                    }
                )

            deduped_entries = {}
            for entry in entries:
                deduped_entries[entry["display_path"]] = entry
            entries = list(deduped_entries.values())
            if not entries:
                return "clean"

            snapshot_root = Path(tempfile.mkdtemp(prefix="clawdeck-ksdiff-"))
            left_dir = snapshot_root / "HEAD"
            right_dir = snapshot_root / "WORKTREE"
            snapshot_root.mkdir(parents=True, exist_ok=True)
            left_dir.mkdir()
            right_dir.mkdir()

            for entry in entries:
                display_path = entry["display_path"]
                left_path = left_dir / display_path
                right_path = right_dir / display_path
                left_path.parent.mkdir(parents=True, exist_ok=True)
                right_path.parent.mkdir(parents=True, exist_ok=True)

                head_path = entry["head_path"]
                if head_path:
                    head_result = subprocess.run(
                        ["git", "-C", repo_root, "show", f"HEAD:{head_path}"],
                        capture_output=True,
                        timeout=5,
                    )
                    if head_result.returncode == 0:
                        left_path.write_bytes(head_result.stdout)
                    else:
                        left_path.write_bytes(b"")
                else:
                    left_path.write_bytes(b"")

                worktree_rel_path = entry["worktree_path"]
                worktree_path = Path(repo_root) / worktree_rel_path if worktree_rel_path else None
                if worktree_path.exists() and worktree_path.is_file():
                    shutil.copy2(worktree_path, right_path)
                else:
                    right_path.write_bytes(b"")

            label = f"{Path(repo_root).name} review"
            result = subprocess.run(
                [KSDIFF_PATH, "--no-stdin", "-l", label, str(left_dir), str(right_dir)],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            logger.warning("Failed to open Kaleidoscope review for %s", path, exc_info=True)
            return "failed"

        ok = result.returncode == 0
        if not ok:
            logger.warning(
                "Failed to open Kaleidoscope review for %s: stderr=%r",
                path,
                result.stderr.strip() or None,
            )
            return "failed"
        return "opened"
