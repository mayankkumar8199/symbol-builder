import os
import re
import glob
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont

# ---------- Default symbols dir resolver ----------
def compute_default_symbols_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.getenv("SYMBOLS_DIR"),  # optional override
        os.path.join(here, "extracted_symbols"),  # next to script (recommended)
        r"C:\Users\mayan\symbol-builder\extracted_symbols",  # your earlier path
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    # If nothing exists, create the script-local folder so the app starts without prompts
    path = os.path.join(here, "extracted_symbols")
    os.makedirs(path, exist_ok=True)
    return path

DEFAULT_SYMBOLS_DIR = compute_default_symbols_dir()

PALETTE_WIDTH = 340
RIGHT_PANEL_WIDTH = 380
CANVAS_SIZE = (1100, 720)
THUMB_SIZE = (96, 96)
BG = "#f6f7fb"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

SPECIAL_TEXT_TOKEN = "::TEXT_UNIT_CODE::"

# ---------- Helpers ----------
def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]

def filename_to_name(path: str) -> str:
    base = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"[_\-]+", " ", base).strip()

def list_symbol_files(folder: str):
    files = []
    for ext in ALLOWED_EXTS:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    return sorted(files, key=natural_key)

def safe_copy_to_folder(src_path: str, dest_folder: str) -> str:
    os.makedirs(dest_folder, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(src_path))
    ext = ext.lower()
    base = re.sub(r"[^\w\-]+", "_", name).strip("_") or "symbol"
    candidate = os.path.join(dest_folder, base + ext)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dest_folder, f"{base}_{i}{ext}")
        i += 1
    shutil.copy2(src_path, candidate)
    return candidate

