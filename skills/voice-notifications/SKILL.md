---
name: voice-notifications
description: Use when the user wants Codex to play, configure, add, list, select, cache, or clean up local voice notification audio, especially the codex-voice-notifier-jk plugin with 温柔 JK voice prompts for task-complete, failure, need-input, attention, checkpoint, clarify, understood, encourage, and praise events. Also use when maintaining the plugin or explaining its Stop-hook behavior.
---

# Voice Notifications

Use the bundled `scripts/voicectl.py` command to manage voice notification audio. The plugin stores user audio and cache files in `PLUGIN_DATA`; outside a plugin runtime it falls back to `~/.codex/voice-notifier-jk`.

## Workflow

1. Initialize storage with `python scripts/voicectl.py init`.
2. Add pre-generated audio with `python scripts/voicectl.py add --event done --file <audio> --text "<spoken text>" --tags done,warm,doctor`.
3. List configured lines with `python scripts/voicectl.py list`.
4. Test playback with `python scripts/voicectl.py play --event done`.
5. Clean stale cache entries with `python scripts/voicectl.py cleanup`.

Address the user as `博士` when proposing or generating spoken text unless they ask otherwise. The default voice should be `温柔 JK`: gentle, youthful, bright, caring, emotional, natural, and clear. Avoid flat mechanical narration and exaggerated acting.

## Audio Model

The manifest is `audio-manifest.json` in the writable data directory. Each item should include:

- `id`: stable identifier
- `event`: `done`, `failed`, `need_input`, `attention`, `checkpoint`, `clarify`, `understood`, `encourage`, or `praise`
- `file`: audio file under the manifest `audioRoot`
- `text`: exact spoken content
- `speaker`, `emotion`, `style`, `tags`, and `useWhen`
- `enabled`, `priority`, and `sha256`
- optional `bundled: true` and `bundleFile` when the audio ships in `assets/bundled-audio/`

Do not delete user audio automatically. The cleanup command may remove stale cache entries and old files under `cache/transcoded`. It deletes orphaned audio only when explicitly called with `--delete-orphans`.

## Bundled Audio

If the plugin should work immediately after download, place distributable `.wav` or `.mp3` files under `assets/bundled-audio/` and add matching manifest items with `bundled: true`. On `init` or first playback, `voicectl.py` copies bundled audio into the writable data directory and records the file hash. Only bundle audio that the user has permission to redistribute.

The bundled 温柔 JK set contains nine mapped events: `task_done.wav` for `done`, `task_failed.wav` for `failed`, `need_input.wav` for `need_input`, `audioattention.wav` for `attention`, `checkpoint.wav` for `checkpoint`, `博士，我想...我们还需要再沟通一下.wav` for `clarify`, `博士，我已经明白你的想法了.wav` for `understood`, `博士，不要沮丧，我们再来试试.wav` for `encourage`, and `博士，你的想法太棒了。.wav` for `praise`. Use the manifest `text`, `tags`, and `useWhen` fields to decide which line represents which situation.

## Hook Behavior

The plugin includes `hooks/hooks.json` with a `Stop` hook. When the plugin is enabled and the hook is trusted, Codex runs `voicectl.py hook-stop` after each assistant response. The hook classifies the final assistant message into an event, selects the highest-priority enabled matching audio item, updates the audio path cache, and plays it locally. If no audio exists, it falls back to a Windows system sound.
