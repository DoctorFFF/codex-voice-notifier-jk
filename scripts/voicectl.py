#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


EVENTS = ("done", "failed", "need_input", "attention", "checkpoint")
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".wma"}
PLUGIN_ROOT = Path(os.environ.get("PLUGIN_ROOT", Path(__file__).resolve().parents[1])).resolve()
PLUGIN_DATA = Path(
    os.environ.get(
        "PLUGIN_DATA",
        os.environ.get(
            "CODEX_VOICE_NOTIFIER_JK_HOME",
            os.environ.get("CODEX_VOICE_NOTIFIER_HOME", Path.home() / ".codex" / "voice-notifier-jk"),
        ),
    )
).resolve()
DEFAULT_MANIFEST = PLUGIN_ROOT / "assets" / "default-audio-manifest.json"
BUNDLED_AUDIO_ROOT = PLUGIN_ROOT / "assets" / "bundled-audio"
MANIFEST_PATH = Path(
    os.environ.get(
        "CODEX_VOICE_NOTIFIER_JK_MANIFEST",
        os.environ.get("CODEX_VOICE_NOTIFIER_MANIFEST", PLUGIN_DATA / "audio-manifest.json"),
    )
).resolve()
CACHE_PATH = PLUGIN_DATA / "state" / "audio-cache.json"
HISTORY_PATH = PLUGIN_DATA / "state" / "selection-history.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def ensure_layout() -> None:
    PLUGIN_DATA.mkdir(parents=True, exist_ok=True)
    (PLUGIN_DATA / "audio").mkdir(parents=True, exist_ok=True)
    (PLUGIN_DATA / "state").mkdir(parents=True, exist_ok=True)
    (PLUGIN_DATA / "cache" / "transcoded").mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        if DEFAULT_MANIFEST.exists():
            shutil.copyfile(DEFAULT_MANIFEST, MANIFEST_PATH)
        else:
            write_json(
                MANIFEST_PATH,
                {
                    "schemaVersion": 1,
                    "plugin": "codex-voice-notifier-jk",
                    "defaultEvent": "done",
                    "audioRoot": "audio",
                    "items": [],
                },
            )
    merge_default_manifest()
    seed_bundled_audio()


def merge_default_manifest() -> None:
    if not DEFAULT_MANIFEST.exists() or not MANIFEST_PATH.exists():
        return

    defaults = read_json(DEFAULT_MANIFEST, {})
    manifest = read_json(MANIFEST_PATH, {})
    changed = False

    for key in ("schemaVersion", "plugin", "defaultEvent", "audioRoot", "voiceDirection"):
        if key in defaults and manifest.get(key) != defaults[key]:
            if key in ("schemaVersion", "plugin", "voiceDirection") or key not in manifest:
                manifest[key] = defaults[key]
                changed = True

    for key in ("events", "selection", "cleanupPolicy"):
        default_value = defaults.get(key)
        if not isinstance(default_value, dict):
            continue
        current_value = manifest.setdefault(key, {})
        if not isinstance(current_value, dict):
            manifest[key] = default_value
            changed = True
            continue
        for child_key, child_value in default_value.items():
            if child_key not in current_value:
                current_value[child_key] = child_value
                changed = True

    manifest.setdefault("items", [])
    default_item_ids = {
        item.get("id")
        for item in defaults.get("items") or []
        if isinstance(item, dict) and item.get("id")
    }
    retained_items = []
    for item in manifest["items"]:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        bundle_name = str(item.get("bundleFile") or item.get("file") or "").strip()
        source = (BUNDLED_AUDIO_ROOT / Path(bundle_name).name).resolve() if bundle_name else None
        obsolete_bundle = (
            bool(item.get("bundled"))
            and item_id not in default_item_ids
            and (source is None or not source.exists())
        )
        if obsolete_bundle:
            changed = True
            continue
        retained_items.append(item)

    if len(retained_items) != len(manifest["items"]):
        manifest["items"] = retained_items

    existing_by_id = {
        item.get("id"): item
        for item in manifest["items"]
        if isinstance(item, dict) and item.get("id")
    }

    for default_item in defaults.get("items") or []:
        if not isinstance(default_item, dict) or not default_item.get("id"):
            continue

        item_id = default_item["id"]
        existing = existing_by_id.get(item_id)
        if existing is None:
            manifest["items"].append(default_item)
            existing_by_id[item_id] = default_item
            changed = True
            continue

        if not existing.get("bundled"):
            continue

        preserve_keys = {"enabled", "priority"}
        for key, value in default_item.items():
            if key in preserve_keys and key in existing:
                continue
            if existing.get(key) != value:
                existing[key] = value
                changed = True

    if changed:
        save_manifest(manifest)


