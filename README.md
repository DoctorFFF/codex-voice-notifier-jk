# Codex Voice Notifier JK

Codex Voice Notifier JK is a local Codex plugin that plays short, pre-generated voice prompts when Codex finishes a response.

The default sound design is **温柔 JK 的声音**: gentle, youthful, bright, caring, emotional, natural, and clear. The default spoken style addresses the user as `博士`.

## What It Does

- Plays a voice prompt from a Codex `Stop` hook after assistant responses.
- Supports bundled default audio in `assets/bundled-audio/` so the plugin can work out of the box.
- Stores runtime audio and cache files in the plugin writable data directory.
- Maintains an audio manifest with text, speaker, emotion, tags, use case, priority, and file hash.
- Maintains a path/hash cache for fast lookup.
- Falls back to a Windows system sound if no local audio has been added yet.
- Provides explicit cleanup rules so personal audio is not deleted unexpectedly.

## Codex Login Note

This plugin is loaded by the local Codex client. Whether your Codex client is authenticated with an API key or an account should not change the plugin files themselves. The practical friction is hook trust: Codex requires you to review and trust plugin-bundled hooks before they run.

## Bundled Audio

Yes, private or custom audio can be included in the package if you want the plugin to be open-box usable. This repository includes the current 温柔 JK notification set:

| Event | File | Spoken Text |
| --- | --- | --- |
| `done` | `assets/bundled-audio/task_done.wav` | 博士，任务完成了。 |
| `failed` | `assets/bundled-audio/task_failed.wav` | 博士，任务运行失败了，我已经停下来了，需要你看一下。 |
| `need_input` | `assets/bundled-audio/need_input.wav` | 博士，我需要你做个决定，回来选一下吧。 |
| `attention` | `assets/bundled-audio/audioattention.wav` | 博士，这里有一件事需要你注意。 |
| `checkpoint` | `assets/bundled-audio/checkpoint.wav` | 博士，阶段性结果已经准备好了。 |

Put redistributable audio files here:

```text
assets/bundled-audio/
```

Then add matching items to:

```text
assets/default-audio-manifest.json
```

Bundled items should use:

```json
{
  "id": "task_done_jk",
  "event": "done",
  "file": "task_done.wav",
  "bundleFile": "task_done.wav",
  "text": "博士，任务完成了。",
  "speaker": "温柔 JK",
  "emotion": "warm",
  "style": "gentle-jk",
  "tags": ["done", "jk", "warm", "doctor", "bundled"],
  "useWhen": "Codex 完成一次正常任务或给出最终结果",
  "enabled": true,
  "priority": 100,
  "sha256": "",
  "bundled": true
}
```

On `init` or first playback, `voicectl.py` copies bundled audio from `assets/bundled-audio/` into the writable plugin data directory and records the file hash. Only bundle audio you have permission to redistribute.

## Install From A Local Checkout

Clone or copy this repository into your plugin directory:

```powershell
git clone https://github.com/DoctorFFF/codex-voice-notifier-jk C:\Users\14187\plugins\codex-voice-notifier-jk
```

For the personal marketplace flow, make sure `C:\Users\14187\.agents\plugins\marketplace.json` contains:

```json
{
  "name": "personal",
  "interface": {
    "displayName": "Personal"
  },
  "plugins": [
    {
      "name": "codex-voice-notifier-jk",
      "source": {
        "source": "local",
        "path": "./plugins/codex-voice-notifier-jk"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

After enabling the plugin, review and trust the bundled hook in Codex. In the CLI this is done with `/hooks`; in the Codex app, open the hook review surface when prompted.

## Quick Start

Initialize storage:

```powershell
D:\python312\python.exe C:\Users\14187\plugins\codex-voice-notifier-jk\scripts\voicectl.py init
```

Add your MiniMax 温柔 JK completion audio:

```powershell
D:\python312\python.exe C:\Users\14187\plugins\codex-voice-notifier-jk\scripts\voicectl.py add `
  --event done `
  --file D:\Downloads\task_done.wav `
  --id task_done_jk `
  --text "博士，任务完成了。" `
  --speaker "温柔 JK" `
  --emotion warm `
  --style gentle-jk `
  --tags done,jk,warm,doctor,short `
  --use-when "Codex 完成一次正常任务或给出最终结果" `
  --priority 100 `
  --replace
```

Test playback:

```powershell
D:\python312\python.exe C:\Users\14187\plugins\codex-voice-notifier-jk\scripts\voicectl.py play --event done
```

List audio:

```powershell
D:\python312\python.exe C:\Users\14187\plugins\codex-voice-notifier-jk\scripts\voicectl.py list
```

## Recommended Voice Lines

| Event | Suggested Text | Voice | Use When |
| --- | --- | --- | --- |
| `done` | 博士，任务完成了。 | 温柔 JK | Normal completion |
| `failed` | 博士，任务运行失败了，我已经停下来了，需要你看一下。 | 温柔 JK, slightly concerned | Unrecovered failure |
| `need_input` | 博士，我需要你做个决定，回来选一下吧。 | 温柔 JK, inviting | User decision required |
| `attention` | 博士，这里有一件事需要你注意。 | 温柔 JK, serious but soft | Warning or important finding |
| `checkpoint` | 博士，阶段性结果已经准备好了。 | 温柔 JK, upbeat | Useful intermediate result |

Generate these with MiniMax or another TTS service, then add each file with `voicectl.py add`.

## Manifest Format

Audio items live in `audio-manifest.json` under the plugin data directory:

```json
{
  "id": "task_done_jk",
  "event": "done",
  "file": "task_done.wav",
  "text": "博士，任务完成了。",
  "speaker": "温柔 JK",
  "emotion": "warm",
  "style": "gentle-jk",
  "tags": ["done", "jk", "warm", "doctor"],
  "useWhen": "Codex 完成一次正常任务或给出最终结果",
  "enabled": true,
  "priority": 100,
  "sha256": "...",
  "createdAt": "2026-06-19T00:00:00Z"
}
```

Codex chooses the highest-priority enabled item matching the event. If the matching file is missing or its hash changed, the item is skipped and the cache is repaired during cleanup.

## Cache And Cleanup

The plugin keeps:

- `state/audio-cache.json`: cache of resolved audio paths and hashes.
- `state/selection-history.jsonl`: lightweight playback history.
- `cache/transcoded/`: temporary converted files, if future workflows need conversion.

Cleanup rules:

- User audio under `audio/` is never deleted automatically.
- `audio-cache.json` is disposable and can be rebuilt.
- Missing files, changed hashes, or removed manifest items remove only cache entries.
- Temporary files under `cache/transcoded/` can be deleted after 7 days.
- Orphaned audio is deleted only when you explicitly run:

```powershell
D:\python312\python.exe C:\Users\14187\plugins\codex-voice-notifier-jk\scripts\voicectl.py cleanup --delete-orphans
```

All deletion is constrained to the plugin data directory.

## Development

Validate the plugin:

```powershell
D:\python312\python.exe C:\Users\14187\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py C:\Users\14187\plugins\codex-voice-notifier-jk
```

The public plugin directory is not self-serve yet, so GitHub distribution plus a personal marketplace entry is the practical route today.
