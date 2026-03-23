# AI Office Simulator — Design Spec

## Overview

A Linux desktop game/simulation where you manage a virtual office of AI workers. Each worker has a unique AI-generated personality. You hire workers by setting a salary, and the salary tier determines their work ethic — highly-paid workers are dedicated professionals, while cheap workers slack off, drink tea, make excuses, and need constant nagging. Workers perform real tasks via Claude CLI in isolated directories.

## Core Concepts

### Purpose
Game/simulation first. The entertainment value of watching AI workers with personalities slack off or work hard is the core experience. Real task output (via Claude CLI) is a bonus.

### Salary Tiers

| Salary     | Tier     | Task Completion | Behavior                                                                  |
|------------|----------|-----------------|---------------------------------------------------------------------------|
| $1000+     | Star     | 90-100%         | Works immediately, stays at desk, polite and professional in chat         |
| $500-999   | Decent   | 60-80%          | Occasional short breaks, mostly works, might grumble                      |
| $200-499   | Mediocre | 30-50%          | Frequent breaks, partial work, needs reminders, slow responses            |
| $0-199     | Lazy     | 0-20%           | Kitchen trips, excuses, wandering, ignores tasks, must nag repeatedly     |

### Worker Statuses

`idle` → `received_task` → `working` / `on_break` / `in_kitchen` / `wandering` / `making_excuses` → `done` / `partially_done`

### Room Assignment

- `working`, `received_task`, `idle` → Workspace
- `on_break`, `in_kitchen` → Kitchen
- `wandering`, `making_excuses` → Hallway
- (Future: Meeting Room for multi-worker tasks)

## Architecture

### Tech Stack

- **Language:** Python 3
- **GUI:** PyQt6 (pure, no web views)
- **AI Backend:** Claude CLI spawned as QProcess subprocesses
- **Persistence:** JSON files

### File Structure

```
src/
  main.py              — App entry point, main window setup
  office_view.py       — Office floor plan widget (rooms + worker cards)
  worker.py            — Worker data model (personality, salary, status)
  worker_widget.py     — Visual worker representation in rooms
  chat_dialog.py       — Popup modal for worker details + chat
  hire_dialog.py       — Hiring flow dialog (role, salary, description)
  ai_engine.py         — Claude CLI subprocess manager (QProcess)
  personality.py       — Personality generation + behavior rules
  worker_manager.py    — Manages all workers, state persistence
data/
  office.json          — Worker list with personality, salary, status
  workers/
    {worker_name}/     — Per-worker isolated working directory
  chat_history/
    {worker_name}.json — Chat log per worker
```

### Key Components