def seed_bundled_audio() -> None:
    if not BUNDLED_AUDIO_ROOT.exists():
        return

    manifest = read_json(MANIFEST_PATH, {})
    manifest.setdefault("audioRoot", "audio")
    manifest.setdefault("items", [])
    root = audio_root(manifest)
    changed = False

    for item in manifest["items"]:
        if not item.get("bundled"):
            continue

        bundle_name = str(item.get("bundleFile") or item.get("file") or "").strip()
        if not bundle_name:
            continue

        source = (BUNDLED_AUDIO_ROOT / Path(bundle_name).name).resolve()
        if not source.exists() or source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        destination_name = Path(str(item.get("file") or source.name)).name
        destination = (root / destination_name).resolve()
        if not is_inside(destination, root):
            continue

        source_hash = sha256_file(source)
        if not destination.exists() or sha256_file(destination) != source_hash:
            shutil.copyfile(source, destination)
            changed = True

        if item.get("sha256") != source_hash:
            item["sha256"] = source_hash
            changed = True

    if changed:
        save_manifest(manifest)


def load_manifest() -> dict[str, Any]:
    ensure_layout()
    manifest = read_json(MANIFEST_PATH, {})
    manifest.setdefault("schemaVersion", 1)
    manifest.setdefault("defaultEvent", "done")
    manifest.setdefault("audioRoot", "audio")
    manifest.setdefault("selection", {"fallbackSystemSound": "Asterisk"})
    manifest.setdefault("items", [])
    return manifest


def save_manifest(manifest: dict[str, Any]) -> None:
    write_json(MANIFEST_PATH, manifest)


def audio_root(manifest: dict[str, Any]) -> Path:
    configured = Path(str(manifest.get("audioRoot") or "audio"))
    root = configured if configured.is_absolute() else PLUGIN_DATA / configured
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def audio_path_for_item(manifest: dict[str, Any], item: dict[str, Any]) -> Path | None:
    file_value = str(item.get("file") or "").strip()
    if not file_value:
        return None
    path = Path(file_value)
    if not path.is_absolute():
        path = audio_root(manifest) / path
    return path.resolve()


def load_cache() -> dict[str, Any]:
    return read_json(CACHE_PATH, {"schemaVersion": 1, "items": {}})


def save_cache(cache: dict[str, Any]) -> None:
    write_json(CACHE_PATH, cache)


def update_cache(manifest: dict[str, Any], item: dict[str, Any], path: Path) -> None:
    cache = load_cache()
    cache.setdefault("schemaVersion", 1)
    cache.setdefault("items", {})
    cache["items"][item["id"]] = {
        "event": item.get("event"),
        "path": str(path),
        "sha256": sha256_file(path) if path.exists() else item.get("sha256", ""),
        "text": item.get("text", ""),
        "lastUsedAt": utc_now(),
    }
    save_cache(cache)


def append_history(event: str, item: dict[str, Any] | None, outcome: str) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "at": utc_now(),
        "event": event,
        "itemId": item.get("id") if item else None,
        "outcome": outcome,
    }
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def valid_audio_item(manifest: dict[str, Any], item: dict[str, Any]) -> tuple[bool, Path | None]:
    if not item.get("enabled", True):
        return False, None
    path = audio_path_for_item(manifest, item)
    if path is None or not path.exists() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return False, path
    expected_hash = str(item.get("sha256") or "")
    if expected_hash and sha256_file(path) != expected_hash:
        return False, path
    return True, path


def select_item(manifest: dict[str, Any], event: str, item_id: str | None = None) -> tuple[dict[str, Any] | None, Path | None]:
    items = list(manifest.get("items") or [])
    if item_id:
        items = [item for item in items if item.get("id") == item_id]
    else:
        items = [item for item in items if item.get("event") == event]

    candidates: list[tuple[int, dict[str, Any], Path]] = []
    for item in items:
        ok, path = valid_audio_item(manifest, item)
        if ok and path is not None:
            candidates.append((int(item.get("priority", 0)), item, path))

    if not candidates and not item_id and event != manifest.get("defaultEvent", "done"):
        return select_item(manifest, str(manifest.get("defaultEvent", "done")))

    if not candidates:
        return None, None

    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    _, item, path = candidates[0]
    return item, path


def fallback_sound(manifest: dict[str, Any]) -> str:
    selection = manifest.get("selection") or {}
    return str(selection.get("fallbackSystemSound") or "Asterisk")


