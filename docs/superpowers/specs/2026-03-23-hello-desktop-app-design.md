# MoodMate Desktop App — Minimal "Hello" Window

## Overview

A minimal Linux desktop application that displays "Hello" in a window. This is the foundation for the future MoodMate AI assistant — starting with the simplest possible working desktop app.

## Tech Stack

- **Language:** Python 3
- **GUI Framework:** PyQt6 (Qt 6 bindings for Python)
- **Platform:** Linux (cross-platform capable)

## Requirements

- Opens a native desktop window titled "MoodMate"
- Displays "Hello" centered in the window
- Window has standard close button (X) that exits the app
- No other functionality

## Project Structure

```
moodMate-ai-assistant/
├── src/
│   └── main.py          # App entry point, creates window with "Hello" label
├── requirements.txt     # PyQt6 dependency
└── README.md            # Install and run instructions
```

## Dependencies

- `PyQt6` — Qt 6 Python bindings

## How to Run

```bash
pip install -r requirements.txt
python src/main.py
```

## Architecture

Single file (`src/main.py`) containing:

1. Create a `QApplication` instance
2. Create a `QMainWindow` with title "MoodMate"
3. Add a `QLabel` with text "Hello", centered
4. Set a reasonable default window size (400x300)
5. Show the window and start the event loop

## Testing

- Manual: run the app, verify "Hello" is displayed, close the window
- No automated tests needed for this phase

## Future

This window will serve as the shell for MoodMate features (mood tracking, AI chat, journaling) to be designed separately.
