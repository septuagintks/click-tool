# Click Tool

A flexible Windows mouse auto-clicker with visual draggable targets. Supports both screen-wide and window-specific clicking modes.

## Run

1. Activate the virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

2. Install dependencies (requires `pywin32`):

   ```bash
   pip install -r requirements.txt
   ```

3. Start the app:

   ```bash
   python main.py
   ```

## Features

### 1. Screen Mode (Original)
- **Global Coordinates**: Set click points anywhere on the screen.
- **Draggable Targets**: Visually position numbered dots.

### 2. Window Mode (New!)
- **Target Windows**: Select one or more specific windows to click within.
- **Background Clicking**: Uses Windows messages (`PostMessage`) to click windows even when they are not in the foreground.
- **Smart Constraints**: Draggable dots are locked within the window's client area and follow the window as it moves or resizes.
- **Cross-Window Sequencing**: Create a complex sequence of clicks spanning across different windows.

### General Features
- **Custom Delays**: Set unique wait times for each individual click point.
- **DPI Awareness**: Accurate positioning on high-resolution displays.
- **Emergency Stop**: Press **Esc** at any time to stop the clicking loop.

## Usage

1. **Choose Mode**: Use the tabs at the top to switch between **Screen Mode** and **Window Mode**.
2. **Add Targets**:
   - In **Screen Mode**, click "Add Dot".
   - In **Window Mode**, click "Add Window" to pick a target, then select it and click "Add Dot".
3. **Position Dots**: Drag the numbered dots to your desired locations. In Window Mode, dots will follow their respective windows.
4. **Configure Sequence**: Adjust the order using Up/Down buttons and set custom post-click delays if needed.
5. **Run**: Click **Start Loop**. Press **Esc** to stop.

## Dependencies
- `pydirectinput`: Used for Screen Mode hardware-level simulation.
- `pywin32`: Used for Window Mode background messaging and window management.
- `tkinter`: Standard GUI library.