def play_audio(path: Path | None, manifest: dict[str, Any], quiet: bool = False, timeout: int = 30) -> int:
    if sys.platform.startswith("win"):
        script = PLUGIN_ROOT / "scripts" / "play_voice.ps1"
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-FallbackSound",
            fallback_sound(manifest),
            "-TimeoutSeconds",
            str(timeout),
        ]
        if path is not None:
            command += ["-AudioPath", str(path)]
        if quiet:
            command.append("-Quiet")
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
            check=False,
            timeout=timeout + 5,
        )
        return result.returncode

    if path is None:
        return 0

    players = (
        ["afplay", str(path)],
        ["paplay", str(path)],
        ["aplay", str(path)],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
    )
    for command in players:
        try:
            return subprocess.run(
                command,
                stdout=subprocess.DEVNULL if quiet else None,
                stderr=subprocess.DEVNULL if quiet else None,
                check=False,
                timeout=timeout,
            ).returncode
        except FileNotFoundError:
            continue
    return 0


def classify_event(text: str) -> str:
    lowered = text.lower()
    failed_keywords = ("failed", "failure", "error", "exception", "blocked", "失败", "报错", "错误", "没能", "无法完成")
    need_input_keywords = ("need your input", "choose", "which", "confirm", "需要你", "请选择", "选一下", "确认", "决定")
    checkpoint_keywords = ("checkpoint", "intermediate", "阶段", "阶段性", "中间结果")
    attention_keywords = ("warning", "risk", "注意", "风险", "警告")

    if any(keyword in lowered for keyword in failed_keywords):
        return "failed"
    if any(keyword in lowered for keyword in need_input_keywords):
        return "need_input"
    if any(keyword in lowered for keyword in checkpoint_keywords):
        return "checkpoint"
    if any(keyword in lowered for keyword in attention_keywords):
        return "attention"
    return "done"


def extract_last_message(payload: dict[str, Any]) -> str:
    value = payload.get("last_assistant_message")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text = value.get("text") or value.get("content")
        if isinstance(text, str):
            return text
    for key in ("message", "response", "content"):
        candidate = payload.get(key)
        if isinstance(candidate, str):
            return candidate
    return ""