def make_text_tool_icon(size=(THUMB_SIZE[0], THUMB_SIZE[1])) -> Image.Image:
    w, h = size
    im = Image.new("RGBA", (w, h), (245, 246, 250, 255))
    draw = ImageDraw.Draw(im)
    # rounded border
    draw.rounded_rectangle([(2, 2), (w-3, h-3)], radius=12, outline=(70, 120, 200, 255), width=2)
    # big 'Aa'
    try:
        # Try a nicer font if available; otherwise default
        font = ImageFont.truetype("arial.ttf", size=int(h*0.44))
    except Exception:
        font = ImageFont.load_default()
    text = "Aa"
    tw, th = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text(((w - tw)//2, (h - th)//2), text, fill=(20, 20, 20, 255), font=font)
    return im

# ---------- Palette ----------
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

        # ---- Synthetic "Text Box" tool at the top ----
        text_row = ttk.Frame(self.inner)
        text_row.pack(fill="x", padx=10, pady=6)

        text_icon = make_text_tool_icon()
        tk_text_icon = ImageTk.PhotoImage(text_icon)
        self._imgrefs["__text_tool__"] = tk_text_icon

        lbl_img = ttk.Label(text_row, image=tk_text_icon)
        lbl_img.grid(row=0, column=0, rowspan=2, sticky="w")

        lbl_txt = ttk.Label(text_row, text="Text Box (Unit Code)", wraplength=PALETTE_WIDTH-140, justify="left")
        lbl_txt.grid(row=0, column=1, sticky="w", padx=(10, 0))

        def begin_text(ev, n="Text Box (Unit Code)", p=SPECIAL_TEXT_TOKEN):
            self.on_start_drag(n, p, ev)

        lbl_img.bind("<Button-1>", begin_text)
        lbl_txt.bind("<Button-1>", begin_text)

        ttk.Separator(self.inner).pack(fill="x", padx=12, pady=(6, 10))

        # ---- Real image symbols from folder ----
        if not self.files:
            ttk.Label(self.inner, text="No images found.\nAdd PNG/JPG symbols to the folder.",
                      foreground="#666").pack(anchor="w", padx=12, pady=8)
            return

        for idx, path in enumerate(self.files, 1):
            row = ttk.Frame(self.inner)
            row.pack(fill="x", padx=10, pady=6)

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

            name = filename_to_name(path)
            lbl_txt = ttk.Label(row, text=f"{idx}. {name}", wraplength=PALETTE_WIDTH-140, justify="left")
            lbl_txt.grid(row=0, column=1, sticky="w", padx=(10, 0))

            def begin(ev, n=name, p=path):
                self.on_start_drag(n, p, ev)
            lbl_img.bind("<Button-1>", begin)
            lbl_txt.bind("<Button-1>", begin)

# ---------- Canvas ----------
class BoardCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.configure(bg="white", width=CANVAS_SIZE[0], height=CANVAS_SIZE[1])
        self.placed = {}        # id -> {kind: 'image'|'text', name, ...}
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
        # nudge
        self.bind_all("<Left>", lambda e: self.nudge(-5, 0))
        self.bind_all("<Right>", lambda e: self.nudge(5, 0))
        self.bind_all("<Up>", lambda e: self.nudge(0, -5))
        self.bind_all("<Down>", lambda e: self.nudge(0, 5))
        # context menu
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Edit Text…", command=lambda: self.edit_selected_text())
        self.menu.add_separator()
        self.menu.add_command(label="Duplicate", command=lambda: self.duplicate_selected())
        self.menu.add_command(label="Bring to Front", command=lambda: self._raise_selected())
        self.menu.add_command(label="Send to Back", command=lambda: self._lower_selected())
        self.menu.add_separator()
        self.menu.add_command(label="Delete", command=lambda: self._delete_selected())
        self.bind("<Button-3>", self._show_menu)

        # hint
        self.hint = self.create_text(
            CANVAS_SIZE[0]//2, CANVAS_SIZE[1]//2,
            text="Drag from palette → drop here",
            fill="#8b8b8b", font=("Segoe UI", 14, "italic")
        )

    # ---- placement ----
    def place_symbol(self, name, src, x, y, base_px=160):
        if src == SPECIAL_TEXT_TOKEN:
            # create a text item
            default_text = "UNIT"
            base_size = 18
            item = self.create_text(x, y, text=default_text, fill="#000000", font=("Segoe UI", base_size, "bold"))
            self.placed[item] = {
                "kind": "text",
                "name": name,
                "text": default_text,
                "font_family": "Segoe UI",
                "font_size_base": base_size,
                "scale": 1.0,
            }
            if self.hint:
                self.delete(self.hint)
                self.hint = None
            self._update_selection(item)
            self.event_generate("<<SymbolPlaced>>")
            return item

        # image symbol
        try:
            pil = Image.open(src).convert("RGBA")
        except Exception:
            pil = Image.new("RGBA", (base_px, int(base_px*0.7)), (0, 0, 0, 0))

        scale = min(1.0, base_px / max(1, max(pil.size)))
        w = max(1, int(pil.width * scale))
        h = max(1, int(pil.height * scale))
        tkimg = ImageTk.PhotoImage(pil.resize((w, h), Image.LANCZOS))

        cid = self.create_image(x, y, image=tkimg)
        self.placed[cid] = {"kind": "image", "name": name, "path": src, "pil": pil, "scale": scale, "tk": tkimg}
        if self.hint:
            self.delete(self.hint)
            self.hint = None

        self._update_selection(cid)
        self.event_generate("<<SymbolPlaced>>")
        return cid

    # ---- selection & move ----
    def _on_click(self, ev):
        hit = self.find_closest(ev.x, ev.y)
        if hit and self.type(hit) in ("image", "text"):
            if self.selected_id == hit[0]:
                self._drag["item"] = hit
                self._drag["x"], self._drag["y"] = ev.x, ev.y
            else:
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

    def _bbox_for_item(self, item_id):
        bbox = self.bbox(item_id)  # (x0, y0, x1, y1)
        return bbox

    def _update_selection(self, cid_or_none):
        for it in self.find_withtag("selbox"):
            self.delete(it)
        self.selected_id = cid_or_none
        if cid_or_none:
            bbox = self._bbox_for_item(cid_or_none)
            if bbox:
                x0, y0, x1, y1 = bbox
                box = self.create_rectangle(x0, y0, x1, y1, dash=(3, 2),
                                            outline="#4A90E2", tags=("selbox",))
                self.tag_lower(box)
        self.event_generate("<<SelectionChanged>>")

    # ---- delete / clear ----
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
            self.event_generate("<<SelectionChanged>>")

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
        self.event_generate("<<SelectionChanged>>")

    # ---- resize (images & text) ----
    def resize_selected(self, factor):
        cid = self.selected_id
        if not cid or cid not in self.placed:
            return
        rec = self.placed[cid]
        rec["scale"] = max(0.2, min(4.0, rec.get("scale", 1.0) * factor))
        self._apply_scale(cid, rec)

    def set_selected_scale_abs(self, scale_abs):
        cid = self.selected_id
        if not cid or cid not in self.placed:
            return
        rec = self.placed[cid]
        rec["scale"] = max(0.2, min(4.0, scale_abs))
        self._apply_scale(cid, rec)

    def get_selected_scale(self):
        cid = self.selected_id
        if not cid or cid not in self.placed:
            return None
        return self.placed[cid].get("scale", 1.0)

    def _apply_scale(self, cid, rec):
        if rec["kind"] == "image":
            pil = rec["pil"]
            w = max(1, int(pil.width * rec["scale"]))
            h = max(1, int(pil.height * rec["scale"]))
            tkimg = ImageTk.PhotoImage(pil.resize((w, h), Image.LANCZOS))
            rec["tk"] = tkimg
            self.itemconfig(cid, image=tkimg)
        else:  # text
            base = rec.get("font_size_base", 18)
            size = max(8, int(base * rec["scale"]))
            self.itemconfig(cid, font=(rec.get("font_family", "Segoe UI"), size, "bold"))
        self._update_selection(cid)

    def _wheel_resize(self, ev):
        if self.selected_id:
            self.resize_selected(1.15 if ev.delta > 0 else 1/1.15)

    # ---- duplicate / arrange ----
    def duplicate_selected(self):
        cid = self.selected_id
        if not cid or cid not in self.placed:
            return
        rec = self.placed[cid]
        x, y = self.coords(cid)

        if rec["kind"] == "image":
            nid = self.place_symbol(rec["name"], rec["path"], x + 25, y + 25, base_px=max(rec["pil"].size))
            self.placed[nid]["scale"] = rec["scale"]
            self._apply_scale(nid, self.placed[nid])
        else:
            nid = self.place_symbol(rec["name"], SPECIAL_TEXT_TOKEN, x + 25, y + 25)
            self.placed[nid]["text"] = rec["text"]
            self.itemconfig(nid, text=rec["text"])
            self.placed[nid]["font_family"] = rec.get("font_family", "Segoe UI")
            self.placed[nid]["font_size_base"] = rec.get("font_size_base", 18)
            self.placed[nid]["scale"] = rec["scale"]
            self._apply_scale(nid, self.placed[nid])

    def _raise_selected(self):
        if self.selected_id:
            self.tag_raise(self.selected_id)

    def _lower_selected(self):
        if self.selected_id:
            self.tag_lower(self.selected_id)

    def nudge(self, dx, dy):
        if self.selected_id:
            self.move(self.selected_id, dx, dy)
            self.event_generate("<<SymbolMoved>>")

    # ---- context menu ----
    def _show_menu(self, ev):
        hit = self.find_closest(ev.x, ev.y)
        if hit and self.type(hit) in ("image", "text"):
            self._update_selection(hit[0])
            # Enable/disable Edit Text depending on kind
            if self.placed.get(self.selected_id, {}).get("kind") == "text":
                self.menu.entryconfig("Edit Text…", state="normal")
            else:
                self.menu.entryconfig("Edit Text…", state="disabled")
            try:
                self.menu.tk_popup(ev.x_root, ev.y_root)
            finally:
                self.menu.grab_release()

    # ---- text editing API ----
    def edit_selected_text(self, new_text=None):
        if not self.selected_id or self.selected_id not in self.placed:
            return
        rec = self.placed[self.selected_id]
        if rec["kind"] != "text":
            return
        if new_text is None:
            # pop a small dialog
            top = tk.Toplevel(self); top.title("Edit Text"); top.grab_set()
            tk.Label(top, text="Unit code:").pack(anchor="w", padx=10, pady=(10,2))
            ent = ttk.Entry(top); ent.insert(0, rec.get("text","UNIT")); ent.pack(fill="x", padx=10)
            def ok():
                txt = ent.get().strip()
                self._apply_text_change(self.selected_id, txt or "UNIT")
                top.destroy()
            ttk.Button(top, text="Apply", command=ok).pack(pady=8)
            ent.focus_set()
        else:
            self._apply_text_change(self.selected_id, new_text)

    def _apply_text_change(self, item_id, text):
        rec = self.placed[item_id]
        rec["text"] = text
        self.itemconfig(item_id, text=text)
        self._update_selection(item_id)
        self.event_generate("<<SymbolMoved>>")  # refresh inspector list bbox

# ---------- Drag ghost ----------
class DragGhost:
    def __init__(self, root, name, src, on_drop):
        self.root, self.name, self.src, self.on_drop = root, name, src, on_drop
        self.top = tk.Toplevel(root); self.top.overrideredirect(True)
        self.top.attributes("-alpha", 0.85); self.top.attributes("-topmost", True)

        if src == SPECIAL_TEXT_TOKEN:
            im = make_text_tool_icon((120, 120))
            self.tkimg = ImageTk.PhotoImage(im)
        else:
            try:
                im = Image.open(src).convert("RGBA"); im.thumbnail((120, 120), Image.LANCZOS)
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
            self.on_drop(widget, self.name, self.src, x, y)

    def _cleanup(self):
        try:
            self.root.unbind_all("<Motion>", self.cid_move)
            self.root.unbind_all("<ButtonRelease-1>", self.cid_up)
        except Exception:
            pass
        self.top.destroy()

# ---------- Inspector ----------
class Inspector(ttk.Frame):
    def __init__(self, master, board, **kw):
        super().__init__(master, **kw)
        self.board = board
        self._suspend_slider_cb = False  # prevents feedback loops

        ttk.Label(self, text="Inspector", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Separator(self).pack(fill="x", padx=10)

        # list of placed items
        self.txt = tk.Text(self, height=10, wrap="word")
        self.txt.pack(fill="both", expand=False, padx=10, pady=10)

        # ---- Selected controls ----
        ttk.Label(self, text="Selected Symbol Controls", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10)
        ctr = ttk.Frame(self); ctr.pack(fill="x", padx=10, pady=(6,10))

        self.sel_name = ttk.Label(ctr, text="(none selected)")
        self.sel_name.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0,6))

        ttk.Label(ctr, text="Size (%):").grid(row=1, column=0, sticky="w")

        # Create slider first WITHOUT command to avoid early callback
        self.scale_slider = ttk.Scale(ctr, from_=20, to=400, orient="horizontal", length=200)
        self.scale_slider.set(100)
        self.scale_slider.grid(row=1, column=1, sticky="we", padx=6)
        ctr.columnconfigure(1, weight=1)

        # Create lbl_scale BEFORE attaching the slider command
        self.lbl_scale = ttk.Label(ctr, width=5, text="100")
        self.lbl_scale.grid(row=1, column=2, sticky="e")

        # Now attach the callback
        self.scale_slider.configure(command=self._on_slider)

        ttk.Button(ctr, text="Dup", width=5, command=self._dup).grid(row=1, column=3, sticky="e")

        # ---- Text editor ----
        self.text_frame = ttk.LabelFrame(self, text="Unit Code (Text Box)")
        self.text_frame.pack(fill="x", padx=10, pady=(0,10))

        row2 = ttk.Frame(self.text_frame); row2.pack(fill="x", padx=8, pady=8)
        ttk.Label(row2, text="Text:").pack(side="left")

        self.text_var = tk.StringVar(value="")
        self.text_entry = ttk.Entry(row2, textvariable=self.text_var)
        self.text_entry.pack(side="left", padx=6, fill="x", expand=True)
        self.text_entry.bind("<Return>", lambda e: self._apply_text_entry())

        self.apply_btn = ttk.Button(row2, text="Apply", command=self._apply_text_entry)
        self.apply_btn.pack(side="left", padx=4)

        # events
        for ev in ("<<SymbolPlaced>>", "<<SymbolMoved>>", "<<SymbolRemoved>>", "<<SelectionChanged>>"):
            self.board.bind(ev, self.refresh)
        self.refresh()

    # enable/disable just text controls (LabelFrame has no 'state' option)
    def _set_text_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.text_entry.configure(state=state)
        self.apply_btn.configure(state=state)

    def _dup(self):
        self.board.duplicate_selected()

    def _apply_text_entry(self):
        txt = (self.text_var.get() or "").strip() or "UNIT"
        self.board.edit_selected_text(txt)

    def _on_slider(self, _val):
        # guard callback when programmatically setting slider
        if self._suspend_slider_cb or not hasattr(self, "lbl_scale"):
            return
        try:
            val = float(self.scale_slider.get())
        except tk.TclError:
            return
        self.lbl_scale.configure(text=str(int(val)))
        if self.board.selected_id:
            self.board.set_selected_scale_abs(val/100.0)

    def refresh(self, ev=None):
        # list placed
        self.txt.delete("1.0", "end")
        self.txt.insert("end", "Placed symbols:\n\n")
        for i, cid in enumerate(self.board.placed.keys(), 1):
            x, y = self.board.coords(cid)
            rec = self.board.placed[cid]
            label = rec["name"] if rec["kind"] == "image" else f'{rec["name"]}: "{rec.get("text","")}"'
            self.txt.insert("end", f"{i}. {label} @ ({int(x)}, {int(y)})\n")

        # selection panel
        rec = self.board.placed.get(self.board.selected_id)
        if rec:
            if rec["kind"] == "image":
                self.sel_name.configure(text=rec["name"])
                self._set_text_controls_enabled(False)
            else:
                self.sel_name.configure(text=f'{rec["name"]} (text)')
                self.text_var.set(rec.get("text", "UNIT"))
                self._set_text_controls_enabled(True)

            # sync slider safely
            self._suspend_slider_cb = True
            try:
                scale_pct = int(rec.get("scale", 1.0) * 100)
                self.scale_slider.set(scale_pct)
                self.lbl_scale.configure(text=str(scale_pct))
            finally:
                self._suspend_slider_cb = False
        else:
            self.sel_name.configure(text="(none selected)")
            self._suspend_slider_cb = True
            try:
                self.scale_slider.set(100)
                self.lbl_scale.configure(text="100")
            finally:
                self._suspend_slider_cb = False
            self.text_var.set("")
            self._set_text_controls_enabled(False)
# ---------- App ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Symbol Builder (with Text Box / Unit Code)")
        self.configure(bg=BG)
        self.geometry(f"{PALETTE_WIDTH+CANVAS_SIZE[0]+RIGHT_PANEL_WIDTH}x{CANVAS_SIZE[1]+90}")

        self._build_toolbar()

        left = ttk.Frame(self, width=PALETTE_WIDTH)
        center = ttk.Frame(self)
        right = ttk.Frame(self, width=RIGHT_PANEL_WIDTH)
        left.pack(side="left", fill="y")
        center.pack(side="left", fill="both", expand=True)
        right.pack(side="right", fill="y")

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

        self.board = BoardCanvas(center)
        self.board.pack(fill="both", expand=True, padx=8, pady=8)
        self.board.focus_set()

        self.inspector = Inspector(right, self.board)
        self.inspector.pack(fill="both", expand=True, padx=6, pady=6)

        self.status = ttk.Label(self, text=f"Folder: {self.current_folder}")
        self.status.pack(fill="x", side="bottom")

    def _build_toolbar(self):
        tb = ttk.Frame(self)
        ttk.Button(tb, text="Choose Folder…", command=self._choose_folder).pack(side="left", padx=4, pady=6)
        ttk.Button(tb, text="Reload", command=self._reload).pack(side="left", padx=4)
        ttk.Button(tb, text="Upload Symbol(s)…", command=self._upload_symbols).pack(side="left", padx=4)
        ttk.Button(tb, text="Delete Selected", command=lambda: self.board._delete_selected()).pack(side="left", padx=4)
        ttk.Button(tb, text="Clear Board", command=self._clear_board).pack(side="left", padx=4)
        ttk.Button(tb, text="Exit", command=self.destroy).pack(side="right", padx=4)
        tb.pack(fill="x")

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="Select symbols folder", initialdir=getattr(self, "current_folder", None))
        if not folder: return
        self.current_folder = folder
        self.palette.load_folder(folder)
        self.status.configure(text=f"Folder: {self.current_folder}")

    def _reload(self):
        if not hasattr(self, "current_folder"):
            self._choose_folder(); return
        self.palette.load_folder(self.current_folder)
        self.status.configure(text=f"Reloaded: {self.current_folder}")

    def _upload_symbols(self):
        if not hasattr(self, "current_folder"):
            self._choose_folder()
            if not hasattr(self, "current_folder"):
                return
        paths = filedialog.askopenfilenames(
            title="Select image files to add",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not paths: return
        copied = 0
        for p in paths:
            try:
                safe_copy_to_folder(p, self.current_folder)
                copied += 1
            except Exception as e:
                messagebox.showwarning("Copy failed", f"Could not add {os.path.basename(p)}:\n{e}")
        if copied:
            self.palette.load_folder(self.current_folder)
            self.status.configure(text=f"Uploaded {copied} file(s) → palette refreshed")

    def _clear_board(self):
        self.board.clear_board()

    def _on_palette_drag_start(self, name, src, event):
        DragGhost(self, name, src, on_drop=self._on_drop_to_canvas)

    def _on_drop_to_canvas(self, canvas: BoardCanvas, name, src, x, y):
        canvas.place_symbol(name, src, x, y)
        self.status.configure(text=f"Placed: {name}")

if __name__ == "__main__":
    App().mainloop()
