# click-tool

A small Windows mouse auto-clicker with a Tkinter window.

## Run

1. Activate the virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

2. Start the app:

   ```bash
   python main.py
   ```

## Usage

- Enter the click interval in milliseconds.
- Click **Add by click**, then left-click anywhere on screen to add that position.
- Right-click or press Esc while capturing to cancel.
- Add multiple positions; they are clicked from top to bottom.
- Use **Up**, **Down**, **Remove**, and **Clear** to edit the position order.
- Click **Start** to begin clicking all saved positions in order.
- Click **Stop** or press Esc to stop immediately.

## Notes

- This version is Windows-only.
- The app uses the standard library only.
