# MoodMate AI Assistant

A Linux desktop application built with Python and PyQt6.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Copy `.env.example` to `.env` and edit as needed:

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AI_PROVIDER` | `opencode`, `claude` | `opencode` | Which AI CLI backend to use |

- **opencode** — uses [opencode](https://github.com/opencode-ai/opencode) (`opencode run "prompt"`)
- **claude** — uses [Claude CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude --print "prompt"`)

## Run

```bash
python src/main.py
```
