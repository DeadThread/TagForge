TagForge

TagForge is a powerful desktop application for managing and tagging music folders with flexible, customizable naming schemes. It features an intuitive Tkinter-based GUI, support for multiple audio formats, persistent UI settings, live logging, and a rich queue-based processing system.
Features:

- Tag audio folders with custom metadata: artist, venue, city, source, format, genre, date, and more

- Flexible folder naming and saving schemes with live preview and editable scheme expressions

- Persistent sash pane positions and window size across sessions

- Support for FLAC, MP3 (with EasyID3), and other formats via Mutagen
  
- Queue system for batch tagging multiple folders

- Live GUI logging with color-coded output and filtering

- Asset management for artists, venues, cities, and history caches

- Integrated audio player for previewing audio files inside the app

- Comprehensive config management via INI files

- Extensible and modular codebase with separate modules for processor, queue, cache, GUI, etc.

Installation

- Clone the repository:

  ```
  git clone https://github.com/deadthread/tagforge.git
  cd tagforge
  ```

Create and activate a Python virtual environment (recommended):
```
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate.bat      # Windows
```
Install required dependencies:

    pip install -r requirements.txt

- Dependencies include mutagen (for audio tagging), tkinter (should be included with Python), and other standard libraries.

- Ensure assets and themes folders exist:

- Assets and themes folders will be auto-created on startup, but you can verify or add custom themes in the themes/ directory.

Usage

- Run the main application:

- python TagForge.py

Main UI Overview

- Folder Tree: Browse and select music folders to tag
  
- Metadata Inputs: Enter artist, venue, city, source, format, genre, and date details

- Queue: Add folders to the processing queue for batch tagging

- Schemes: Edit folder and saving schemes to customize naming conventions

- Logging: View detailed logs with color highlighting

- Audio Player: Preview audio files within the app

Configuration

- Settings are stored in config/config.ini. This includes saved theme, folder and saving naming schemes, history of recent inputs, and used cache for artists and genres.

- You can manually edit this INI file or use the GUI scheme editor for live updates.

Customizing Naming Schemes

- TagForge uses a custom scheme language allowing placeholders like {artist}, {venue}, {date}, etc.

- Folder Scheme defines the folder name pattern

- Saving Scheme defines how files are named/saved

- Use the scheme editor in the app to create or modify schemes and preview their output live.

Development
Code Structure Highlights

- TagForge.py - main entry point with TkTagForge app class

- utils/ - backend utilities for processing, caching, queue management, logging, theme management, etc.

- gui/ - GUI components and widgets, sash persistence, scheme editor, tree selectors

- assets/ - asset files for artists, venues, cities, and icons

- themes/ - theme definitions

Logging

- GUI logs show in a text widget with color-coded tags

- Backend logs use Python’s logging module for console/file output

Contributing

Contributions and suggestions are welcome! Please:

- Fork the repo

- Create a feature branch

- Make changes with clear commit messages

- Submit a pull request

License

- This project is licensed under the MIT License — see the LICENSE file for details.
Contact

- Created and maintained by [DeadThread]. Feel free to open issues or contact via GitHub.
Acknowledgments

- Thanks to the open source libraries used: Mutagen, Tkinter, and Python standard libraries.

Troubleshooting

- Ensure Python 3.7+ is installed

- Make sure mutagen is installed (pip install mutagen)

- Confirm assets and themes folders exist and contain required files

- Report bugs on GitHub Issues with logs if possible
