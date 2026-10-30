#!/usr/bin/env python3
"""Install this skill using only Python's standard library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import uuid

SOURCE = Path(__file__).resolve().parent.parent
MARKER = ".skill-install.json"
# Older copies of this installer used a package-specific marker name. Accept
# them so an existing copy install is still recognised as ours.
LEGACY_MARKERS = (".pr-contributor-install.json",)
FRAMEWORKS = {
    "claude": ".claude/skills", "codex": ".codex/skills",
    "agents": ".agents/skills", "dsh": ".dsh/skills",
    "magpie": ".config/magpie/library/skills", "hermes": ".hermes/skills",
}
IGNORED = {".git", "__pycache__", ".pytest_cache", MARKER, *LEGACY_MARKERS}


def within(path, parent):
    return path == parent or parent in path.parents


def skill_name(source):
    text = (source / "SKILL.md").read_text(encoding="utf-8")
    front = text.split("---", 2)
    match = re.search(r"^name:\s*['\"]?([a-zA-Z0-9_-]+)['\"]?\s*$", front[1], re.M) if len(front) == 3 and not front[0].strip() else None
    if not match:
        raise ValueError("SKILL.md needs a safe frontmatter name (letters, digits, '-' or '_')")
    return match[1]


def targets(home, only, override):
    if override:
        path = Path(override)
        if not path.is_absolute():
            raise ValueError("--skills-dir must be an absolute path to the actual skills directory")
        return [(only or "custom", path, True)]
    result = []
    for name, relative in FRAMEWORKS.items():
        if only and only != name:
            continue
        directory = home / relative
        # Hermes may have an existing home/profile without a skills folder yet.
        result.append((name, directory, name == "hermes" and directory.parent.is_dir()))
        if name == "hermes":
            profiles = home / ".hermes/profiles"
            if profiles.is_dir():
                for profile in sorted(profiles.iterdir()):
                    if profile.is_dir() and not profile.is_symlink():
                        result.append((f"hermes:{profile.name}", profile / "skills", True))
    return result


def tree_digest(root):
    digest = hashlib.sha256()
    def walk(directory, prefix=""):
        for item in sorted(directory.iterdir()):
            if item.name in IGNORED:
                continue
            relative = prefix + item.name
            digest.update(relative.encode() + b"\0")
            if item.is_symlink():
                digest.update(b"L" + os.readlink(item).encode())
            elif item.is_dir():
                digest.update(b"D")
                walk(item, relative + "/")
            else:
                digest.update(b"F" + item.read_bytes())
    walk(root)
    return digest.hexdigest()


def owned_copy(dest, source):
    for marker_name in (MARKER, *LEGACY_MARKERS):
        try:
            marker = dest / marker_name
            if not marker.is_symlink() and json.loads(marker.read_text())["source"] == str(source):
                return True
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return False


def validate(directory, source, name):
    parent = directory.resolve()
    dest = directory / name
    # A link at the destination can point at source; never traverse it for removal.
    lexical_dest = parent / name
    if within(lexical_dest, source) or within(source, lexical_dest):
        raise ValueError(f"refusing destination overlapping source: {dest}; choose another --skills-dir")
    if directory.exists() and not directory.is_dir():
        raise ValueError(f"skills directory is not a directory: {directory}")
    return dest


def backup(dest, root, discovery, source):
    resolved = root.resolve()
    if within(resolved, source) or any(within(resolved, path.resolve()) for path in discovery):
        raise ValueError(f"backup directory overlaps skill discovery/source: {root}; fix the directory layout")
    root.mkdir(parents=True, exist_ok=True)
    target = root / (dest.name + "-" + uuid.uuid4().hex)
    # rename deliberately fails closed (including cross-device failures), never
    # falls back to a partial recursive move or proceeds after a failed backup.
    dest.rename(target)
    print(f"  backup: {dest} -> {target}")
    return target


def install(directory, dest, source, copy, backups, discovery):
    if not copy and dest.is_symlink() and dest.resolve() == source:
        print(f"  unchanged: {dest}")
        return
    if copy and dest.is_dir() and not dest.is_symlink() and owned_copy(dest, source) and tree_digest(dest) == tree_digest(source):
        print(f"  unchanged copy: {dest}")
        return
    directory.mkdir(parents=True, exist_ok=True)
    # Stage before moving an existing install, so a failed copy preserves it.
    stage = Path(tempfile.mkdtemp(prefix=f".{dest.name}-stage-", dir=directory))
    staged = stage / dest.name
    saved = None
    try:
        if copy:
            shutil.copytree(source, staged, symlinks=True, ignore=shutil.ignore_patterns(*IGNORED))
            (staged / MARKER).write_text(json.dumps({"source": str(source)}) + "\n")
        else:
            staged.symlink_to(source, target_is_directory=True)
        if dest.exists() or dest.is_symlink():
            saved = backup(dest, backups, discovery, source)
        try:
            staged.rename(dest)
        except OSError:
            if saved is not None and not dest.exists() and not dest.is_symlink():
                saved.rename(dest)
            raise
        print(f"  installed {'copy' if copy else 'symlink'}: {dest}")
    finally:
        shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install this skill into detected agent skills directories (Python 3, no dependencies).", epilog="Examples: ./install.sh --target claude; ./install.sh --copy; ./install.sh --uninstall")
    parser.add_argument("--copy", action="store_true", help="copy skill files without .git instead of linking")
    parser.add_argument("--target", choices=tuple(FRAMEWORKS), help="select one framework (Hermes includes existing profiles)")
    parser.add_argument("--skills-dir", help="explicit absolute skills directory; overrides framework discovery")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--list", action="store_true", help="show destinations without changing files")
    action.add_argument("--uninstall", action="store_true", help="remove this source's symlinks; archive owned copies; preserve unrelated installs")
    args = parser.parse_args(argv)
    try:
        source = SOURCE.resolve()
        name = skill_name(source)
        home = Path.home()
        destinations = targets(home, args.target, args.skills_dir)
        # Validate every destination before the first mutation.
        validated = [(label, directory, create, validate(directory, source, name)) for label, directory, create in destinations]
        discovery = [home / relative for relative in FRAMEWORKS.values()] + [item[1] for item in validated]
        profiles = home / ".hermes/profiles"
        if profiles.is_dir():
            discovery.extend(profile / "skills" for profile in profiles.iterdir() if profile.is_dir())
        # Backups live under a per-skill path derived from the skill name, so
        # each package keeps its own namespace and never collides.
        backups = home / ".local/state" / name / "install-backups"
        failures = 0
        for label, directory, create, dest in validated:
            try:
                if args.list:
                    status = "installed" if dest.exists() or dest.is_symlink() else "available" if directory.is_dir() or create else "directory absent"
                    print(f"{label}: {status} -> {dest}")
                elif args.uninstall:
                    if dest.is_symlink() and dest.resolve() == source:
                        dest.unlink()
                        print(f"  removed symlink: {dest}")
                    elif dest.is_dir() and not dest.is_symlink() and owned_copy(dest, source):
                        backup(dest, backups, discovery, source)
                        print(f"  uninstalled copy (preserved in backups): {dest}")
                    elif dest.exists() or dest.is_symlink():
                        raise ValueError(f"unrelated install preserved: {dest}; inspect it manually")
                    else:
                        print(f"  not installed: {dest}")
                elif directory.is_dir() or create:
                    install(directory, dest, source, args.copy, backups, discovery)
                else:
                    print(f"  skipped {label}: directory absent ({directory})")
            except (OSError, ValueError) as error:
                failures += 1
                print(f"error: {label}: {error}; correct the path/permissions and retry", file=sys.stderr)
        return 1 if failures else 0
    except (OSError, ValueError) as error:
        print(f"error: {error}; correct the path/permissions and retry", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
