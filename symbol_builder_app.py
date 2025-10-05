import os
import re
import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# =======================
# Configuration
# =======================
# Change this default if you like; you can also switch folders at runtime.
DEFAULT_SYMBOLS_DIR = r"extracted_symbols"

PALETTE_WIDTH = 340
RIGHT_PANEL_WIDTH = 360
CANVAS_SIZE = (1100, 720)
THUMB_SIZE = (96, 96)
BG = "#f6f7fb"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# =======================
# Helpers
# =======================
def natural_key(s: str):
    """Natural sort key: splits 001_Infantry before 10_..."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def filename_to_name(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[_\-]+", " ", base).strip()

def list_symbol_files(folder: str):
    files = []
    for ext in ALLOWED_EXTS:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    files = sorted(files, key=natural_key)
    return files

# =======================
# Palette (left)
# =======================
class SymbolPalette(ttk.Frame):
    def __init__(self, master, on_start_drag, **kw):
        super().__init__(master, **kw)
        self.on_start_drag = on_start_drag

        self.canvas = tk.Canvas(self, width=PALETTE_WIDTH, bg=BG, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw", width=PALETTE_WIDTH)
        self.canvas.configure(yscrollcommand=self.sb.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.sb.pack(side="right", fill="y")

        self._imgrefs = {}
        self.folder = None
        self.files = []

    def load_folder(self, folder: str):
        self.folder = folder
        self.files = list_symbol_files(folder)
        for w in self.inner.winfo_children():
            w.destroy()

        title = ttk.Label(self.inner, text=f"Palette ({len(self.files)} symbols)", font=("Segoe UI", 12, "bold"))
        title.pack(anchor="w", padx=12, pady=(10, 6))
        ttk.Separator(self.inner).pack(fill="x", padx=12, pady=(0, 8))

        if not self.files:
            ttk.Label(self.inner, text="No images found.\nAdd PNG/JPG symbols to the folder.",
                      foreground="#666").pack(anchor="w", padx=12, pady=8)
            return

        for idx, path in enumerate(self.files, 1):
            row = ttk.Frame(self.inner)
            row.pack(fill="x", padx=10, pady=6)

            # thumbnail
            lbl_img = ttk.Label(row)
            lbl_img.grid(row=0, column=0, rowspan=2, sticky="w")

            try:
                im = Image.open(path).convert("RGBA")
                im.thumbnail(THUMB_SIZE, Image.LANCZOS)
                tkimg = ImageTk.PhotoImage(im)
            except Exception:
                im = Image.new("RGBA", THUMB_SIZE, (230, 230, 230, 255))
                tkimg = ImageTk.PhotoImage(im)

            self._imgrefs[path] = tkimg
            lbl_img.configure(image=tkimg)

            # label
            name = filename_to_name(path)
            lbl_txt = ttk.Label(row, text=f"{idx}. {name}", wraplength=PALETTE_WIDTH-140, justify="left")
            lbl_txt.grid(row=0, column=1, sticky="w", padx=(10, 0))

            # drag start
            def begin(ev, n=name, p=path):
                self.on_start_drag(n, p, ev)
            lbl_img.bind("<Button-1>", begin)
            lbl_txt.bind("<Button-1>", begin)

# =======================
# Canvas (center)
# =======================
class BoardCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.configure(bg="white", width=CANVAS_SIZE[0], height=CANVAS_SIZE[1])
        self.placed = {}        # id -> {name, path, pil, tk, scale}
        self.selected_id = None
        self._drag = {"item": None, "x": 0, "y": 0}

        # interactions
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind_all("<Delete>", self._delete_selected)
        self.bind_all("<plus>", lambda e: self.resize_selected(1.15))
        self.bind_all("<minus>", lambda e: self.resize_selected(1/1.15))
        self.bind_all("<KP_Add>", lambda e: self.resize_selected(1.15))
        self.bind_all("<KP_Subtract>", lambda e: self.resize_selected(1/1.15))
        self.bind_all("<Control-MouseWheel>", self._wheel_resize)

        # hint
        self.hint = self.create_text(
            CANVAS_SIZE[0]//2, CANVAS_SIZE[1]//2,
            text="Drag from palette → drop here",
            fill="#8b8b8b", font=("Segoe UI", 14, "italic")
        )

    def place_symbol(self, name, img_path, x, y, base_px=160):
        # load original (kept for re-scaling)
        pil = None
        try:
            pil = Image.open(img_path).convert("RGBA")
        except Exception:
            # fallback transparent rectangle
            pil = Image.new("RGBA", (base_px, int(base_px*0.7)), (0, 0, 0, 0))

        scale = min(1.0, base_px / max(1, max(pil.size)))
        w = max(1, int(pil.width * scale))
        h = max(1, int(pil.height * scale))
        tkimg = ImageTk.PhotoImage(pil.resize((w, h), Image.LANCZOS))

        cid = self.create_image(x, y, image=tkimg)
        self.placed[cid] = {"name": name, "path": img_path, "pil": pil, "scale": scale, "tk": tkimg}
        if self.hint:
            self.delete(self.hint)
            self.hint = None
        self._update_selection(cid)
        self.event_generate("<<SymbolPlaced>>")
        return cid

    # selection & move
    def _on_click(self, ev):
        hit = self.find_closest(ev.x, ev.y)
        if hit and self.type(hit) == "image":
            self._drag["item"] = hit
            self._drag["x"], self._drag["y"] = ev.x, ev.y
            self._update_selection(hit[0])
            return
        self._update_selection(None)

    def _on_drag(self, ev):
        if self._drag["item"]:
            dx, dy = ev.x - self._drag["x"], ev.y - self._drag["y"]
            self.move(self._drag["item"], dx, dy)
            self._drag["x"], self._drag["y"] = ev.x, ev.y
            self.event_generate("<<SymbolMoved>>")

    def _on_release(self, ev):
        self._drag["item"] = None

    # selection box
    def _update_selection(self, cid_or_none):
        for it in self.find_withtag("selbox"):
            self.delete(it)
        self.selected_id = cid_or_none
        if cid_or_none:
            x, y = self.coords(cid_or_none)
            rec = self.placed[cid_or_none]
            w, h = rec["tk"].width(), rec["tk"].height()
            box = self.create_rectangle(x-w/2, y-h/2, x+w/2, y+h/2,
                                        dash=(3, 2), outline="#4A90E2", tags=("selbox",))
            self.tag_lower(box)

    # delete / clear
    def _delete_selected(self, ev=None):
        if self.selected_id and self.selected_id in self.placed:
            self.delete(self.selected_id)
            del self.placed[self.selected_id]
            self.selected_id = None
            if not self.find_all() and not self.hint:
                self.hint = self.create_text(
                    CANVAS_SIZE[0]//2, CANVAS_SIZE[1]//2,
                    text="Drag from palette → drop here",
                    fill="#8b8b8b", font=("Segoe UI", 14, "italic")
                )
            self.event_generate("<<SymbolRemoved>>")

    def clear_board(self):
        for cid in list(self.placed.keys()):
            self.delete(cid)
        self.placed.clear()
        self.selected_id = None
        if not self.hint:
            self.hint = self.create_text(
                CANVAS_SIZE[0]//2, CANVAS_SIZE[1]//2,
                text="Drag from palette → drop here",
                fill="#8b8b8b", font=("Segoe UI", 14, "italic")
            )
        self.event_generate("<<SymbolRemoved>>")

    # resize
    def resize_selected(self, factor):
        cid = self.selected_id
        if not cid or cid not in self.placed:
            return
        rec = self.placed[cid]
        new_scale = max(0.2, min(4.0, rec["scale"] * factor))
        if abs(new_scale - rec["scale"]) < 1e-3:
            return
        rec["scale"] = new_scale
        w = max(1, int(rec["pil"].width * new_scale))
        h = max(1, int(rec["pil"].height * new_scale))
        tkimg = ImageTk.PhotoImage(rec["pil"].resize((w, h), Image.LANCZOS))
        rec["tk"] = tkimg
        self.itemconfig(cid, image=tkimg)
        self._update_selection(cid)

    def _wheel_resize(self, ev):
        if self.selected_id:
            self.resize_selected(1.15 if ev.delta > 0 else 1/1.15)

# =======================
# Drag ghost (palette DnD)
# =======================
class DragGhost:
    def __init__(self, root, name, img_path, on_drop):
        self.root, self.name, self.img_path, self.on_drop = root, name, img_path, on_drop
        self.top = tk.Toplevel(root); self.top.overrideredirect(True)
        self.top.attributes("-alpha", 0.85); self.top.attributes("-topmost", True)

        try:
            im = Image.open(img_path).convert("RGBA"); im.thumbnail((120, 120), Image.LANCZOS)
            self.tkimg = ImageTk.PhotoImage(im)
        except Exception:
            ph = Image.new("RGBA", (120, 90), (0, 0, 0, 0)); self.tkimg = ImageTk.PhotoImage(ph)

        ttk.Label(self.top, image=self.tkimg, padding=0).pack()
        self.cid_move = root.bind_all("<Motion>", self._follow)
        self.cid_up = root.bind_all("<ButtonRelease-1>", self._drop)

    def _follow(self, ev):
        self.top.geometry(f"+{ev.x_root+6}+{ev.y_root+6}")

    def _drop(self, ev):
        widget = self.root.winfo_containing(ev.x_root, ev.y_root)
        self._cleanup()
        if isinstance(widget, BoardCanvas):
            x = widget.canvasx(ev.x); y = widget.canvasy(ev.y)
            self.on_drop(widget, self.name, self.img_path, x, y)

    def _cleanup(self):
        try:
            self.root.unbind_all("<Motion>", self.cid_move)
            self.root.unbind_all("<ButtonRelease-1>", self.cid_up)
        except Exception:
            pass
        self.top.destroy()

# =======================
# Inspector (right)
# =======================
class Inspector(ttk.Frame):
    def __init__(self, master, board: BoardCanvas, **kw):
        super().__init__(master, **kw)
        self.board = board
        ttk.Label(self, text="Inspector", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Separator(self).pack(fill="x", padx=10)
        self.txt = tk.Text(self, height=12, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=10)
        for ev in ("<<SymbolPlaced>>", "<<SymbolMoved>>", "<<SymbolRemoved>>"):
            self.board.bind(ev, self.refresh)
        self.refresh()

    def refresh(self, ev=None):
        self.txt.delete("1.0", "end")
        self.txt.insert("end", "Placed symbols:\n\n")
        for i, cid in enumerate(self.board.placed.keys(), 1):
            x, y = self.board.coords(cid)
            name = self.board.placed[cid]["name"]
            self.txt.insert("end", f"{i}. {name} @ ({int(x)}, {int(y)})\n")

# =======================
# App
# =======================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Symbol Builder (folder-based)")
        self.configure(bg=BG)
        self.geometry(f"{PALETTE_WIDTH+CANVAS_SIZE[0]+RIGHT_PANEL_WIDTH}x{CANVAS_SIZE[1]+80}")

        # toolbar
        self._build_toolbar()

        # layout panes
        left = ttk.Frame(self, width=PALETTE_WIDTH)
        center = ttk.Frame(self)
        right = ttk.Frame(self, width=RIGHT_PANEL_WIDTH)
        left.pack(side="left", fill="y")
        center.pack(side="left", fill="both", expand=True)
        right.pack(side="right", fill="y")

        # palette
        self.palette = SymbolPalette(left, on_start_drag=self._on_palette_drag_start)
        self.palette.pack(fill="both", expand=True)

        folder = DEFAULT_SYMBOLS_DIR
        if not os.path.isdir(folder):
            folder = filedialog.askdirectory(title="Select symbols folder")
            if not folder:
                messagebox.showerror("No folder", "No folder selected. Exiting.")
                self.destroy()
                return
        self.current_folder = folder
        self.palette.load_folder(folder)

        # canvas
        self.board = BoardCanvas(center)
        self.board.pack(fill="both", expand=True, padx=8, pady=8)
        self.board.focus_set()

        # inspector
        self.inspector = Inspector(right, self.board)
        self.inspector.pack(fill="both", expand=True, padx=6, pady=6)

        # status
        self.status = ttk.Label(self, text=f"Folder: {self.current_folder}")
        self.status.pack(fill="x", side="bottom")

    # toolbar
    def _build_toolbar(self):
        tb = ttk.Frame(self)
        ttk.Button(tb, text="Choose Folder…", command=self._choose_folder).pack(side="left", padx=4, pady=6)
        ttk.Button(tb, text="Reload", command=self._reload).pack(side="left", padx=4)
        ttk.Button(tb, text="Clear Board", command=self._clear_board).pack(side="left", padx=4)
        ttk.Button(tb, text="Exit", command=self.destroy).pack(side="right", padx=4)
        tb.pack(fill="x")

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Select symbols folder", initialdir=self.current_folder if hasattr(self, "current_folder") else None)
        if not folder: return
        self.current_folder = folder
        self.palette.load_folder(folder)
        self.status.configure(text=f"Folder: {self.current_folder}")

    def _reload(self):
        if not hasattr(self, "current_folder"):
            self._choose_folder(); return
        self.palette.load_folder(self.current_folder)
        self.status.configure(text=f"Reloaded: {self.current_folder}")

    def _clear_board(self):
        self.board.clear_board()

    # palette drag
    def _on_palette_drag_start(self, name, img_path, event):
        DragGhost(self, name, img_path, on_drop=self._on_drop_to_canvas)

    def _on_drop_to_canvas(self, canvas: BoardCanvas, name, img_path, x, y):
        canvas.place_symbol(name, img_path, x, y)
        self.status.configure(text=f"Placed: {name}")

if __name__ == "__main__":
    App().mainloop()
