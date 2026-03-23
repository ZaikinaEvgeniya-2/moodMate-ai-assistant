# Worker Friendship System Design

## Overview

Workers form friendships when they coincidentally share non-workspace rooms (kitchen, hallway, meeting room). As friendship grows, workers actively follow friends to rooms, have AI-generated conversations, and spend more time hanging out. The Chef treats chatting friends the same as any slacker — everyone gets sent back to work.

## Data Model

### FriendshipManager (`src/friendship_manager.py`)

Central class owning all friendship state.

**Core data:**
```python
friendships: dict[tuple[str, str], int]  # (worker_id_a, worker_id_b) -> level 1-5
# Keys sorted alphabetically: ("alex-a1", "sarah-b2") so order doesn't matter
```

**Methods:**
- `get_level(worker_a, worker_b) -> int` — 0 if not friends
- `increase_friendship(worker_a, worker_b)` — +1, capped at 5
- `get_friends(worker_id) -> list[tuple[str, int]]` — all friends with levels
- `get_friends_in_room(worker_id, room, all_workers) -> list[Worker]` — friends in same room
- `save()` / `load()` — persist to `data/friendships.json`

**New worker status:** `"chatting"` added to `STATUS_TO_ROOM`. Unlike other statuses, `chatting` maps to the worker's current room dynamically (kitchen, hallway, or meeting_room — never workspace).

### Persistence

`data/friendships.json`:
```json
{
  "friendships": {
    "alex-a1|sarah-b2": 3,
    "alex-a1|bob-c3": 1
  }
}
```

Pipe-delimited key for JSON compatibility (tuples can't be JSON keys). Loaded on startup, saved on friendship changes.

### Friendship Levels

| Level | Name | Follow Chance | Chat Duration |
|-------|------|--------------|---------------|
| 1 | Acquaintances | 10% | ~15s |
| 2 | Buddies | 25% | ~22s |
| 3 | Good Friends | 40% | ~30s |
| 4 | Best Friends | 60% | ~37s |
| 5 | Inseparable | 80% | ~45s |

Friendships never decay. Once friends, forever friends.

## Friendship Growth (Co-location Detection)

MainWindow runs a **tick timer every 10 seconds** calling `FriendshipManager.tick()`:

1. Group all workers by `current_room`
2. Skip `workspace` — friendships only form in kitchen, hallway, meeting_room
3. For each pair in the same non-workspace room where both have a non-working status (`on_break`, `in_kitchen`, `wandering`, `making_excuses`, `chatting`):
   - Call `increase_friendship(worker_a, worker_b)` — +1, capped at 5
4. Save if any friendships changed

Two workers slacking in the kitchen simultaneously grow friendship by +1 per 10-second tick. Takes ~50 seconds of shared room time to reach max level.

## Follow-Friend Mechanic

When BehaviorEngine changes a worker's status to a slacking state (`on_break`, `in_kitchen`, `wandering`, `making_excuses`):

1. Query FriendshipManager for friends of that worker who are currently `idle` in workspace with no pending task
2. For each eligible friend, roll against friendship level chance (10%/25%/40%/60%/80%)
3. **Max 1 follower per event** — if multiple friends pass the roll, pick one randomly (weighted by level). Prevents the entire office emptying out.
4. The chosen follower changes status to match the destination room (e.g., `in_kitchen`) after a random 2-5 second delay
5. Workers who are `working`, have a pending task, or are already in a non-workspace room are never pulled away

## Friend Conversations (AI-Generated)

### Trigger
When the 10-second tick detects two friends co-located in a non-workspace room and neither is already `chatting`:

1. Set both workers' status to `"chatting"`
2. Fire one AI call to generate dialogue

### AI Call
- Uses AIEngine with a combined prompt incorporating both workers' personality prompts
- Asks for 3-4 lines of banter (short, token-efficient)
- Topics: office gossip, complaining about work, random fun based on their personalities

### Storage
Conversations saved to `data/conversations/{worker_a_id}_{worker_b_id}.json`:
```json
{
  "conversations": [
    {
      "timestamp": "2026-03-23T14:30:00",
      "lines": [
        {"worker_id": "alex-a1", "text": "Did you see the new API spec?"},
        {"worker_id": "sarah-b2", "text": "Yeah, total chaos lol"},
        {"worker_id": "alex-a1", "text": "I need another coffee just thinking about it"},
        {"worker_id": "sarah-b2", "text": "Same, let's hide here a bit longer"}
      ]
    }
  ]
}
```

### Duration & Cooldown
- Chat duration based on friendship level (15s at Lv.1, 45s at Lv.5)
- After chat ends, both workers return to their previous slacking status; BehaviorEngine takes over normally
- **60-second cooldown** per pair after a conversation — prevents API spam
- **One conversation at a time per worker** — if Alex chats with Sarah, Bob can't start chatting with Alex until that conversation ends

## Chef Interaction

No special treatment. Chef catches slackers the same way:
- If Chef enters a room where friends are `chatting`, both get the "Sorry!" treatment
- Both get sent back to workspace
- Conversation is interrupted and saved as-is

## UI

### Grouped Friend Card (FriendGroupWidget)

When two friends are both `chatting` in the same room, their individual WorkerWidgets are replaced with a single `FriendGroupWidget`:

- Shared border with pink accent (`#e91e63`)
- Both worker emojis + names side by side with heart icon between them
- Latest conversation line shown as italic snippet
- Clickable "Read conversation" link in cyan (`#64ffda`)
- Friendship level badge (e.g., "Lv.3")

When conversation ends, they split back into individual WorkerWidgets.

### Friend Conversation Dialog (FriendChatDialog)

Opens when clicking FriendGroupWidget:

- Shows current conversation with lines attributed to each worker (emoji + name prefix)
- Read-only — user observes, doesn't participate
- History tab/section to browse past conversations between this pair
- Simple close button — no fire/task actions

### Worker Card Enhancement

When a worker has friends, their regular WorkerWidget shows a small indicator:
- Heart + count: e.g., "❤ 2 friends"
- Visible in all rooms, all statuses

## Files Changed/Created

### New files:
- `src/friendship_manager.py` — FriendshipManager class
- `src/friend_group_widget.py` — FriendGroupWidget for grouped display
- `src/friend_chat_dialog.py` — FriendChatDialog for viewing conversations

### Modified files:
- `src/worker.py` — add `"chatting"` status
- `src/office_view.py` — handle FriendGroupWidget creation/removal, friend indicator on WorkerWidget
- `src/worker_widget.py` — add friend count indicator
- `src/main.py` — wire up FriendshipManager, tick timer, follow-friend logic, conversation triggers
- `src/worker_manager.py` — save/load conversations
- `src/personality.py` — BehaviorEngine awareness of chatting status (don't override it)
