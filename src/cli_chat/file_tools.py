"""File CRUD tools for the CLI chat, sandboxed to a working directory.

All paths are resolved against ``workdir`` and rejected with a clear
error if they escape it (either via ``..`` or symlinks pointing
outside). This keeps the model from reading or writing arbitrary files
on disk.
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Annotated

from langchain_core.tools import tool


def _resolve(workdir: Path, raw_path: str) -> Path:
    """Resolve ``raw_path`` against ``workdir`` and ensure it stays inside.

    Raises ``ValueError`` if the resolved path escapes the sandbox.
    """
    candidate = (workdir / raw_path).resolve()
    workdir_resolved = workdir.resolve()
    try:
        candidate.relative_to(workdir_resolved)
    except ValueError as exc:
        raise ValueError(
            f"path '{raw_path}' escapes the working directory "
            f"'{workdir_resolved}'"
        ) from exc
    return candidate


def build_file_tools(workdir: str | os.PathLike[str]) -> list:
    """Create the file CRUD tools bound to ``workdir``."""
    root = Path(workdir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    @tool
    def read_file(
        path: Annotated[
            str,
            "Path relative to the working directory, e.g. 'src/main.py'.",
        ],
    ) -> str:
        """Read the contents of a text file. Returns an error string if the
        file is missing, not a regular file, or larger than 1 MB."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        if not target.exists():
            return f"error: '{path}' does not exist"
        if not target.is_file():
            return f"error: '{path}' is not a regular file"
        if target.stat().st_size > 1_000_000:
            return f"error: '{path}' is larger than 1 MB; refusing to read"
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"error: '{path}' is not a UTF-8 text file"

    @tool
    def write_file(
        path: Annotated[
            str,
            "Path relative to the working directory, e.g. 'notes/todo.md'.",
        ],
        content: Annotated[str, "The full text content to write."],
    ) -> str:
        """Create or overwrite a text file with the given content. Creates
        parent directories as needed."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} chars to {target.relative_to(root)}"

    @tool
    def list_dir(
        path: Annotated[
            str,
            "Directory path relative to the working directory. Use '.' for the root.",
        ] = ".",
    ) -> str:
        """List the immediate contents of a directory (names + type marker)."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        if not target.exists():
            return f"error: '{path}' does not exist"
        if not target.is_dir():
            return f"error: '{path}' is not a directory"
        entries: list[str] = []
        for child in sorted(target.iterdir()):
            if child.is_dir():
                entries.append(f"[dir]  {child.name}")
            elif child.is_file():
                entries.append(f"[file] {child.name}")
            else:
                entries.append(f"[?]    {child.name}")
        if not entries:
            return "(empty directory)"
        return "\n".join(entries)

    @tool
    def delete_file(
        path: Annotated[
            str,
            "Path relative to the working directory to delete.",
        ],
    ) -> str:
        """Delete a file or empty directory. For non-empty directories use
        ``delete_dir_recursive``."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        if not target.exists():
            return f"error: '{path}' does not exist"
        if target.is_dir():
            return (
                f"error: '{path}' is a directory; use delete_dir_recursive "
                "to remove it"
            )
        target.unlink()
        return f"deleted {target.relative_to(root)}"

    @tool
    def delete_dir_recursive(
        path: Annotated[
            str,
            "Directory path relative to the working directory to remove.",
        ],
    ) -> str:
        """Recursively delete a directory and all of its contents. This is
        destructive; the model should confirm with the user first if the
        directory may be important."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        if not target.exists():
            return f"error: '{path}' does not exist"
        if not target.is_dir():
            return f"error: '{path}' is not a directory"
        # Refuse to delete the sandbox root itself.
        if target == root:
            return "error: refusing to delete the working directory root"
        shutil.rmtree(target)
        return f"removed directory {target.relative_to(root)}"

    @tool
    def file_info(
        path: Annotated[
            str,
            "Path relative to the working directory.",
        ],
    ) -> str:
        """Return existence, type, size (bytes) and modification time for a path."""
        try:
            target = _resolve(root, path)
        except ValueError as e:
            return f"error: {e}"
        if not target.exists():
            return f"error: '{path}' does not exist"
        stat = target.stat()
        kind = (
            "directory"
            if target.is_dir()
            else "file"
            if target.is_file()
            else "other"
        )
        mtime = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        return (
            f"exists: True\n"
            f"type: {kind}\n"
            f"size_bytes: {stat.st_size}\n"
            f"modified: {mtime}\n"
            f"path: {target.relative_to(root)}"
        )

    return [
        read_file,
        write_file,
        list_dir,
        delete_file,
        delete_dir_recursive,
        file_info,
    ]


TOOL_DESCRIPTIONS = {
    "read_file": "read a text file",
    "write_file": "create or overwrite a file",
    "list_dir": "list directory contents",
    "delete_file": "delete a single file",
    "delete_dir_recursive": "recursively delete a directory",
    "file_info": "existence/type/size/mtime for a path",
}