**MainWindow** — Top-level window. Contains the OfficeView widget and a toolbar with the "Hire Worker" button and a total salary label (sum of all workers' monthly salaries — display only, no accounting logic).

**OfficeView** — Widget divided into 4 rooms: Workspace, Kitchen, Meeting Room, Hallway. Each room is a container widget that holds WorkerWidget instances. Workers move between rooms by being reparented to a different room container based on their current status.

**Worker** — Data model holding: id, name, emoji avatar, role, salary, tier, personality_prompt (full system prompt for Claude CLI), traits (list of 3), catchphrase, favorite_excuse, status, current_room, task_queue.

**WorkerWidget** — Visual card for a worker shown inside a room. Displays emoji, name, status indicator (colored dot), and current activity text. Clickable — opens ChatDialog.

**ChatDialog** — Modal popup. Shows worker avatar, name, role, salary, personality traits as badges, current status. Contains scrollable chat history and text input. Sending a message triggers task execution via AIEngine.

**HireDialog** — Modal popup with: role dropdown (Developer, Writer, Designer, Tester, DevOps, Other), salary slider ($0-$2000 with live tier label), optional description text field, "Generate" button that calls Claude CLI to create personality, preview of generated worker, "Hire" / "Try Again" buttons.

**AIEngine** — Manages Claude CLI subprocesses. Each task spawns a new `claude` invocation via QProcess:
```
claude --print --system-prompt "{personality_prompt}" \
       --working-dir data/workers/{worker_name}/ \
       "{task_message}"
```
Personality prompt controls the worker's tone, effort level, and behavior. For lazy workers, the prompt instructs Claude to produce minimal/incomplete output.

**WorkerManager** — Creates, stores, removes workers. Loads/saves `office.json`. Assigns status transitions and room changes based on salary tier behavior rules. Manages timers for breaks and delays.

## Personality System

### Generation

When hiring, Claude CLI generates a personality from this prompt:
> "Generate a worker personality for a {role} with salary ${salary}. Include: name, emoji avatar, 3 personality traits, work style, favorite excuse for not working, catchphrase. Return as JSON."

The generated personality becomes the system prompt for all future Claude CLI calls for that worker.

### Behavior Examples

**Star ($1200, Developer):**
- Receives task → status: `working` → stays in Workspace
- Chat: "On it, boss! Looking at auth.py now..."
- Actually works on files → reports result
- Chat: "Done! Fixed the null check on line 23 and added input validation."

**Mediocre ($400, Writer):**
- Receives task → brief pause → status: `working`
- Chat: "Yeah I looked at it... I changed something, not sure if it works."
- Produces partial output

**Lazy ($100, Developer):**
- Receives task → "Hmm interesting... but first I need tea" → moves to Kitchen
- Timer: 30-60 seconds in Kitchen
- Returns → "What was the task again?"
- User repeats → "Ok ok..." → does maybe 20% of the task
- Chat: "auth.py? Never heard of it. My keyboard is sticky."

### Status Transition Rules

Lazy workers (tier $0-199):
1. `received_task` → 70% chance moves to Kitchen (`in_kitchen`), 30% stays and complains (`making_excuses`)
2. After Kitchen timer (30-60s) → `wandering` in Hallway OR back to Workspace
3. If nagged in chat → small chance of doing partial work
4. May cycle through Kitchen/Hallway multiple times before producing any output

Decent workers (tier $500-999):
1. `received_task` → `working` in Workspace
2. After 2-3 task interactions → 30% chance of short break (`on_break` in Kitchen, 15-20s)
3. Returns to Workspace, continues working
4. Mostly completes tasks with occasional grumbling

Mediocre workers (tier $200-499):
1. `received_task` → 40% chance short delay before starting, 60% starts working
2. Frequent breaks — every 1-2 interactions, 50% chance moves to Kitchen (20-30s)
3. If nagged → resumes with complaints, does partial work
4. Produces 30-50% of what was asked

Star workers (tier $1000+):
1. `received_task` → immediately `working` in Workspace
2. Stays in Workspace until task complete
3. Reports result in chat

## UI Design

### Office Floor Plan Layout

Room-based grid layout:

```
┌────────────────────────┬──────────────┐
│   💻 Workspace          │  ☕ Kitchen   │
│                        │              │
│  [Worker] [Worker]     │  [Worker]    │
│  [Worker]              │              │
├────────────────────────┼──────────────┤
│   🗣️ Meeting Room       │  🚶 Hallway  │
│                        │              │
│   (empty)              │  [Worker]    │
│                        │              │
└────────────────────────┴──────────────┘
 Status bar: ● 2 working  ● 1 on break  ● 1 slacking  [+ Hire Worker]
```

Each room has a colored header, workers appear as cards inside their current room. Bottom status bar shows aggregate counts and the Hire button.

### Worker Card (in room)

```
┌─────────────────────┐
│  👨‍💻  Alex            │
│  ● Working hard      │  (green dot = working)
│  $1,200/mo           │
│  Task: Fix login bug │
└─────────────────────┘
```

### Chat Modal

```
┌──────────────────────────────────┐
│  👨‍💻 Alex — Developer             │
│  $1,200/mo  ⭐ Star               │
│  [hardworking] [detail-oriented] │
│  Status: ● Working               │
│──────────────────────────────────│
│  You: Fix the login bug          │
│  Alex: On it, boss! Looking at   │
│        auth.py now...            │
│  Alex: Found the issue. The null │
│        check was missing...      │
│  Alex: Done! Fixed it.           │
│──────────────────────────────────│
│  [Type a message...        ] [→] │
│                         [Fire 🔥]│
└──────────────────────────────────┘
```

### Hire Dialog

```
┌──────────────────────────────────┐
│  🏢 Hire New Worker               │
│──────────────────────────────────│
│  Role: [Developer        ▾]     │
│                                  │
│  Salary: ──●────── $500/mo       │
│  Tier: 💼 Decent                  │
│                                  │
│  Description (optional):         │
│  [Good at Python, loves cats   ] │
│                                  │
│  [Generate Personality]          │
│──────────────────────────────────│
│  Preview:                        │
│  🐱 Whiskers — Decent Developer   │
│  "Code is like yarn, I chase it" │
│  Traits: cat-lover, focused, shy │
│                                  │
│  [Try Again]        [Hire! ✓]   │
└──────────────────────────────────┘
```

## Data Persistence

### office.json

```json
{
  "workers": [
    {
      "id": "alex-001",
      "name": "Alex",
      "emoji": "👨‍💻",
      "role": "developer",
      "salary": 1200,
      "tier": "star",
      "personality_prompt": "You are Alex, a dedicated senior developer...",
      "traits": ["hardworking", "detail-oriented", "polite"],
      "catchphrase": "Consider it done!",
      "favorite_excuse": "N/A — Alex doesn't make excuses",
      "status": "idle",
      "current_room": "workspace"
    }
  ]
}
```

### Chat History (per worker)

```json
{
  "messages": [
    {"role": "user", "content": "Fix the login bug", "timestamp": "2026-03-23T10:00:00"},
    {"role": "worker", "content": "On it, boss!", "timestamp": "2026-03-23T10:00:02"}
  ]
}
```

## Firing Workers

Right-click on a worker card or click "Fire" button in chat modal. Confirmation dialog appears. On confirm: worker removed from office.json, their working directory and chat history deleted.

## Scope Boundaries

**In scope (v1):**
- Office view with 4 rooms
- Hire/fire workers
- Salary-based personality and behavior
- Chat with workers + real task execution via Claude CLI
- Per-worker isolated directories
- JSON persistence
- Status transitions and room movement

**Out of scope (future):**
- Worker-to-worker interaction
- Office upgrades / furniture
- Sound effects
- Multiple projects/offices
- Budget/money management system
- Worker skill progression over time
