import os, json, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# ---------------------- CONFIG ----------------------
SYMS_DIR = os.path.abspath("./extracted_symbols")
THUMB = (86, 86)

STATUS_BADGE = {"Reinforced (Attached)": "+", "Reduced (Detached)": "−", "Reinforced and Reduced": "±"}

# canvas zones size
ZONE_FONT = ("Segoe UI", 12, "bold")

# ---------------------- Library ----------------------
class SymbolLibrary:
    def __init__(self, folder):
        self.folder = folder
        self.items = []
        self.by_type = {"ECHELON": [], "ROLE": [], "STATUS": [], "MOBILITY": [], "CAPABILITY": [], "AMPLIFIER": [], "GRAPHIC": []}
        self._load()

    def _load(self):
        self.items.clear()
        for k in self.by_type: self.by_type[k] = []
        manifest = os.path.join(self.folder, "symbols_manifest.json")
        if not os.path.exists(manifest):
            messagebox.showwarning("Missing manifest", f"symbols_manifest.json not found in {self.folder}\nRun prepare_symbols.py first.")
            return
        data = json.load(open(manifest, "r", encoding="utf-8"))
        for it in data.get("items", []):
            typ = it["type"].upper()
            name = it["name"]
            path = os.path.join(self.folder, it["path"])
            if not os.path.exists(path): 
                continue
            im = None
            try:
                img = Image.open(path).convert("RGBA")
                img.thumbnail(THUMB, Image.LANCZOS)
                im = ImageTk.PhotoImage(img)
            except Exception:
                im = None
            rec = {"type": typ, "name": name, "path": path, "thumb": im}
            self.items.append(rec)
            if typ in self.by_type:
                self.by_type[typ].append(rec)

