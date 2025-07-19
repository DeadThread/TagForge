import tkinter as tk
from tkinter import ttk

class QueueManager:
    def __init__(self, treeview_widget: ttk.Treeview, log_widget: tk.Text | None = None):
        """
        Manage a folder queue with metadata, reflected in a ttk.Treeview with two columns.

        Args:
            treeview_widget: The ttk.Treeview used to display queued folders with two columns:
                             - first column: folder path display name
                             - second column: proposed folder name
            log_widget: Optional Tkinter Text widget for logging messages.
        """
        self.saved = []            # List of normalized folder paths in queue
        self.saved_meta = {}       # Dict mapping folder path -> metadata dict
        self.tree = treeview_widget
        self.log = log_widget
        self.evaluate_schemes_func = None  # Function to evaluate schemes

    def set_scheme_evaluator(self, evaluate_func):
        """
        Set the function used to evaluate schemes for generating proposed names.
        
        Args:
            evaluate_func: Function that takes metadata dict and returns proposed path
        """
        self.evaluate_schemes_func = evaluate_func

    def add(self, folder_path: str, proposed_name: str, metadata: dict):
        """
        Add a folder, its proposed folder name, and metadata to the queue and update UI.

        Args:
            folder_path: The original folder path string to queue.
            proposed_name: The proposed output folder name (string).
            metadata: Dictionary of metadata associated with the folder.
        """
        norm_path = self._normalize_path(folder_path)
        if not norm_path:
            return

        if norm_path not in self.saved:
            self.saved.append(norm_path)
            # Store metadata without the proposed_name since it can change
            self.saved_meta[norm_path] = metadata
            # Insert folder_path and proposed_name in correct order to match columns
            self.tree.insert("", "end", iid=norm_path, values=(norm_path, proposed_name))
            self._log(f"Queued folder: {norm_path} | Proposed Name: {proposed_name}")

    def remove_selected(self):
        """
        Remove currently selected folders from queue and UI.
        """
        selected_items = self.tree.selection()
        if not selected_items:
            return

        for iid in selected_items:
            self.tree.delete(iid)
            if iid in self.saved:
                self.saved.remove(iid)
                self.saved_meta.pop(iid, None)
            self._log(f"Removed from queue: {iid}")

    def remove_folder(self, folder_path: str):
        """
        Remove a folder by path from queue and UI.

        Args:
            folder_path: Folder path to remove.
        """
        norm_path = self._normalize_path(folder_path)
        if norm_path in self.saved:
            self.saved.remove(norm_path)
            self.saved_meta.pop(norm_path, None)
            self.tree.delete(norm_path)
            self._log(f"Removed from queue: {norm_path}")

    def clear(self):
        """
        Clear entire queue and UI.
        """
        self.saved.clear()
        self.saved_meta.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._log("Queue cleared.")

    def refresh_proposed_names(self):
        """
        Regenerate all proposed names using current schemes and update UI.
        This should be called whenever schemes are updated.
        """
        if not self.evaluate_schemes_func:
            return
            
        # Update each item in the queue
        for folder_path in self.saved:
            metadata = self.saved_meta.get(folder_path, {})
            try:
                # Generate new proposed name using current schemes
                new_proposed = self.evaluate_schemes_func(metadata)
                
                # Update the treeview item
                self.tree.item(folder_path, values=(folder_path, new_proposed))
                
                self._log(f"Updated queue item: {folder_path} | New Proposed Name: {new_proposed}")
                
            except Exception as e:
                self._log(f"Error updating proposed name for {folder_path}: {e}")

    def refresh_ui(self):
        """
        Refresh the Treeview UI to reflect current queue state.
        """
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for folder in self.saved:
            metadata = self.saved_meta.get(folder, {})
            proposed = ""
            
            # Try to generate current proposed name if evaluator is available
            if self.evaluate_schemes_func:
                try:
                    proposed = self.evaluate_schemes_func(metadata)
                except Exception as e:
                    self._log(f"Error generating proposed name for {folder}: {e}")
                    proposed = "Error generating name"
            
            self.tree.insert("", "end", iid=folder, values=(folder, proposed))

    def refresh_ui_threadsafe(self):
        """
        Refresh UI safely from any thread.
        """
        try:
            self.tree.after(0, self.refresh_ui)
        except Exception:
            pass

    def get_all_queued(self):
        """
        Return a list of all queued folder paths.
        """
        return list(self.saved)

    def get_metadata(self, folder_path: str):
        """
        Get metadata for a specific folder path.
        
        Args:
            folder_path: The folder path to get metadata for
            
        Returns:
            Dictionary of metadata, or empty dict if not found
        """
        norm_path = self._normalize_path(folder_path)
        return self.saved_meta.get(norm_path, {})

    def _normalize_path(self, path: str) -> str:
        """
        Normalize folder path slashes to forward slashes.

        Returns empty string if input invalid.
        """
        if not path:
            return ""
        return path.replace("\\", "/")

    def _log(self, msg: str):
        if self.log:
            try:
                self.log.insert(tk.END, msg + "\n")
                self.log.see(tk.END)
            except Exception:
                pass