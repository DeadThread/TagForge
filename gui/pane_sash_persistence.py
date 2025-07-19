def install_outer_pane_sash_persistence(self):
    """Persist sash position of self.outer_pane (vertical split with audio player) between runs."""

    def save_sash_pos(event=None):
        try:
            if not self.outer_pane.winfo_exists():
                return
            pos = self.outer_pane.sashpos(0)
            if not self.cfg.has_section("Panes"):
                self.cfg.add_section("Panes")
            self.cfg.set("Panes", "outer", str(pos))
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            self.log_message(f"Saved sash position for outer pane: {pos}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to save outer pane sash position: {e}", level="error")

    def restore_sash_pos():
        try:
            if not self.outer_pane.winfo_exists():
                return
            pos = self.cfg.getint("Panes", "outer", fallback=None)
            if pos is not None:
                self.outer_pane.update_idletasks()
                self.outer_pane.sashpos(0, pos)
                self.outer_pane.update()
                self.log_message(f"Restored sash position for outer pane: {pos}", level="debug")
            else:
                # Default: set sash pos so audio player is 240 px tall
                total_height = self.root.winfo_height()
                if total_height > 300:
                    self.outer_pane.sashpos(0, total_height - 240)
                    self.log_message(f"Set default outer pane sash pos: {total_height - 240}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to restore outer pane sash position: {e}", level="error")

    self.root.after(150, restore_sash_pos)
    self.outer_pane.bind("<B1-Motion>", save_sash_pos, add="+")
    self.outer_pane.bind("<ButtonRelease-1>", save_sash_pos, add="+")


def install_main_pane_sash_persistence(self):
    """Persist sash position of self.paned_main between runs."""

    def save_sash_pos(event=None):
        try:
            if not self.paned_main.winfo_exists():
                return
            pos = self.paned_main.sashpos(0)
            if not self.cfg.has_section("Panes"):
                self.cfg.add_section("Panes")
            self.cfg.set("Panes", "main", str(pos))
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            self.log_message(f"Saved sash position for main: {pos}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to save sash position: {e}", level="error")

    def restore_sash_pos():
        try:
            if not self.paned_main.winfo_exists():
                return
            pos = self.cfg.getint("Panes", "main", fallback=None)
            if pos is not None:
                self.paned_main.update_idletasks()
                self.paned_main.sashpos(0, pos)
                self.paned_main.update()
                self.log_message(f"Restored sash position for main: {pos}", level="debug")
            else:
                self.log_message("No saved sash position for main found in config", level="debug")
        except Exception as e:
            self.log_message(f"Failed to restore sash position: {e}", level="error")

    self.root.after(150, restore_sash_pos)
    self.paned_main.bind("<B1-Motion>", save_sash_pos, add="+")
    self.paned_main.bind("<ButtonRelease-1>", save_sash_pos, add="+")


def install_left_paned_sash_persistence(self):
    """Persist sash position of self.left_paned (vertical split between folder tree and queue) between runs."""

    def save_sash_pos(event=None):
        try:
            if not self.left_paned.winfo_exists():
                return
            pos = self.left_paned.sashpos(0)
            if not self.cfg.has_section("Panes"):
                self.cfg.add_section("Panes")
            self.cfg.set("Panes", "left_paned", str(pos))
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            self.log_message(f"Saved sash position for left_paned: {pos}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to save sash position for left_paned: {e}", level="error")

    def restore_sash_pos():
        try:
            if not self.left_paned.winfo_exists():
                return
            pos = self.cfg.getint("Panes", "left_paned", fallback=None)
            if pos is not None:
                self.left_paned.update_idletasks()
                self.left_paned.sashpos(0, pos)
                self.left_paned.update()
                self.log_message(f"Restored sash position for left_paned: {pos}", level="debug")
            else:
                self.log_message("No saved sash position for left_paned found in config", level="debug")
        except Exception as e:
            self.log_message(f"Failed to restore sash position for left_paned: {e}", level="error")

    self.root.after(150, restore_sash_pos)
    self.left_paned.bind("<B1-Motion>", save_sash_pos, add="+")
    self.left_paned.bind("<ButtonRelease-1>", save_sash_pos, add="+")


def install_main_window_size_persistence(self):
    """Persist the main window size and position between runs."""

    already_restored = {"done": False}
    last_geometry = {"value": None}

    def save_window_geometry(event=None):
        if not already_restored["done"]:
            return

        try:
            geometry = self.root.geometry()
            if geometry == last_geometry["value"]:
                # Geometry hasn't changed, skip saving
                return

            last_geometry["value"] = geometry

            width = self.root.winfo_width()
            height = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()

            if not self.cfg.has_section("Window"):
                self.cfg.add_section("Window")
            self.cfg.set("Window", "width", str(width))
            self.cfg.set("Window", "height", str(height))
            self.cfg.set("Window", "x", str(x))
            self.cfg.set("Window", "y", str(y))

            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cfg.write(f)

            self.log_message(f"Saved main window size and position: {geometry}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to save window size/position: {e}", level="error")

    def restore_window_geometry():
        try:
            width = self.cfg.getint("Window", "width", fallback=None)
            height = self.cfg.getint("Window", "height", fallback=None)
            x = self.cfg.getint("Window", "x", fallback=None)
            y = self.cfg.getint("Window", "y", fallback=None)

            if width and height:
                geometry = f"{width}x{height}"
                if x is not None and y is not None:
                    geometry += f"+{x}+{y}"
                self.root.geometry(geometry)
                self.log_message(f"Restored main window geometry: {geometry}", level="debug")
        except Exception as e:
            self.log_message(f"Failed to restore window size/position: {e}", level="error")
        finally:
            already_restored["done"] = True

    self.root.after(100, restore_window_geometry)
    self.root.bind("<Configure>", save_window_geometry, add="+")