# ---------------------- Drop zones ----------------------
class DropZone:
    def __init__(self, canvas, name, accept_types, box, hint):
        self.canvas = canvas
        self.name = name
        self.accept = set(accept_types)
        self.box = box  # (x0,y0,x1,y1)
        self.r = canvas.create_rectangle(*box, dash=(3,2), width=2, outline="#8fb0ff")
        self.hint = canvas.create_text((box[0]+box[2])//2, (box[1]+box[3])//2, text=hint, fill="#777", font=("Segoe UI", 10, "italic"))
        self.img_id = None
        self.txt_id = None
        self.assignment = None  # rec dict

    def inside(self, x, y):
        x0,y0,x1,y1 = self.box
        return x0<=x<=x1 and y0<=y<=y1

    def clear(self):
        if self.img_id: self.canvas.delete(self.img_id); self.img_id=None
        if self.txt_id: self.canvas.delete(self.txt_id); self.txt_id=None
        self.assignment = None
        self.canvas.itemconfigure(self.hint, state="normal")

    def set_value(self, rec):
        self.clear()
        self.assignment = rec
        x0,y0,x1,y1 = self.box
        cx,cy = (x0+x1)//2,(y0+y1)//2
        # draw icon
        try:
            img = Image.open(rec["path"]).convert("RGBA")
            img.thumbnail((max(24,x1-x0-10), max(24,y1-y0-10)), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img)
            self.img_id = self.canvas.create_image(cx, cy, image=tkimg)
            if not hasattr(self.canvas, "_imgrefs"): self.canvas._imgrefs = {}
            self.canvas._imgrefs[self.img_id] = tkimg
        except Exception:
            # text fallback
            label = rec["name"]
            if rec["type"]=="STATUS":
                label = STATUS_BADGE.get(rec["name"], rec["name"])
            self.txt_id = self.canvas.create_text(cx, cy, text=label, font=ZONE_FONT)
        self.canvas.itemconfigure(self.hint, state="hidden")

    def highlight(self, on):
        self.canvas.itemconfigure(self.r, outline="#2b6cff" if on else "#8fb0ff")

# ---------------------- Canvas ----------------------
class SymbolCanvas(tk.Canvas):
    def __init__(self, master, **kw):
        super().__init__(master, bg="white", **kw)
        self.affiliation = "Friendly"  # Friendly/Hostile (frame shape)
        self._imgrefs = {}
        self._build()

    def _build(self):
        W,H = int(self["width"]), int(self["height"])
        cx,cy = W//2, H//2
        fw,fh = 520, 320
        self.frame_box = (cx-fw//2, cy-fh//2, cx+fw//2, cy+fh//2)
        self._draw_frame()

        x0,y0,x1,y1 = self.frame_box
        # zones
        self.z_ech = DropZone(self, "ECHELON", {"ECHELON"}, (x0+90, y0-48, x1-90, y0-8), "Echelon")
        self.z_role = DropZone(self, "ROLE", {"ROLE"}, (x0+90, y0+50, x1-90, y1-50), "Role (Branch)")
        self.z_status = DropZone(self, "STATUS", {"STATUS"}, (x1-100, y0+8, x1-8, y0+60), "Status")
        self.z_mob = DropZone(self, "MOBILITY", {"MOBILITY"}, (x0+12, y1-60, x0+110, y1-12), "Mobility")
        self.z_cap = DropZone(self, "CAPABILITY", {"CAPABILITY"}, (x1-110, y1-60, x1-12, y1-12), "Capability")

        # unit name (right of frame)
        self.unit_text = self.create_text(x1+24, (y0+y1)//2, text="", anchor="w", font=("Segoe UI", 12, "bold"))

    def _draw_frame(self):
        self.delete("FRAME")
        x0,y0,x1,y1 = self.frame_box
        if self.affiliation == "Friendly":
            self.create_rectangle(x0,y0,x1,y1, width=3, tags="FRAME")
        else:
            mx,my = (x0+x1)//2,(y0+y1)//2
            self.create_polygon(mx,y0, x1,my, mx,y1, x0,my, outline="black", width=3, fill="", tags="FRAME")

    def set_affiliation(self, aff):
        self.affiliation = aff
        self._draw_frame()
        self.event_generate("<<Changed>>")

    def set_unit_name(self, s):
        self.itemconfigure(self.unit_text, text=s)
        self.event_generate("<<Changed>>")

    def hover(self, x,y, typ):
        for z in (self.z_ech, self.z_role, self.z_status, self.z_mob, self.z_cap):
            z.highlight(z.inside(x,y) and (typ in z.accept))

    def try_drop(self, x_root, y_root, rec):
        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()
        target = None
        for z in (self.z_ech, self.z_role, self.z_status, self.z_mob, self.z_cap):
            z.highlight(False)
            if z.inside(x,y) and rec["type"] in z.accept:
                target = z
        if not target: return False
        target.set_value(rec)
        self.event_generate("<<Changed>>")
        return True

    def clear(self):
        for z in (self.z_ech, self.z_role, self.z_status, self.z_mob, self.z_cap):
            z.clear()
        self.itemconfigure(self.unit_text, text="")
        self.event_generate("<<Changed>>")

    def summary(self):
        role = self.z_role.assignment["name"] if self.z_role.assignment else None
        ech = self.z_ech.assignment["name"] if self.z_ech.assignment else None
        stat = self.z_status.assignment["name"] if self.z_status.assignment else ""
        unit = self.itemcget(self.unit_text, "text").strip()
        if not role or not ech:
            return "(Place Role and Echelon)"
        # Status suffix in words on right label, but status badge in-frame
        stat_txt = f" {stat}" if stat else ""
        name_txt = f" — {unit}" if unit else ""
        # Normalize a few long names
        role_clean = role
        role_clean = role_clean.replace("(Round dot inside the rectangle represents an artillery unit)", "").strip()
        return f"{self.affiliation} {role_clean} {ech}{stat_txt}{name_txt}"

    def to_json(self):
        def val(z): return z.assignment["name"] if z.assignment else None
        return {
            "affiliation": self.affiliation,
            "echelon": val(self.z_ech),
            "role": val(self.z_role),
            "status": val(self.z_status),
            "mobility": val(self.z_mob),
            "capability": val(self.z_cap),
            "unit_name": self.itemcget(self.unit_text, "text").strip() or None
        }

# ---------------------- Drag helper ----------------------
class DragGhost:
    def __init__(self, root, img=None, text=""):
        self.root = root
        self.win = tk.Toplevel(root); self.win.overrideredirect(True); self.win.attributes("-alpha", 0.9)
        frm = ttk.Frame(self.win, padding=2); frm.pack()
        self.lbl = ttk.Label(frm, image=img) if img else ttk.Label(frm, text=text, padding=4, relief="solid")
        if img: self.lbl.image = img
        self.lbl.pack()
        self._m = root.bind_all("<Motion>", self._motion)
        self._u = root.bind_all("<ButtonRelease-1>", self._release)
        self.on_drop = None
        self.payload = None
        self.on_hover = None

    def _motion(self, e):
        self.win.geometry(f"+{e.x_root+10}+{e.y_root+10}")
        if self.on_hover:
            self.on_hover(e)

    def _release(self, e):
        if self.on_drop:
            self.on_drop(e, self.payload)
        self.destroy()

    def destroy(self):
        try:
            self.root.unbind_all("<Motion>", self._m)
            self.root.unbind_all("<ButtonRelease-1>", self._u)
        except Exception:
            pass
        self.win.destroy()

# ---------------------- Palette ----------------------
class Palette(ttk.Frame):
    def __init__(self, master, lib: SymbolLibrary, on_drop, on_hover):
        super().__init__(master)
        self.lib = lib
        self.on_drop = on_drop
        self.on_hover = on_hover

        ttk.Label(self, text="Palette", font=("Segoe UI",12,"bold")).pack(anchor="w", padx=8, pady=(8,4))
        self.nb = ttk.Notebook(self); self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tabs = {}
        for tab, key in [
            ("Echelon","ECHELON"),
            ("Role","ROLE"),
            ("Status","STATUS"),
            ("Mobility","MOBILITY"),
            ("Capability","CAPABILITY"),
            ("Amplifiers","AMPLIFIER"),
            ("Graphics","GRAPHIC"),
        ]:
            f = ttk.Frame(self.nb); self.nb.add(f, text=tab); self.tabs[key]=f

        self._populate()

    def _grid(self, parent, items):
        frm = ttk.Frame(parent); frm.pack(fill="both", expand=True)
        for i, it in enumerate(items):
            cell = ttk.Frame(frm, padding=4, relief="groove")
            cell.grid(row=i//3, column=i%3, sticky="nsew", padx=4, pady=4)
            lbl_img = ttk.Label(cell, image=it["thumb"]) if it["thumb"] else ttk.Label(cell, text="(img)")
            if it["thumb"]: lbl_img.image = it["thumb"]
            lbl_img.pack()
            ttk.Label(cell, text=it["name"], wraplength=120, justify="center").pack(pady=(4,0))
            # drag start
            for w in (cell, lbl_img):
                w.bind("<Button-1>", lambda e, rec=it: self._start_drag(e, rec))
        for c in range(3): frm.grid_columnconfigure(c, weight=1)

    def _populate(self):
        for key, frame in self.tabs.items():
            for w in frame.winfo_children(): w.destroy()
            self._grid(frame, self.lib.by_type.get(key, []))

    def _start_drag(self, event, rec):
        ghost = DragGhost(self.winfo_toplevel(), img=rec["thumb"])
        ghost.payload = rec
        ghost.on_drop = self.on_drop
        ghost.on_hover = self.on_hover

# ---------------------- App ----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Indian Army Symbol Builder (Placeholders)")
        self.geometry("1400x820")
        self.configure(bg="#f4f6fb")

        # left / center / right
        left = ttk.Frame(self, width=360); left.pack(side="left", fill="y")
        center = ttk.Frame(self); center.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(self, width=360); right.pack(side="right", fill="y")

        # library + palette
        self.lib = SymbolLibrary(SYMS_DIR)
        self.palette = Palette(left, self.lib, on_drop=self._on_drop, on_hover=self._on_hover)
        self.palette.pack(fill="both", expand=True)

        # canvas
        self.canvas = SymbolCanvas(center, width=900, height=640)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<<Changed>>", lambda e: self._refresh_summary())

        # right panel
        self._build_right(right)
        self._refresh_summary()

    def _build_right(self, parent):
        fr = ttk.LabelFrame(parent, text="Frame / Affiliation")
        fr.pack(fill="x", padx=8, pady=8)
        v = tk.StringVar(value="Friendly")
        ttk.Radiobutton(fr, text="Friendly (Rectangle)", variable=v, value="Friendly", command=lambda: self.canvas.set_affiliation(v.get())).pack(anchor="w", padx=8, pady=2)
        ttk.Radiobutton(fr, text="Hostile (Rhombus)", variable=v, value="Hostile", command=lambda: self.canvas.set_affiliation(v.get())).pack(anchor="w", padx=8, pady=2)

        fr2 = ttk.LabelFrame(parent, text="Unit name (printed to the right)")
        fr2.pack(fill="x", padx=8, pady=8)
        self.unit_entry = ttk.Entry(fr2)
        self.unit_entry.pack(fill="x", padx=8, pady=6)
        self.unit_entry.bind("<KeyRelease>", lambda e: self.canvas.set_unit_name(self.unit_entry.get()))

        fr3 = ttk.LabelFrame(parent, text="Summary")
        fr3.pack(fill="both", expand=True, padx=8, pady=8)
        self.summary = tk.Text(fr3, height=10, wrap="word")
        self.summary.pack(fill="both", expand=True, padx=8, pady=8)

        btns = ttk.Frame(parent); btns.pack(fill="x", padx=8, pady=8)
        ttk.Button(btns, text="Reload Symbols", command=self._reload).pack(side="left", padx=3)
        ttk.Button(btns, text="Clear", command=self.canvas.clear).pack(side="left", padx=3)
        ttk.Button(btns, text="Export JSON", command=self._export).pack(side="left", padx=3)
        ttk.Button(btns, text="Change Folder", command=self._change_folder).pack(side="right", padx=3)

    def _reload(self):
        self.lib = SymbolLibrary(self.lib.folder)
        self.palette.lib = self.lib
        self.palette._populate()
        messagebox.showinfo("Reloaded", f"Loaded: {self.lib.folder}")

    def _change_folder(self):
        d = filedialog.askdirectory(title="Select extracted_symbols folder")
        if not d: return
        self.lib = SymbolLibrary(d)
        self.palette.lib = self.lib
        self.palette._populate()
        messagebox.showinfo("Folder changed", f"Loaded: {self.lib.folder}")

    def _on_hover(self, e):
        x = self.canvas.winfo_pointerx() - self.canvas.winfo_rootx()
        y = self.canvas.winfo_pointery() - self.canvas.winfo_rooty()
        # Find the "current" typ from a stored ghost? The palette passes the rec in on_drop only,
        # so we conservatively highlight all that match pointer vs last known typ. Simplify:
        # No-op hover highlight here to keep behavior reliable on all platforms.

    def _on_drop(self, event, rec):
        ok = self.canvas.try_drop(event.x_root, event.y_root, rec)
        if not ok:
            # ignore silently or show a toast: invalid slot
            pass
        self._refresh_summary()

    def _refresh_summary(self):
        self.summary.delete("1.0", "end")
        self.summary.insert("end", self.canvas.summary())

    def _export(self):
        data = self.canvas.to_json()
        if not data["echelon"] or not data["role"]:
            messagebox.showwarning("Incomplete", "Place both Role and Echelon before export.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")], initialfile="composite_symbol.json")
        if not p: return
        import json
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", f"Saved to {p}")

if __name__ == "__main__":
    App().mainloop()