def cmd_init(_: argparse.Namespace) -> int:
    ensure_layout()
    print(f"dataRoot={PLUGIN_DATA}")
    print(f"manifest={MANIFEST_PATH}")
    print(f"audioRoot={audio_root(load_manifest())}")
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    source = Path(args.file).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise SystemExit(f"audio file not found: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise SystemExit(f"unsupported audio extension: {source.suffix}")

    digest = sha256_file(source)
    item_id = args.id or f"{args.event}_{digest[:12]}"
    extension = source.suffix.lower()
    destination = audio_root(manifest) / f"{item_id}{extension}"

    if destination.exists() and not args.replace:
        raise SystemExit(f"target already exists: {destination}; use --replace to overwrite")

    existing_items = list(manifest.get("items") or [])
    if any(item.get("id") == item_id for item in existing_items) and not args.replace:
        raise SystemExit(f"item id already exists: {item_id}; use --replace to overwrite")

    shutil.copyfile(source, destination)
    tags = [part.strip() for part in ",".join(args.tags or []).split(",") if part.strip()]
    item = {
        "id": item_id,
        "event": args.event,
        "file": destination.name,
        "text": args.text,
        "speaker": args.speaker or "",
        "emotion": args.emotion or "warm",
        "style": args.style or "natural",
        "tags": tags,
        "useWhen": args.use_when or "",
        "enabled": not args.disabled,
        "priority": args.priority,
        "sha256": sha256_file(destination),
        "createdAt": utc_now(),
    }

    manifest["items"] = [entry for entry in existing_items if entry.get("id") != item_id]
    manifest["items"].append(item)
    save_manifest(manifest)
    update_cache(manifest, item, destination)
    print(json.dumps(item, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    items = list(manifest.get("items") or [])
    if args.json:
        print(json.dumps({"manifest": str(MANIFEST_PATH), "items": items}, ensure_ascii=False, indent=2))
        return 0

    print(f"manifest: {MANIFEST_PATH}")
    if not items:
        print("No audio items configured yet.")
        return 0

    for item in items:
        ok, path = valid_audio_item(manifest, item)
        status = "ok" if ok else "missing"
        print(f"{item.get('id')} [{item.get('event')}] {status} priority={item.get('priority', 0)}")
        print(f"  text: {item.get('text', '')}")
        print(f"  file: {path if path else item.get('file', '')}")
        print(f"  tags: {', '.join(item.get('tags') or [])}")
    return 0


def cmd_play(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    item, path = select_item(manifest, args.event, args.id)
    if item and path:
        update_cache(manifest, item, path)
        append_history(args.event, item, "audio")
    else:
        append_history(args.event, None, "fallback")
    if args.dry_run:
        print(json.dumps({"event": args.event, "item": item, "path": str(path) if path else None}, ensure_ascii=False, indent=2))
        return 0
    return play_audio(path, manifest, quiet=args.quiet, timeout=args.timeout)


def cmd_hook_stop(_: argparse.Namespace) -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        message = extract_last_message(payload)
        event = classify_event(message)
        manifest = load_manifest()
        item, path = select_item(manifest, event)
        if item and path:
            update_cache(manifest, item, path)
            append_history(event, item, "audio")
        else:
            append_history(event, None, "fallback")
        play_audio(path, manifest, quiet=True, timeout=30)
        print(json.dumps({"continue": True, "suppressOutput": True}))
        return 0
    except Exception as exc:
        log_path = PLUGIN_DATA / "state" / "hook-errors.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now()} {type(exc).__name__}: {exc}\n")
        print(json.dumps({"continue": True, "suppressOutput": True}))
        return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    cache = load_cache()
    items_by_id = {item.get("id"): item for item in manifest.get("items") or []}
    removed_cache_entries: list[str] = []

    for item_id, record in list((cache.get("items") or {}).items()):
        item = items_by_id.get(item_id)
        path = Path(record.get("path", "")).resolve() if record.get("path") else None
        remove = item is None or path is None or not path.exists()
        if not remove and item and item.get("sha256"):
            remove = sha256_file(path) != item.get("sha256")
        if remove:
            cache["items"].pop(item_id, None)
            removed_cache_entries.append(item_id)

    removed_temp_files: list[str] = []
    ttl_days = int(((manifest.get("cleanupPolicy") or {}).get("transcodedCacheTtlDays")) or args.ttl_days)
    deadline = datetime.now(timezone.utc) - timedelta(days=ttl_days)
    transcoded_root = (PLUGIN_DATA / "cache" / "transcoded").resolve()
    if transcoded_root.exists():
        for path in transcoded_root.rglob("*"):
            if path.is_file():
                modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                if modified < deadline and is_inside(path, transcoded_root):
                    path.unlink()
                    removed_temp_files.append(str(path))

    removed_orphans: list[str] = []
    if args.delete_orphans:
        referenced = {
            audio_path_for_item(manifest, item)
            for item in manifest.get("items") or []
            if audio_path_for_item(manifest, item) is not None
        }
        root = audio_root(manifest)
        for path in root.iterdir():
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and path.resolve() not in referenced:
                if is_inside(path, root):
                    path.unlink()
                    removed_orphans.append(str(path))

    save_cache(cache)
    print(
        json.dumps(
            {
                "removedCacheEntries": removed_cache_entries,
                "removedTempFiles": removed_temp_files,
                "removedOrphans": removed_orphans,
                "deleteOrphans": bool(args.delete_orphans),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Codex voice notification audio.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the writable data directory and manifest.")
    init.set_defaults(func=cmd_init)

    add = subparsers.add_parser("add", help="Add an audio file to the manifest and local audio store.")
    add.add_argument("--event", choices=EVENTS, required=True)
    add.add_argument("--file", required=True)
    add.add_argument("--text", required=True)
    add.add_argument("--id")
    add.add_argument("--speaker")
    add.add_argument("--emotion")
    add.add_argument("--style")
    add.add_argument("--tags", action="append")
    add.add_argument("--use-when", default="")
    add.add_argument("--priority", type=int, default=100)
    add.add_argument("--disabled", action="store_true")
    add.add_argument("--replace", action="store_true")
    add.set_defaults(func=cmd_add)

    list_cmd = subparsers.add_parser("list", help="List configured voice lines.")
    list_cmd.add_argument("--json", action="store_true")
    list_cmd.set_defaults(func=cmd_list)

    play = subparsers.add_parser("play", help="Play the selected event or item.")
    play.add_argument("--event", choices=EVENTS, default="done")
    play.add_argument("--id")
    play.add_argument("--quiet", action="store_true")
    play.add_argument("--dry-run", action="store_true")
    play.add_argument("--timeout", type=int, default=30)
    play.set_defaults(func=cmd_play)

    hook_stop = subparsers.add_parser("hook-stop", help="Codex Stop hook entrypoint.")
    hook_stop.set_defaults(func=cmd_hook_stop)

    cleanup = subparsers.add_parser("cleanup", help="Clean stale cache entries and optional orphan files.")
    cleanup.add_argument("--ttl-days", type=int, default=7)
    cleanup.add_argument("--delete-orphans", action="store_true")
    cleanup.set_defaults(func=cmd_cleanup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
