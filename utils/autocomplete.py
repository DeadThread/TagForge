import tkinter as tk
from tkinter import ttk

class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self._completion_list = []
        self._hits = []
        self._hit_index = 0
        self._ignore_autocomplete = False

        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._reset_state)

    def set_completion_list(self, completion_list):
        """Set list of possible completions."""
        self._completion_list = sorted(completion_list, key=str.lower)
        self['values'] = self._completion_list

    def _on_keyrelease(self, event):
        if self._ignore_autocomplete:
            return

        if event.keysym in ("Left", "Right", "Escape", "Return", "Tab", "Up", "Down"):
            # Don't autocomplete on these keys
            return

        text = self.get()

        if text == "":
            self._hit_index = 0
            self['values'] = self._completion_list
            return

        self._hits = [item for item in self._completion_list if item.lower().startswith(text.lower())]

        if self._hits:
            first_hit = self._hits[0]

            # Only do inline autocomplete insertion if key is not BackSpace or Delete
            if event.keysym not in ("BackSpace", "Delete") and first_hit.lower() != text.lower():
                self._ignore_autocomplete = True
                self.delete(0, tk.END)
                self.insert(0, first_hit)
                self.select_range(len(text), tk.END)
                self.icursor(len(text))
                self._ignore_autocomplete = False

            self['values'] = self._hits
        else:
            self['values'] = ()



    def _reset_state(self, event=None):
        self._hit_index = 0
        self._hits = []
        self._ignore_autocomplete = False

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("300x100")

    fruits = ['Apple', 'Apricot', 'Avocado', 'Banana', 'Blackberry', 'Blueberry', 'Cherry', 'Date', 'Fig', 'Grape']

    combo = AutocompleteCombobox(root)
    combo.set_completion_list(fruits)
    combo.pack(padx=10, pady=10, fill='x')
    combo.focus_set()

    root.mainloop()
