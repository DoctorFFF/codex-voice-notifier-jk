# Codex Voice Notifier JK

Codex Voice Notifier JK is a local Codex plugin that plays short voice prompts when Codex finishes a response.

The bundled voice style is **温柔 JK 的声音**: gentle, bright, caring, emotional, natural, and clear. The default spoken address is `博士`.

## For Humans

### What You Get

This plugin ships with nine ready-to-use voice prompts: five task-state prompts and four conversational feedback prompts.

| Event | Audio | Spoken Text |
| --- | --- | --- |
| Done | `task_done.wav` | 博士，任务完成了。 |
| Failed | `task_failed.wav` | 博士，任务运行失败了，我已经停下来了，需要你看一下。 |
| Need input | `need_input.wav` | 博士，我需要你做个决定，回来选一下吧。 |
| Attention | `audioattention.wav` | 博士，这里有一件事需要你注意。 |
| Checkpoint | `checkpoint.wav` | 博士，阶段性结果已经准备好了。 |
| Clarify | `博士，我想...我们还需要再沟通一下.wav` | 博士，我想...我们还需要再沟通一下 |
| Understood | `博士，我已经明白你的想法了.wav` | 博士，我已经明白你的想法了 |
| Encourage | `博士，不要沮丧，我们再来试试.wav` | 博士，不要沮丧，我们再来试试 |
| Praise | `博士，你的想法太棒了。.wav` | 博士，你的想法太棒了。 |

The audio files are bundled in:

```text
assets/bundled-audio/
```

Codex reads their meaning from:

```text
assets/default-audio-manifest.json
```

### Install

Clone the repository:

```powershell
git clone https://github.com/DoctorFFF/codex-voice-notifier-jk C:\Users\<you>\plugins\codex-voice-notifier-jk
```

Add it to your personal Codex marketplace:

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

On Windows, that marketplace file usually lives at:

```text
C:\Users\<you>\.agents\plugins\marketplace.json
```

Restart Codex, enable the plugin, then review and trust the bundled hook when Codex asks.

### DIY Your Own Voice

Use MiniMax or another TTS service to generate a short emotional audio clip. Keep each line short, warm, and recognizable.

To replace a bundled prompt:

1. Put your new `.wav` file in `assets/bundled-audio/`.
2. Update the matching item in `assets/default-audio-manifest.json`.
3. Keep `text` as the exact spoken words.
4. Use `tags`, `emotion`, and `useWhen` to describe how the clip should be used.
5. Commit and push the changed audio plus manifest.

To add a runtime-only voice line without changing the repository:

```powershell
D:\python312\python.exe C:\Users\<you>\plugins\codex-voice-notifier-jk\scripts\voicectl.py add `
  --event done `
  --file D:\Downloads\my_done.wav `
  --text "博士，任务完成了。" `
  --speaker "温柔 JK" `
  --emotion warm `
  --style gentle-jk `
  --tags done,jk,warm,doctor `
  --use-when "Codex 完成一次正常任务或给出最终结果" `
  --priority 120
```

Test playback:

```powershell
D:\python312\python.exe C:\Users\<you>\plugins\codex-voice-notifier-jk\scripts\voicectl.py play --event done
```

List configured voices:

```powershell
D:\python312\python.exe C:\Users\<you>\plugins\codex-voice-notifier-jk\scripts\voicectl.py list
```

### Cleanup

The plugin will not automatically delete your user audio. Temporary cache can be cleaned safely:

```powershell
D:\python312\python.exe C:\Users\<you>\plugins\codex-voice-notifier-jk\scripts\voicectl.py cleanup
```

Only delete orphaned audio when you really mean it:

```powershell
D:\python312\python.exe C:\Users\<you>\plugins\codex-voice-notifier-jk\scripts\voicectl.py cleanup --delete-orphans
```

## For Codex

### Purpose

Use this plugin to play local voice notifications after Codex responses. Prefer the bundled 温柔 JK voice lines unless the user configures another line with higher priority.

### Runtime Paths

- Plugin root: `codex-voice-notifier-jk`
- Bundled audio: `assets/bundled-audio/`
- Default manifest: `assets/default-audio-manifest.json`
- Runtime data root: `PLUGIN_DATA`, or `~/.codex/voice-notifier-jk` outside plugin runtime
- Runtime manifest: `<data root>/audio-manifest.json`
- Runtime audio: `<data root>/audio/`
- Cache: `<data root>/state/audio-cache.json`

### Events

Use these event names exactly:

| Event | Use When |
| --- | --- |
| `done` | Normal completion or final result |
| `failed` | Failed command, unrecovered error, blocked task |
| `need_input` | User must choose, confirm, or provide missing info |
| `attention` | Important warning, risk, or notable finding |
| `checkpoint` | Useful intermediate or staged result |
| `clarify` | Need more discussion or clarification |
| `understood` | Acknowledge that Codex understands the user's idea |
| `encourage` | Encourage the user after a setback or retry |
| `praise` | Positively acknowledge a strong user idea |

### Bundled Mapping

| Event | Item ID | File |
| --- | --- | --- |
| `done` | `task_done_jk` | `task_done.wav` |
| `failed` | `task_failed_jk` | `task_failed.wav` |
| `need_input` | `need_input_jk` | `need_input.wav` |
| `attention` | `attention_jk` | `audioattention.wav` |
| `checkpoint` | `checkpoint_jk` | `checkpoint.wav` |
| `clarify` | `clarify_jk` | `博士，我想...我们还需要再沟通一下.wav` |
| `understood` | `understood_jk` | `博士，我已经明白你的想法了.wav` |
| `encourage` | `encourage_jk` | `博士，不要沮丧，我们再来试试.wav` |
| `praise` | `praise_jk` | `博士，你的想法太棒了。.wav` |

### Commands

Initialize or refresh bundled audio:

```powershell
D:\python312\python.exe scripts\voicectl.py init
```

Dry-run event selection:

```powershell
D:\python312\python.exe scripts\voicectl.py play --event done --dry-run
```

Play an event:

```powershell
D:\python312\python.exe scripts\voicectl.py play --event done
```

List configured lines:

```powershell
D:\python312\python.exe scripts\voicectl.py list
```

### Selection Rules

- Read `audio-manifest.json`.
- Filter to enabled items with matching `event`.
- Skip missing files or files whose `sha256` does not match.
- Pick the highest `priority`.
- If no matching file exists, fall back to the configured Windows system sound.
- The `Stop` hook calls `scripts/voicectl.py hook-stop`.

### Manifest Item Shape

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
  "sha256": "...",
  "bundled": true
}
```

### Validation

Before publishing changes:

```powershell
D:\python312\python.exe C:\Users\<you>\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py C:\Users\<you>\plugins\codex-voice-notifier-jk
```
