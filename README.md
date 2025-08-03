[![TagForge Screenshots](https://i.imgur.com/N3YbUbn.png)](https://imgur.com/a/XOPU0n3)

TagForge is a desktop application designed to help users efficiently batch tag and rename audio files using customizable naming schemes. It provides a flexible GUI to manage metadata, apply schemes, and update autocomplete dropdowns based on user-maintained asset files.

Features

    Batch process entire folders of supported audio files (MP3, FLAC, etc.).

    Apply complex, user-defined naming schemes to file names and metadata tags.

    Live evaluation and preview of naming schemes using sample metadata.

    Autocomplete dropdown lists for artists, venues, cities, and other common metadata fields.

    Dropdown lists are automatically updated after each batch process based on updated asset files.

    Persistent UI layout, including window size and sash (splitter) positions.

    Support for light and dark themes.

    Configurable asset lists stored as simple text files.

    Detailed logging visible in the GUI and saved to file for troubleshooting.

Installation
Requirements

    Python 3.8+

    Mutagen (for audio metadata manipulation)

    Standard Python libraries including Tkinter

Steps

    Clone or download the repository.

    Create and activate a Python virtual environment (recommended):

python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

Install dependencies:

pip install -r requirements.txt

Run the application:

    python TagForge.py

Usage

    Open the application.

    Use the File → Open Folder menu to select the folder containing audio files.

    Configure the naming scheme in the Naming Scheme Editor tab, adjusting tokens and syntax to your preference.

    Use the Preview feature to see how the naming scheme will affect sample metadata.

    Adjust metadata fields manually or select values from autocomplete dropdowns populated from asset files.

    Click Process Folder to batch apply the naming scheme and update tags for all supported files in the folder.

    After processing, dropdowns refresh automatically to include any new entries found in the asset text files.

Configuration and Asset Files

    Asset lists (artists.txt, venues.txt, cities.txt, etc.) are stored in the assets/ directory as plain text files, one entry per line.

    These asset files populate the autocomplete dropdown menus.

    After processing files, TagForge re-reads the asset files to update dropdown lists accordingly.

    UI state (window size, splitter positions) is saved in a config file on exit and restored on startup.

    Themes are loaded from the themes/ folder, with support for light and dark modes.

Naming Scheme Editor

    Supports defining flexible naming schemes for file renaming and tagging using a token-based syntax.

    Includes live preview with sample metadata to verify the scheme before processing.

    Allows saving and loading presets (currently through config or internal presets).

User Interface

    Main window divided by adjustable sashes with persistent sizes.

    Dropdowns provide autocomplete for quick metadata entry.

    Logs window displays detailed process output and errors.

Logging

    Detailed log output is displayed live in the GUI console.

    Log files are saved locally for review.

    Logs include information on file processing, tagging steps, and errors.

Contributing

Contributions to fix bugs or improve the current functionality are welcome. Please:

    Fork the repository.

    Create a feature or bugfix branch.

    Follow PEP8 style guidelines.

    Submit a pull request with a clear description of changes.

License

TagForge is released under the MIT License. See LICENSE for details.
