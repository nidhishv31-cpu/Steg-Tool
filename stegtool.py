#!/usr/bin/env python3
"""
Stegtool v2.0  —  Advanced Steganography Suite        Wire format: v4
══════════════════════════════════════════════════════════════════════
⚠  BREAKING CHANGE from v3: v3 images cannot be extracted with v4.
   Scatter-seed now derived from scrypt(pw, salt).  See CHANGELOG.md.
══════════════════════════════════════════════════════════════════════
Features:
  • High-DPI scaling enabled (Fixes pixel blurriness/dullness on Windows)
  • Customize options moved to an independent popup modal
  • 8 Premium Minimalist Presets (Obsidian, Nord Ice, Forest Edge, Deep Steel, 
    Rose Quartz, Slate Light, Cyberpunk Neon, Sepia Warmth)
  • Font size & family configuration dropdowns in the modal
  • Safe context-managed file handling
  • Robust cross-platform drag-and-drop parsing
  • Integrated standard logging (capturing tracebacks)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import os, struct, threading, logging, re
import numpy as np

# Import core functionalities
import steg_core as core

# Initialize GUI logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (GUI) %(message)s")
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# HIGH-DPI SCALING ENHANCEMENT
# ══════════════════════════════════════════════════════════════
try:
    from ctypes import windll
    try:
        if hasattr(windll, 'shcore'):
            windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware (Windows 8.1+)
        elif hasattr(windll, 'user32'):
            windll.user32.SetProcessDPIAware() # Fallback for older systems
    except Exception as e:
        logger.debug(f"Failed setting DPI awareness parameters: {e}")
except Exception as e:
    logger.debug(f"Could not import ctypes windll: {e}")

# ══════════════════════════════════════════════════════════════
# CONSTANTS & CUSTOMIZATION SETUP
# ══════════════════════════════════════════════════════════════
APP_VER = '5.0'
SP = {1:4, 2:8, 3:12, 4:16, 5:20, 6:24, 8:32}

# Color palettes
PALETTES = core.PALETTES if hasattr(core, 'PALETTES') else {
    "Obsidian (Dark)": {
        'bg': '#0a0a0f', 'bg_card': '#12121e', 'bg_input': '#181829',
        'bg_hover': '#222238', 'bg_press': '#1c1c2e', 'sidebar': '#0f0f18',
        'border': '#29293f', 'border_hi': '#4f46e5',
        'accent': '#818cf8', 'accent_dk': '#6366f1',
        'secondary': '#22d3ee', 'sec_dk': '#0ea5e9',
        'danger': '#f87171', 'warning': '#fbbf24', 'success': '#34d399',
        'text': '#f1f5f9', 'text_muted': '#64748b', 'text_dim': '#94a3b8',
        's1': '#f87171', 's2': '#fb923c', 's3': '#fbbf24', 's4': '#34d399', 's5': '#22d3ee',
    }
}
# Default theme initialization
C = dict(PALETTES.get("Obsidian (Dark)", list(PALETTES.values())[0]))

F_FAMILY = "Segoe UI"
F_SIZE_OFFSET = 0

def get_font(key, bold=False):
    base_fonts = {
        'display': (F_FAMILY, 20),
        'title': (F_FAMILY, 14),
        'label': (F_FAMILY, 10),
        'body': (F_FAMILY, 10),
        'caption': (F_FAMILY, 9),
        'mono': ('Consolas', 10),
        'tiny': (F_FAMILY, 8),
    }
    font_name, size = base_fonts.get(key, (F_FAMILY, 10))
    if font_name != 'Consolas': font_name = F_FAMILY
    res_size = max(6, size + F_SIZE_OFFSET)
    return (font_name, res_size, 'bold') if (bold or key in ('display', 'title', 'label')) else (font_name, res_size)

def pw_strength(pw):
    if not pw: return 0, '', 'border'
    s  = (len(pw)>=8) + (len(pw)>=12)
    s += bool(re.search(r'[A-Z]',pw) and re.search(r'[a-z]',pw))
    s += bool(re.search(r'\d',pw))
    s += bool(re.search(r'[^a-zA-Z0-9]',pw))
    return s, ['','Weak','Fair','Good','Strong','Very Strong'][s], \
              ['border','s1','s2','s3','s4','s5'][s]

# ══════════════════════════════════════════════════════════════
# WIDGETS
# ══════════════════════════════════════════════════════════════

class Btn(tk.Button):
    _V = {
        'primary': lambda: (C['accent_dk'],  C['accent'],    C['border_hi'], '#fff'),
        'success': lambda: (C['sec_dk'],     C['secondary'], C['border_hi'], '#fff'),
        'ghost':   lambda: (C['bg_input'],   C['bg_hover'],  C['bg_press'],  C['text']),
        'danger':  lambda: (C['danger'],     '#ff9999',      '#d04040',      '#fff'),
    }
    def __init__(self, parent, text, cmd, variant='primary', **kw):
        bg, hbg, pbg, fg = self._V.get(variant, self._V['primary'])()
        bd_thickness = 1 if variant == 'primary' else 0
        super().__init__(parent, text=text, command=cmd, font=get_font('body', bold=(variant == 'primary')),
                         bg=bg, fg=fg, activebackground=hbg, activeforeground=fg,
                         relief='flat', padx=SP[4], pady=8,
                         cursor='hand2', highlightthickness=bd_thickness, highlightbackground=C['accent'], borderwidth=0, **kw)
        self.bind('<Enter>',           lambda _: self.config(bg=hbg))
        self.bind('<Leave>',           lambda _: self.config(bg=bg))
        self.bind('<Button-1>',        lambda _: self.config(bg=pbg))
        self.bind('<ButtonRelease-1>', lambda _: self.config(bg=hbg))

class DropZone(tk.Frame):
    _DEF_TOP = "Drag & drop image here"
    _DEF_BTM = "or click to Browse"
    def __init__(self, parent, on_click=None, **kw):
        super().__init__(parent, bg=C['bg_input'], highlightbackground=C['border'], highlightthickness=1, relief='flat', **kw)
        self._base = C['border'];  self._hi = C['accent']
        self._ico = tk.Label(self, text='📄', font=get_font('display'), bg=C['bg_input'], fg=C['accent'])
        self._ico.pack(pady=(SP[3], SP[1]))
        self._lbl1 = tk.Label(self, text=self._DEF_TOP, font=get_font('body'), bg=C['bg_input'], fg=C['text_muted'])
        self._lbl1.pack()
        self._lbl2 = tk.Label(self, text=self._DEF_BTM, font=get_font('caption', bold=True), bg=C['bg_input'], fg=C['accent'])
        self._lbl2.pack(pady=(0, SP[3]))
        if on_click:
            for w in (self, self._ico, self._lbl1, self._lbl2):
                w.bind('<Button-1>', lambda _: on_click())
                w.configure(cursor='hand2')
    def highlight(self, on): self.config(highlightbackground=self._hi if on else self._base)
    def set_file(self, name):
        self._ico.config(text='✓', fg=C['secondary'])
        self._lbl1.config(text=name, fg=C['text'])
        self._lbl2.config(text='Image Loaded Successfully', fg=C['secondary'])
    def reset(self):
        self._ico.config(text='📄', fg=C['accent'])
        self._lbl1.config(text=self._DEF_TOP, fg=C['text_muted'])
        self._lbl2.config(text=self._DEF_BTM, fg=C['accent'])

class ToggleSwitch(tk.Canvas):
    W, H = 46, 24
    def __init__(self, parent, var: tk.BooleanVar, cmd=None, **kw):
        super().__init__(parent, width=self.W, height=self.H, bg=parent.cget('bg'), highlightthickness=0, cursor='hand2', **kw)
        self._var = var;  self._cmd = cmd
        self._draw()
        self.bind('<Button-1>', self._click)
    def _draw(self):
        self.delete('all')
        on = self._var.get()
        tc = C['accent_dk'] if on else C['border']
        r  = self.H // 2
        self.create_oval(0, 0, self.H, self.H,   fill=tc, outline='')
        self.create_oval(self.W-self.H, 0, self.W, self.H, fill=tc, outline='')
        self.create_rectangle(r, 0, self.W-r, self.H, fill=tc, outline='')
        tx = self.W - r if on else r
        self.create_oval(tx-r+3, 3, tx+r-3, self.H-3, fill='white', outline='')
    def _click(self, _):
        self._var.set(not self._var.get())
        self._draw()
        if self._cmd: self._cmd()
    def redraw(self): self._draw()

class Toast:
    def __init__(self, root, msg, kind='success', ms=3500):
        colors = {'success': C['success'], 'error': C['danger'], 'warn': C['warning']}
        icons  = {'success': '✓', 'error': '✕', 'warn': '⚠'}
        clr    = colors.get(kind, C['success'])
        ico    = icons.get(kind, '✓')
        w = tk.Toplevel(root)
        w.wm_overrideredirect(True)
        w.attributes('-topmost', True)
        w.configure(bg=clr)
        tk.Label(w, text=f'  {ico}  {msg}  ', font=get_font('body'), bg=clr, fg='#ffffff', padx=SP[4], pady=SP[2]).pack()
        root.update_idletasks()
        tw = w.winfo_reqwidth()
        rx, ry = root.winfo_rootx(), root.winfo_rooty()
        rw = root.winfo_width()
        w.geometry(f'+{rx+rw-tw-SP[4]}+{ry+50}')
        root.after(ms, lambda: self._close(w))
    @staticmethod
    def _close(w):
        try: w.destroy()
        except Exception: pass

# ══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════
class StegtoolApp(TkinterDnD.Tk):

    def __init__(self):
        super().__init__()
        self.title(f'Stegtool v{APP_VER}')
        self.geometry('1120x720')
        self.minsize(940, 600)
        self.configure(bg=C['bg'])

        # Customization system state
        self.theme_var = tk.StringVar(value="Obsidian (Dark)")
        self.font_var  = tk.StringVar(value="Segoe UI")
        self.size_var  = tk.StringVar(value="Normal")

        # Committed active style parameters
        self.active_theme_name = "Obsidian (Dark)"
        self.active_font_family = "Segoe UI"
        self.active_font_scale = "Normal"

        # Persistent stego states
        self._panel     = 'hide'
        self.hide_img   = ''
        self.extr_img   = ''
        self.analyze_img = ''
        self.hide_file  = ''
        self.mode_var   = tk.StringVar(value='text')
        self._enc_var   = tk.BooleanVar(value=True)
        self._prog      = 0.0
        self._going     = False
        self._extracted = None
        self._suggested = ''
        self._snap: dict = {}

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>',      self._on_drop)
        self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.dnd_bind('<<DragLeave>>', self._on_drag_leave)

        # Keyboard shortcuts
        self.bind('<Control-Key-1>', lambda _: self._show_hide())
        self.bind('<Control-Key-2>', lambda _: self._show_extr())
        self.bind('<Control-Key-3>', lambda _: self._show_analyze())
        self.bind('<Control-Key-4>', lambda _: self._show_customize())
        self.bind('<Control-o>',     lambda _: self._shortcut_open())
        self.bind('<Control-O>',     lambda _: self._shortcut_open())

        self._build()
        self._center()

    def _on_drop(self, event):
        path = self._parse_dnd(event.data)
        if not os.path.isfile(path): return
        if self._panel == 'hide': self._on_hide_drop(path)
        elif self._panel == 'extract': self._on_extr_drop(path)
        elif self._panel == 'analyze': self._on_analyze_drop(path)
        self._drag_reset()

    # FIX: Robust cross-platform drag-and-drop path parser (covers spaces/quotes/braces)
    @staticmethod
    def _parse_dnd(data):
        raw = (data or '').strip()
        if raw.startswith('{') and '}' in raw:
            p = raw[1:raw.find('}')]
        else:
            p = raw.split()[0] if raw.split() else ''
        p = p.strip('"').strip("'")
        return os.path.normpath(p)

    def _on_drag_enter(self, _):
        if   self._panel == 'hide'    and hasattr(self, '_hdrop'): self._hdrop.highlight(True)
        elif self._panel == 'extract' and hasattr(self, '_edrop'): self._edrop.highlight(True)

    def _on_drag_leave(self, _):  self._drag_reset()

    def _drag_reset(self):
        if hasattr(self, '_hdrop'): self._hdrop.highlight(False)
        if hasattr(self, '_edrop'): self._edrop.highlight(False)

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f'{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}')

    def _mk_entry(self, parent, show='', **kw):
        return tk.Entry(parent, font=get_font('body'), show=show,
                        bg=C['bg_input'], fg=C['text'], insertbackground=C['text'],
                        relief='flat', highlightthickness=1,
                        highlightcolor=C['border_hi'], highlightbackground=C['border'],
                        **kw)

    def _lbl(self, parent, text, font_key='body', fg=None, bold=False, **kw):
        return tk.Label(parent, text=text, font=get_font(font_key, bold=bold), bg=C['bg_card'], fg=fg or C['text'], **kw)

    def _sep(self, parent, pady=SP[3]):
        tk.Frame(parent, bg=C['border'], height=1).pack(fill='x', pady=pady)

    def _card(self, parent, pad=SP[4]):
        return tk.Frame(parent, bg=C['bg_card'], highlightbackground=C['border'], highlightthickness=1, padx=pad, pady=pad)

    # ─── State Snapshot & Restore ────────────────────────────

    def _snapshot(self):
        s = {}
        if hasattr(self, '_hpw') and self._hpw.winfo_exists():    s['h_pw']  = self._hpw.get()
        if hasattr(self, '_hpw2') and self._hpw2.winfo_exists():   s['h_pw2'] = self._hpw2.get()
        if hasattr(self, '_secret') and self._secret.winfo_exists(): s['h_txt'] = self._secret.get('1.0', tk.END)
        if hasattr(self, '_epw') and self._epw.winfo_exists():    s['e_pw']  = self._epw.get()
        s['encrypt'] = self._enc_var.get()
        self._snap   = s

    def _restore(self):
        s = self._snap
        if 'encrypt' in s: self._enc_var.set(s['encrypt'])
        if hasattr(self, '_hpw') and self._hpw.winfo_exists():
            if s.get('h_pw'):  self._hpw.insert(0, s['h_pw'])
            if hasattr(self, '_hpw2') and self._hpw2.winfo_exists() and s.get('h_pw2'): self._hpw2.insert(0, s['h_pw2'])
            if hasattr(self, '_secret') and self._secret.winfo_exists() and s.get('h_txt','').strip(): self._secret.insert('1.0', s['h_txt'].strip())
            self._upd_strength()
            self._chk_match()
        if hasattr(self, '_epw') and self._epw.winfo_exists() and s.get('e_pw'): self._epw.insert(0, s['e_pw'])

        # Restore images
        if self.hide_img and hasattr(self, '_hdrop') and self._hdrop.winfo_exists():
            self._hdrop.set_file(os.path.basename(self.hide_img))
            if hasattr(self, '_hprev') and self._hprev.winfo_exists():
                self._load_prev(self.hide_img, self._hprev)
            self._upd_cap()
            if hasattr(self, '_jpeg_w') and self._jpeg_w.winfo_exists() and os.path.splitext(self.hide_img)[1].lower() in ('.jpg', '.jpeg'):
                self._jpeg_w.pack(anchor='w', pady=(0, SP[1]))
        if self.extr_img and hasattr(self, '_edrop') and self._edrop.winfo_exists():
            self._edrop.set_file(os.path.basename(self.extr_img))
            if hasattr(self, '_eprev') and self._eprev.winfo_exists():
                self._load_prev(self.extr_img, self._eprev)
        if self.hide_file and hasattr(self, '_flbl') and self._flbl.winfo_exists() and os.path.exists(self.hide_file):
            sz = os.path.getsize(self.hide_file)
            self._flbl.config(text=f'{os.path.basename(self.hide_file)}  ({sz:,} B)', fg=C['text'])

        if self._panel == 'hide' and hasattr(self, '_on_enc_change'): self._on_enc_change(init=True)

    # ─── Customize Panel ──────────────────────────────────────

    def _show_customize(self):
        """Displays customization settings directly inside the main workspace."""
        self._panel = 'customize'
        self._clr()
        self._set_nav(self._nb_c)

        # Header Frame
        hdr = tk.Frame(self.content, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, SP[3]))
        tk.Label(hdr, text='Customize Settings', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(side='left')

        g = tk.Frame(self.content, bg=C['bg'])
        g.pack(fill='both', expand=True)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)
        g.rowconfigure(0, weight=1)

        # Immediate preview callback
        def preview_theme():
            pname = self.theme_var.get()
            if pname in PALETTES:
                C.update(PALETTES[pname])
                self.after(10, self._rebuild_customize)

        def preview_font(event=None):
            global F_FAMILY, F_SIZE_OFFSET
            F_FAMILY = self.font_var.get()
            sz = self.size_var.get()
            if sz == "Small":      F_SIZE_OFFSET = -1
            elif sz == "Large":    F_SIZE_OFFSET = 2
            elif sz == "Huge":     F_SIZE_OFFSET = 4
            else:                  F_SIZE_OFFSET = 0 # Normal
            self.after(10, self._rebuild_customize)

        # ── Left Card (Theme Selector) ───────────────────────
        Lc = self._card(g)
        Lc.grid(row=0, column=0, sticky='nsew', padx=(0, SP[2]))

        self._lbl(Lc, '  Color Presets', font_key='label', fg=C['text_muted']).pack(anchor='w', pady=(0, SP[2]))
        
        # Modern standard radio buttons for theme selection to ensure background colors propagate
        for key in list(PALETTES.keys()):
            rframe = tk.Frame(Lc, bg=C['bg_card'])
            rframe.pack(fill='x', pady=2)
            
            # Palette preview square
            prev = tk.Canvas(rframe, width=32, height=16, bg=PALETTES[key]['bg'], highlightthickness=1, highlightbackground=PALETTES[key]['border'])
            prev.pack(side='left', padx=(0, SP[2]))
            prev.create_rectangle(2, 2, 10, 14, fill=PALETTES[key]['accent'], outline='')
            prev.create_rectangle(12, 2, 20, 14, fill=PALETTES[key]['secondary'], outline='')
            prev.create_rectangle(22, 2, 30, 14, fill=PALETTES[key]['bg_card'], outline='')

            tk.Radiobutton(rframe, text=key, variable=self.theme_var, value=key,
                           bg=C['bg_card'], fg=C['text'], selectcolor=C['bg_input'],
                           activebackground=C['bg_hover'], activeforeground=C['text'],
                           relief='flat', highlightthickness=0, anchor='w',
                           command=preview_theme).pack(side='left', fill='x', expand=True)

        self._sep(Lc, pady=SP[3])

        # Font scale
        self._lbl(Lc, 'Font Scale', font_key='label', fg=C['text_muted']).pack(anchor='w', pady=(SP[1], 2))
        combo_size = ttk.Combobox(Lc, textvariable=self.size_var, 
                                  values=["Small", "Normal", "Large", "Huge"], 
                                  state="readonly")
        combo_size.pack(fill='x', pady=(0, SP[3]))
        combo_size.bind("<<ComboboxSelected>>", preview_font)

        # ── Right Card (Preview & Apply) ─────────────────────
        Rc = self._card(g)
        Rc.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))

        self._lbl(Rc, '  Preview & Typography', font_key='label', fg=C['text_muted']).pack(anchor='w', pady=(0, SP[2]))
        
        # Font family combobox
        self._lbl(Rc, 'Font Family', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(0, 2))
        combo_font = ttk.Combobox(Rc, textvariable=self.font_var, 
                                  values=["Segoe UI", "Arial", "Consolas", "Courier New", "Verdana"], 
                                  state="readonly")
        combo_font.pack(fill='x', pady=(0, SP[3]))
        combo_font.bind("<<ComboboxSelected>>", preview_font)

        # Live styling demo frame
        demo = tk.Frame(Rc, bg=C['bg_input'], highlightbackground=C['border'], highlightthickness=1, padx=SP[3], pady=SP[3])
        demo.pack(fill='both', expand=True, pady=(0, SP[3]))

        tk.Label(demo, text="Live Preview", font=get_font('body', bold=True), bg=C['bg_input'], fg=C['accent']).pack(pady=(0, SP[1]))
        tk.Label(demo, text="AES-256-GCM cipher active", font=get_font('tiny'), bg=C['bg_input'], fg=C['secondary']).pack(pady=(SP[1], 0))

        def apply_changes():
            pname = self.theme_var.get()
            if pname in PALETTES: C.update(PALETTES[pname])
            
            global F_FAMILY, F_SIZE_OFFSET
            F_FAMILY = self.font_var.get()
            sz = self.size_var.get()
            if sz == "Small":      F_SIZE_OFFSET = -1
            elif sz == "Large":    F_SIZE_OFFSET = 2
            elif sz == "Huge":     F_SIZE_OFFSET = 4
            else:                  F_SIZE_OFFSET = 0 # Normal

            self.active_theme_name = pname
            self.active_font_family = F_FAMILY
            self.active_font_scale = sz
            
            self.after(10, self._apply_and_rebuild)

        # Action panel
        bf = tk.Frame(Rc, bg=C['bg_card'])
        bf.pack(fill='x', side='bottom')
        Btn(bf, "Apply Workspace Styles", apply_changes, 'success').pack(fill='x')

    # ─── Build Sidebar and Main ──────────────────────────────

    def _rebuild_customize(self):
        self._snapshot()
        self._build()
        self._restore()
        self._show_customize()

    def _apply_and_rebuild(self):
        self._snapshot()
        self._build()
        self._restore()
        self._show_customize()
        Toast(self, "Styles Applied!", kind="success")

    def _build(self):
        # Configure Ttk global styles matching active dictionary C
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TCombobox', fieldbackground=C['bg_input'], background=C['bg_card'], foreground=C['text'], bordercolor=C['border'], lightcolor=C['border'], darkcolor=C['border'], arrowcolor=C['accent'])
        style.map('TCombobox', fieldbackground=[('readonly', C['bg_input'])], selectbackground=[('readonly', C['accent_dk'])], selectforeground=[('readonly', C['text'])])
        
        self.option_add('*TCombobox*Listbox.background', C['bg_input'])
        self.option_add('*TCombobox*Listbox.foreground', C['text'])
        self.option_add('*TCombobox*Listbox.selectBackground', C['accent'])
        self.option_add('*TCombobox*Listbox.selectForeground', '#070c14')

        logger.info(f"Rebuilding window with theme colors: bg={C['bg']}, sidebar={C['sidebar']}, bg_card={C['bg_card']}")

        for w in self.winfo_children(): w.destroy()
        self.configure(bg=C['bg'])

        root = tk.Frame(self, bg=C['bg'])
        root.pack(fill='both', expand=True)

        # ── Sidebar ──────────────────────────────────────────
        sb = tk.Frame(root, bg=C['sidebar'], width=220)
        sb.pack(side='left', fill='y')
        sb.pack_propagate(False)

        # Logo
        logo = tk.Frame(sb, bg=C['sidebar'])
        logo.pack(fill='x', pady=(SP[5], SP[3]))
        
        logo_canvas = tk.Canvas(logo, width=50, height=60, bg=C['sidebar'], highlightthickness=0)
        logo_canvas.pack(pady=(SP[2], 0))
        # Draw a beautiful modern double shield outline in accent/cyan colors
        logo_canvas.create_polygon(
            [25, 5, 42, 10, 42, 35, 25, 52, 8, 35, 8, 10],
            fill='', outline=C['accent'], width=2, smooth=True
        )
        logo_canvas.create_polygon(
            [25, 12, 37, 16, 37, 33, 25, 45, 13, 33, 13, 16],
            fill='', outline=C['accent_dk'], width=1, smooth=True
        )
        
        tk.Label(logo, text='STEGTOOL', font=get_font('body', bold=True), bg=C['sidebar'], fg=C['text']).pack(pady=(SP[1], 0))
        tk.Label(logo, text=f'v{APP_VER}', font=get_font('tiny'), bg=C['sidebar'], fg=C['text_muted']).pack(pady=(0, SP[4]))

        tk.Frame(sb, bg=C['border'], height=1).pack(fill='x', padx=SP[4])

        # Navigation
        nav = tk.Frame(sb, bg=C['sidebar'])
        nav.pack(fill='x', padx=SP[2], pady=SP[2])
        self._nb_h = self._mknav(nav, '⬆  Hide Data',    self._show_hide)
        self._nb_e = self._mknav(nav, '⬇  Extract Data', self._show_extr)
        self._nb_a = self._mknav(nav, '🔍  Analyze',      self._show_analyze)
        self._nb_c = self._mknav(nav, '⚙  Customize',    self._show_customize)
        
        self._nb_h.pack(fill='x', pady=SP[1])
        self._nb_e.pack(fill='x', pady=SP[1])
        self._nb_a.pack(fill='x', pady=SP[1])
        self._nb_c.pack(fill='x', pady=SP[1])

        # Footer with shortcut hints
        ft = tk.Frame(sb, bg=C['sidebar'])
        ft.pack(side='bottom', fill='x', padx=SP[3], pady=SP[2])
        tk.Label(ft, text='AES-256-GCM · scrypt KDF · zlib', font=get_font('tiny'), bg=C['sidebar'], fg=C['text_muted']).pack()
        tk.Label(ft, text='Ctrl+1/2/3/4  Switch Panels', font=get_font('tiny'), bg=C['sidebar'], fg=C['text_dim']).pack()
        tk.Label(ft, text='Ctrl+O  Open Image', font=get_font('tiny'), bg=C['sidebar'], fg=C['text_dim']).pack()

        # ── Content Panel ────────────────────────────────────
        self.content = tk.Frame(root, bg=C['bg'])
        self.content.pack(side='right', fill='both', expand=True, padx=SP[4], pady=SP[4])
        if self._panel == 'extract':
            self._show_extr()
        elif self._panel == 'analyze':
            self._show_analyze()
        elif self._panel == 'customize':
            self._show_customize()
        else:
            self._show_hide()

    def _mknav(self, parent, text, cmd):
        f = tk.Frame(parent, bg=C['sidebar'], highlightthickness=1, highlightbackground=C['sidebar'], padx=SP[3], pady=SP[2])
        f._active = False
        
        lbl = tk.Label(f, text=text, font=get_font('body'), bg=C['sidebar'], fg=C['text_muted'], cursor='hand2', anchor='w')
        lbl.pack(side='left', fill='x', expand=True)
        
        arr = tk.Label(f, text='', font=get_font('body'), bg=C['sidebar'], fg=C['accent'], cursor='hand2')
        arr.pack(side='right')
        
        f._lbl = lbl; f._arr = arr

        def click(_=None):
            if cmd in (self._show_hide, self._show_extr, self._show_analyze):
                self._revert_unapplied()
            cmd()
        def hover(_=None):
            if not f._active:
                f.config(bg=C['bg_hover']); lbl.config(bg=C['bg_hover'], fg=C['text'])
                arr.config(bg=C['bg_hover'])
        def leave(_=None):
            if not f._active:
                f.config(bg=C['sidebar']); lbl.config(bg=C['sidebar'], fg=C['text_muted'])
                arr.config(bg=C['sidebar'])

        for w in (f, lbl, arr): w.bind('<Button-1>', click); w.bind('<Enter>', hover); w.bind('<Leave>', leave)
        return f

    def _set_nav(self, active):
        for f in (self._nb_h, self._nb_e, self._nb_a, self._nb_c):
            f._active = False
            f.config(bg=C['sidebar'], highlightbackground=C['sidebar'])
            f._lbl.config(bg=C['sidebar'], fg=C['text_muted'])
            f._arr.config(bg=C['sidebar'], text='')
        active._active = True
        active.config(bg=C['bg_hover'], highlightbackground=C['accent'])
        active._lbl.config(bg=C['bg_hover'], fg=C['text'])
        active._arr.config(bg=C['bg_hover'], text='›')

    def _clr(self):
        for w in self.content.winfo_children(): w.destroy()

    def _revert_unapplied(self):
        if (self.theme_var.get() != self.active_theme_name or
            self.font_var.get() != self.active_font_family or
            self.size_var.get() != self.active_font_scale):
            
            C.update(PALETTES[self.active_theme_name])
            self.theme_var.set(self.active_theme_name)
            self.font_var.set(self.active_font_family)
            self.size_var.set(self.active_font_scale)
            
            global F_FAMILY, F_SIZE_OFFSET
            F_FAMILY = self.active_font_family
            sz = self.active_font_scale
            if sz == "Small":      F_SIZE_OFFSET = -1
            elif sz == "Large":    F_SIZE_OFFSET = 2
            elif sz == "Huge":     F_SIZE_OFFSET = 4
            else:                  F_SIZE_OFFSET = 0
            
            self._snapshot()
            self._build()
            self._restore()

    # ════════════════════════════════════════════════════════
    # HIDE PANEL
    # ════════════════════════════════════════════════════════

    def _show_hide(self):
        self._panel = 'hide'
        self._clr()
        self._set_nav(self._nb_h)

        # Header Frame with Badge
        hdr = tk.Frame(self.content, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, SP[3]))
        tk.Label(hdr, text='Hide Data', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(side='left')
        
        badge = tk.Frame(hdr, bg=C['bg_input'], highlightbackground=C['accent'], highlightthickness=1, padx=6, pady=2)
        badge.pack(side='left', padx=SP[3])
        tk.Label(badge, text='⚡ LSB STEGANOGRAPHY', font=get_font('tiny', bold=True), bg=C['bg_input'], fg=C['accent']).pack()

        g = tk.Frame(self.content, bg=C['bg'])
        g.pack(fill='both', expand=True)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)
        g.rowconfigure(0, weight=1)

        # ── Left Card ────────────────────────────────────────
        Lc = self._card(g)
        Lc.grid(row=0, column=0, sticky='nsew', padx=(0, SP[2]))

        self._lbl(Lc, '  Cover Image', font_key='label', fg=C['text_dim']).pack(anchor='w', pady=(0, SP[2]))
        self._hdrop = DropZone(Lc, on_click=self._browse_hide_img, height=100)
        self._hdrop.pack(fill='x', pady=(0, SP[2]))

        self._hprev = tk.Label(Lc, text='No image selected\n\nDrop or browse a PNG / BMP file', font=get_font('caption'), bg=C['bg_input'], fg=C['text_muted'], justify='center', height=7)
        self._hprev.pack(fill='x')

        self._cap_c = tk.Canvas(Lc, height=4, bg=C['bg_input'], highlightthickness=0)
        self._cap_c.pack(fill='x', pady=(SP[1], 0))
        self._cap_l = self._lbl(Lc, 'Capacity: select an image', font_key='tiny', fg=C['text_muted'])
        self._cap_l.pack(anchor='w', pady=(SP[1], 0))

        self._est_l = self._lbl(Lc, '', font_key='tiny', fg=C['text_muted'])
        self._est_l.pack(anchor='w')

        self._jpeg_w = tk.Label(Lc, text='⚠  JPEG is lossy — data may be destroyed!', font=get_font('tiny'), bg=C['bg_card'], fg=C['warning'])

        self._sep(Lc, pady=SP[3])

        # Encryption toggle
        enc_row = tk.Frame(Lc, bg=C['bg_card'])
        enc_row.pack(fill='x', pady=(0, SP[2]))
        self._enc_sw = ToggleSwitch(enc_row, self._enc_var, self._on_enc_change)
        self._enc_sw.pack(side='left', padx=(0, SP[3]))

        enc_txt = tk.Frame(enc_row, bg=C['bg_card'])
        enc_txt.pack(side='left')
        self._lbl(enc_txt, 'Encrypt with AES-256-GCM', font_key='label').pack(anchor='w')
        self._lbl(enc_txt, 'scrypt KDF · password-protected', font_key='tiny', fg=C['text_muted']).pack(anchor='w')

        self._pw_frame = tk.Frame(Lc, bg=C['bg_card'])
        self._build_pw_block(self._pw_frame)

        self._plain_note = tk.Frame(Lc, bg=C['bg_input'], highlightbackground=C['warning'], highlightthickness=1, padx=12, pady=10)
        hdr_box = tk.Frame(self._plain_note, bg=C['bg_input'])
        hdr_box.pack(fill='x', anchor='w')
        tk.Label(hdr_box, text='⚠ UNENCRYPTED MODE', font=get_font('caption', bold=True), bg=C['bg_input'], fg=C['warning']).pack(side='left')
        tk.Label(self._plain_note, 
                 text='No password protection will be applied. Anyone with Stegtool or an LSB extractor can reveal this hidden content.', 
                 font=get_font('tiny'), bg=C['bg_input'], fg=C['text_muted'], justify='left', wraplength=260).pack(anchor='w', pady=(4, 0))

        self._on_enc_change(init=True)

        # ── Right Card ───────────────────────────────────────
        Rc = self._card(g)
        Rc.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))

        mf = tk.Frame(Rc, bg=C['bg_card'])
        mf.pack(fill='x', pady=(0, SP[3]))
        self._lbl(mf, 'Data Type:', font_key='label').pack(side='left', pady=4)
        
        self._mode_buttons = {}
        def select_mode(val):
            self.mode_var.set(val)
            for k, btn in self._mode_buttons.items():
                if k == val:
                    btn.config(bg=C['bg_hover'], fg=C['accent'], highlightbackground=C['accent'], highlightthickness=1)
                else:
                    btn.config(bg=C['bg_card'], fg=C['text_muted'], highlightbackground=C['border'], highlightthickness=1)
            self._toggle_mode()

        for val, txt in [('text', '📄 Text'), ('file', '📁 File')]:
            btn = tk.Button(mf, text=txt, font=get_font('body'), relief='flat', bd=0, padx=12, pady=4, cursor='hand2')
            btn.config(command=lambda v=val: select_mode(v))
            btn.pack(side='left', padx=(SP[2], 0))
            self._mode_buttons[val] = btn

        self._mode_cont = tk.Frame(Rc, bg=C['bg_card'])
        self._mode_cont.pack(fill='both', expand=True)

        # Text container
        self._tf = tk.Frame(self._mode_cont, bg=C['bg_card'])
        self._lbl(self._tf, 'Secret Message:', font_key='label').pack(anchor='w', pady=(0, SP[1]))
        self._secret = scrolledtext.ScrolledText(self._tf, wrap=tk.WORD, height=12, font=get_font('mono'), bg=C['bg_input'], fg=C['text'], insertbackground=C['text'], relief='flat', highlightthickness=1, highlightcolor=C['border_hi'], highlightbackground=C['border'], padx=SP[2], pady=SP[2])
        self._secret.pack(fill='both', expand=True)
        self._secret.bind('<KeyRelease>', lambda _: self._upd_psnr())

        # File container
        self._ff = tk.Frame(self._mode_cont, bg=C['bg_card'])
        self._lbl(self._ff, 'File to Hide:', font_key='label').pack(anchor='w', pady=(0, SP[1]))
        fr = tk.Frame(self._ff, bg=C['bg_card'])
        fr.pack(fill='x')
        self._flbl = tk.Label(fr, text='No file selected', font=get_font('body'), bg=C['bg_input'], fg=C['text_muted'], padx=SP[2], pady=6, anchor='w')
        self._flbl.pack(side='left', fill='x', expand=True)
        Btn(fr, 'Browse…', self._browse_hide_file, 'ghost').pack(side='left', padx=(SP[1], 0))

        # Initialize selected state for segmented buttons
        select_mode(self.mode_var.get())

        self._sep(Rc)
        bf = tk.Frame(Rc, bg=C['bg_card'])
        bf.pack(fill='x', pady=(0, SP[2]))
        self._hbtn = Btn(bf, '⬆  Hide in Image', self._do_hide, 'success')
        self._hbtn.pack(side='left', padx=(0, SP[2]))
        Btn(bf, 'Clear', self._clear_hide, 'ghost').pack(side='left')

        self._prog_c = tk.Canvas(Rc, height=4, bg=C['bg_input'], highlightthickness=0)
        self._prog_c.pack(fill='x')
        self._hstat = self._lbl(Rc, '', font_key='caption', fg=C['text_muted'])
        self._hstat.pack(anchor='w', pady=(SP[1], 0))

    def _build_pw_block(self, parent):
        self._lbl(parent, 'Password:', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[2], SP[1]))
        self._hpw = self._mk_entry(parent, show='*')
        self._hpw.pack(fill='x', ipady=5)
        self._hpw.bind('<KeyRelease>', lambda _: self._upd_strength())

        self._str_c = tk.Canvas(parent, height=4, bg=C['bg_input'], highlightthickness=0)
        self._str_c.pack(fill='x', pady=(2, 0))
        self._str_l = self._lbl(parent, '', font_key='tiny', fg=C['text_muted'])
        self._str_l.pack(anchor='e')

        self._lbl(parent, 'Confirm:', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[1], SP[1]))
        self._hpw2 = self._mk_entry(parent, show='*')
        self._hpw2.pack(fill='x', ipady=5)
        self._hpw2.bind('<KeyRelease>', lambda _: self._chk_match())

        self._pmatch = self._lbl(parent, '', font_key='tiny', fg=C['text_muted'])
        self._pmatch.pack(anchor='w', pady=(2, 0))

        # Keyfile 2FA Row
        self._lbl(parent, 'Keyfile 2FA (Optional):', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[2], SP[1]))
        kf_row = tk.Frame(parent, bg=C['bg_card'])
        kf_row.pack(fill='x')
        self._hkeyfile_lbl = tk.Label(kf_row, text='No keyfile selected', font=get_font('tiny'), bg=C['bg_input'], fg=C['text_muted'], anchor='w', padx=6, pady=4)
        self._hkeyfile_lbl.pack(side='left', fill='x', expand=True)
        Btn(kf_row, 'Keyfile…', self._browse_hide_keyfile, 'ghost').pack(side='left', padx=(4, 0))

    def _on_enc_change(self, init=False):
        if self._enc_var.get():
            self._plain_note.pack_forget()
            self._pw_frame.pack(fill='x')
        else:
            self._pw_frame.pack_forget()
            self._plain_note.pack(fill='x', pady=(SP[1], 0))
        if not init: self._upd_cap()
        if hasattr(self, '_enc_sw'): self._enc_sw.redraw()

    def _upd_strength(self):
        if not hasattr(self, '_hpw'): return
        score, lbl, key = pw_strength(self._hpw.get())
        self._str_c.delete('all')
        if score:
            w = self._str_c.winfo_width() or 200
            self._str_c.create_rectangle(0, 0, int(w*score/5), 4, fill=C[key], outline='')
        self._str_l.config(text=lbl, fg=C.get(key, C['text_muted']))
        self._upd_psnr()

    def _chk_match(self):
        if not hasattr(self, '_hpw'): return
        p1, p2 = self._hpw.get(), self._hpw2.get()
        if not p2:
            self._pmatch.config(text='')
            self._hpw2.config(highlightbackground=C['border'])
        elif p1 == p2:
            self._pmatch.config(text='✓ Passwords match', fg=C['success'])
            self._hpw2.config(highlightbackground=C['success'])
        else:
            self._pmatch.config(text='✗ Passwords do not match', fg=C['danger'])
            self._hpw2.config(highlightbackground=C['danger'])

    def _upd_psnr(self):
        if not self.hide_img or not hasattr(self, '_est_l'): return
        try:
            if self.mode_var.get() == 'text':
                txt  = self._secret.get('1.0', tk.END).strip() if hasattr(self,'_secret') else ''
                size = len(txt.encode('utf-8')) + 1
            elif self.hide_file and os.path.exists(self.hide_file):
                size = os.path.getsize(self.hide_file) + 3 + len(os.path.basename(self.hide_file))
            else: return
            ep = core.Stego.estimate_psnr(self.hide_img, size)
            if ep == float('inf'): self._est_l.config(text='Est. PSNR: Perfect', fg=C['success'])
            elif ep > 40: self._est_l.config(text=f'Est. PSNR: ~{ep:.1f} dB  ✓', fg=C['secondary'])
            else: self._est_l.config(text=f'Est. PSNR: ~{ep:.1f} dB  ⚠', fg=C['warning'])
        except Exception as e:
            logger.debug(f"Failed calculating estimated PSNR: {e}")

    def _toggle_mode(self):
        if self.mode_var.get() == 'text':
            self._ff.pack_forget()
            self._tf.pack(fill='both', expand=True)
        else:
            self._tf.pack_forget()
            self._ff.pack(fill='both', expand=True)
        self._upd_psnr()

    def _on_hide_drop(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg'): self._jpeg_w.pack(anchor='w', pady=(SP[1], 0))
        elif ext not in ('.png', '.bmp'):
            messagebox.showwarning('Invalid File', 'Please use a PNG or BMP cover image.'); return
        else: self._jpeg_w.pack_forget()
        self.hide_img = path
        self._hdrop.set_file(os.path.basename(path))
        self._load_prev(path, self._hprev)
        self._upd_cap()
        self._upd_psnr()

    def _browse_hide_img(self):
        p = filedialog.askopenfilename(title='Select Cover Image', filetypes=[('Image files','*.png *.bmp *.jpg *.jpeg'), ('PNG','*.png'),('BMP','*.bmp'),('JPEG','*.jpg *.jpeg')])
        if p: self._on_hide_drop(p)

    def _browse_hide_file(self):
        p = filedialog.askopenfilename(title='Select File to Hide')
        if p:
            self.hide_file = p
            sz = os.path.getsize(p)
            self._flbl.config(text=f'{os.path.basename(p)}  ({sz:,} B)', fg=C['text'])
            self._upd_psnr()

    def _load_prev(self, path, lbl, mx=(320, 200)):
        try:
            with Image.open(path) as img:
                img = img.convert('RGB')
                img.thumbnail(mx)
                ph = ImageTk.PhotoImage(img)
            lbl.config(image=ph, text='', height=ph.height())
            lbl.image = ph
        except Exception as e:
            logger.error(f"Failed loading thumbnail preview for {path}: {e}")
            lbl.config(image='', text='Preview unavailable', height=6)

    def _upd_cap(self):
        if not self.hide_img: return
        enc = self._enc_var.get() if hasattr(self, '_enc_var') else True
        cap = core.Stego.capacity(self.hide_img, encrypted=enc)
        mode = 'encrypted' if enc else 'plain'
        self._cap_l.config(text=f'Capacity ({mode}): {cap:,} bytes')
        self._cap_c.delete('all')
        if cap:
            w = self._cap_c.winfo_width() or 200
            self._cap_c.create_rectangle(0, 0, w, 4, fill=C['accent'] if enc else C['secondary'], outline='')

    def _do_hide(self):
        if not self.hide_img: messagebox.showwarning('No Image', 'Please select a cover image.'); return
        encrypt = self._enc_var.get()
        pw = ''
        if encrypt:
            pw  = self._hpw.get()
            pw2 = self._hpw2.get()
            if not pw: messagebox.showwarning('No Password', 'Please enter a password.'); return
            if pw != pw2: messagebox.showerror('Mismatch', 'Passwords do not match.'); return
            
            # FIX: Warn user on weak/fair passwords with confirmation prompts
            score, label, _ = pw_strength(pw)
            if score <= 2:
                ans = messagebox.askyesno("Weak Password", 
                                          f"The password you entered is '{label}'. This leaves the steganography "
                                          "vulnerable to brute-force dictionary attacks. Proceed anyway?")
                if not ans:
                    return

        if self.mode_var.get() == 'text':
            txt = self._secret.get('1.0', tk.END).strip()
            if not txt: messagebox.showwarning('Empty', 'Please enter a secret message.'); return
            plain = core.pack_text(txt)
        else:
            if not self.hide_file or not os.path.exists(self.hide_file): messagebox.showwarning('No File', 'Please select a file to hide.'); return
            with open(self.hide_file, 'rb') as fh: plain = core.pack_file(self.hide_file, fh.read())

        cap = core.Stego.capacity(self.hide_img, encrypted=encrypt)
        if len(plain) > cap: messagebox.showerror('Too Large', f'Data is {len(plain):,} B but image holds only {cap:,} B.'); return

        out = filedialog.asksaveasfilename(title='Save Stego Image', defaultextension='.png', filetypes=[('PNG Image','*.png'),('BMP Image','*.bmp')])
        if not out: return

        # FIX: Ensure output format is lossless (PNG/BMP) to prevent JPEG destruction
        if out.lower().endswith(('.jpg', '.jpeg')):
            out = os.path.splitext(out)[0] + '.png'
            messagebox.showinfo('Format Adjusted', 
                                'JPEG format uses lossy compression which destroys hidden LSB steganography.\n\n'
                                f'Stegtool has automatically saved your output image in PNG format:\n{out}')

        self._hbtn.config(state='disabled', text='Working…')
        self._going = True; self._prog = 0.0
        self._poll()
        self.update()

        def work():
            def cb(v): self._prog = v
            kf = getattr(self, '_hkeyfile_bytes', b'')
            if encrypt: ok, msg = core.Stego.hide(self.hide_img, plain, pw, out, cb, keyfile_bytes=kf)
            else: ok, msg = core.Stego.hide_plain(self.hide_img, plain, out, cb)
            self.after(0, lambda: self._hide_done(ok, msg, out))
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        if not self._going: return
        v = self._prog
        self._prog_c.delete('all')
        W = self._prog_c.winfo_width() or 300
        if v > 0: self._prog_c.create_rectangle(0, 0, max(4, int(W * min(v, 1.0))), 4, fill=C['secondary'], outline='')
        if   v < 0.03: msg, clr = 'Starting…',                           C['text_muted']
        elif v < 0.25: msg, clr = 'Deriving keys via scrypt (~1 s)…',    C['warning']
        elif v < 0.46: msg, clr = 'Encrypting & preparing payload…',     C['warning']
        elif v < 0.87: msg, clr = 'Embedding data…',                     C['warning']
        else:          msg, clr = 'Saving…',                              C['warning']
        self._hstat.config(text=msg, fg=clr)
        self.after(80, self._poll)

    def _hide_done(self, ok, msg, out):
        self._going = False
        self._hbtn.config(state='normal', text='⬆  Hide in Image')
        self._prog_c.delete('all')
        if ok:
            self._last_out = out
            p  = core.Stego.psnr(self.hide_img, out)
            pt = f'PSNR: {p:.2f} dB' if p != float('inf') else 'PSNR: Perfect'
            self._hstat.config(text=f'{msg}  ·  {pt}', fg=C['success'])
            Toast(self, f'{msg}', kind='success')
            # Add comparison button
            if hasattr(self, '_cmp_btn') and self._cmp_btn.winfo_exists():
                self._cmp_btn.destroy()
            self._cmp_btn = Btn(self.content, '🔍 View Before/After', lambda: self._show_comparison(self.hide_img, out), 'ghost')
            self._cmp_btn.pack(anchor='e', pady=(SP[1], 0))
        else:
            self._hstat.config(text=msg, fg=C['danger'])
            messagebox.showerror('Hide Failed', msg)

    def _clear_hide(self):
        self.hide_img = self.hide_file = ''
        self._hdrop.reset()
        self._hprev.config(image='', text='No image selected\n\nDrop or browse a PNG / BMP file')
        self._hprev.image = None
        if hasattr(self, '_hpw'):
            self._hpw.delete(0, tk.END)
            self._hpw2.delete(0, tk.END)
            self._hpw2.config(highlightbackground=C['border'])
        if hasattr(self, '_secret'): self._secret.delete('1.0', tk.END)
        self._flbl.config(text='No file selected', fg=C['text_muted'])
        self._cap_l.config(text='Capacity: select an image')
        self._est_l.config(text='')
        self._cap_c.delete('all')
        self._prog_c.delete('all')
        self._hstat.config(text='')
        if hasattr(self, '_str_c'): self._str_c.delete('all')
        if hasattr(self, '_str_l'): self._str_l.config(text='')
        if hasattr(self, '_pmatch'): self._pmatch.config(text='')
        self._jpeg_w.pack_forget()

    # ════════════════════════════════════════════════════════
    # EXTRACT PANEL
    # ════════════════════════════════════════════════════════

    def _show_extr(self):
        self._panel = 'extract'
        self._clr()
        self._set_nav(self._nb_e)

        # Header Frame with Badge
        hdr = tk.Frame(self.content, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, SP[3]))
        tk.Label(hdr, text='Extract Data', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(side='left')
        
        badge = tk.Frame(hdr, bg=C['bg_input'], highlightbackground=C['accent'], highlightthickness=1, padx=6, pady=2)
        badge.pack(side='left', padx=SP[3])
        tk.Label(badge, text='⚡ LSB STEGANOGRAPHY', font=get_font('tiny', bold=True), bg=C['bg_input'], fg=C['accent']).pack()

        g = tk.Frame(self.content, bg=C['bg'])
        g.pack(fill='both', expand=True)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=2)
        g.rowconfigure(0, weight=1)

        # ── Left Card ────────────────────────────────────────
        Lc = self._card(g)
        Lc.grid(row=0, column=0, sticky='nsew', padx=(0, SP[2]))

        self._lbl(Lc, '  Stego Image', font_key='label', fg=C['text_dim']).pack(anchor='w', pady=(0, SP[2]))
        self._edrop = DropZone(Lc, on_click=self._browse_extr_img, height=100)
        self._edrop.pack(fill='x', pady=(0, SP[2]))

        self._eprev = tk.Label(Lc, text='No image selected\n\nDrop or browse a PNG / BMP file', font=get_font('caption'), bg=C['bg_input'], fg=C['text_muted'], justify='center', height=7)
        self._eprev.pack(fill='x')

        self._sep(Lc)
        self._lbl(Lc, 'Password (if encrypted):', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(0, SP[1]))
        self._epw = self._mk_entry(Lc, show='*')
        self._epw.pack(fill='x', ipady=5)

        # Keyfile 2FA for Extract
        self._lbl(Lc, 'Keyfile 2FA (if used):', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[1], SP[1]))
        ekf_row = tk.Frame(Lc, bg=C['bg_card'])
        ekf_row.pack(fill='x', pady=(0, SP[2]))
        self._ekeyfile_lbl = tk.Label(ekf_row, text='No keyfile selected', font=get_font('tiny'), bg=C['bg_input'], fg=C['text_muted'], anchor='w', padx=6, pady=4)
        self._ekeyfile_lbl.pack(side='left', fill='x', expand=True)
        Btn(ekf_row, 'Keyfile…', self._browse_extr_keyfile, 'ghost').pack(side='left', padx=(4, 0))

        Btn(Lc, '⬇  Reveal Hidden Data', self._do_extr, 'primary').pack(fill='x')
        self._estat = self._lbl(Lc, '', font_key='caption', fg=C['text_muted'])
        self._estat.pack(anchor='w', pady=(SP[2], 0))

        # ── Right Card ───────────────────────────────────────
        Rc = self._card(g)
        Rc.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))

        self._lbl(Rc, '  Extracted Data', font_key='label', fg=C['text_dim']).pack(anchor='w', pady=(0, SP[2]))
        self._rtxt = scrolledtext.ScrolledText(Rc, wrap=tk.WORD, height=15, font=get_font('mono'), bg=C['bg_input'], fg=C['text'], insertbackground=C['text'], relief='flat', highlightthickness=1, highlightcolor=C['border_hi'], highlightbackground=C['border'], padx=SP[2], pady=SP[2])
        self._rtxt.pack(fill='both', expand=True)
        self._rtxt.insert('1.0', 'Extracted content will appear here…')
        self._rtxt.config(state='disabled')

        self._sf = tk.Frame(Rc, bg=C['bg_card'])
        Btn(self._sf, '⬇ Save as File', self._save_extr, 'primary').pack(side='left', padx=(0, SP[2]))
        Btn(self._sf, '📋 Copy & Auto-Wipe (30s)', self._copy_autowipe_clipboard, 'ghost').pack(side='left')
        self._sname = self._lbl(self._sf, '', font_key='caption', fg=C['text_muted'])
        self._sname.pack(side='left', padx=(SP[2], 0))

    def _on_extr_drop(self, path):
        if not path.lower().endswith(('.png', '.bmp')): messagebox.showwarning('Invalid File', 'Use a PNG or BMP stego image.'); return
        self.extr_img = path
        self._edrop.set_file(os.path.basename(path))
        self._load_prev(path, self._eprev)

    def _browse_extr_img(self):
        p = filedialog.askopenfilename(title='Select Stego Image', filetypes=[('Image files','*.png *.bmp'),('PNG','*.png'),('BMP','*.bmp')])
        if p: self._on_extr_drop(p)

    def _do_extr(self):
        if not self.extr_img: messagebox.showwarning('No Image', 'Please select a stego image.'); return
        pw = self._epw.get()
        kf = getattr(self, '_ekeyfile_bytes', b'')
        self._estat.config(text='Extracting…  (if encrypted, deriving keys takes ~1s)', fg=C['warning'])
        self.update()
        def work():
            ok, res = core.Stego.extract(self.extr_img, pw, keyfile_bytes=kf)
            self.after(0, lambda: self._extr_done(ok, res))
        threading.Thread(target=work, daemon=True).start()

    def _extr_done(self, ok, res):
        self._rtxt.config(state='normal')
        self._rtxt.delete('1.0', tk.END)
        self._sf.pack_forget()
        self._extracted = None

        if ok:
            mode, content = res
            if mode == 'text':
                self._rtxt.insert('1.0', content)
                self._extracted = content.encode('utf-8')
                self._suggested = 'extracted_text.txt'
                self._estat.config(text=f'✓  Text extracted — {len(content):,} chars.', fg=C['success'])
                Toast(self, f'Text extracted ({len(content):,} chars)', kind='success')
            else:
                fname, fdata = content
                self._extracted = fdata
                self._suggested = fname
                self._rtxt.insert('1.0', f'[File: {fname}  —  {len(fdata):,} bytes]\n\n')
                self._rtxt.insert(tk.END, fdata[:512].hex())
                if len(fdata) > 512: self._rtxt.insert(tk.END, f'\n\n… ({len(fdata)-512:,} more bytes)')
                self._estat.config(text=f'✓  File "{fname}" extracted  ({len(fdata):,} B).', fg=C['success'])
                Toast(self, f'File extracted: {fname}', kind='success')
            self._sname.config(text=f'→  {self._suggested}')
            self._sf.pack(fill='x', pady=(SP[3], 0))
        else:
            self._rtxt.insert('1.0', f'[Error]\n\n{res}')
            self._estat.config(text=res, fg=C['danger'])
            Toast(self, 'Extraction failed', kind='error', ms=4000)
        self._rtxt.config(state='disabled')

    def _save_extr(self):
        if self._extracted is None: return
        p = filedialog.asksaveasfilename(title='Save Extracted File', initialfile=self._suggested)
        if p:
            try:
                with open(p, 'wb') as fh: fh.write(self._extracted)
                Toast(self, f'Saved: {os.path.basename(p)}', kind='success')
            except OSError as e: messagebox.showerror('Save Failed', f'Could not save:\n{e}')


    # ════════════════════════════════════════════════════════
    # ANALYZE PANEL (Steganalysis)
    # ════════════════════════════════════════════════════════

    def _show_analyze(self):
        self._panel = 'analyze'
        self._clr()
        self._set_nav(self._nb_a)

        # Header
        hdr = tk.Frame(self.content, bg=C['bg'])
        hdr.pack(fill='x', pady=(0, SP[3]))
        tk.Label(hdr, text='Steganalysis', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(side='left')
        badge = tk.Frame(hdr, bg=C['bg_input'], highlightbackground=C['accent'], highlightthickness=1, padx=6, pady=2)
        badge.pack(side='left', padx=SP[3])
        tk.Label(badge, text='⚡ CHI-SQUARE DETECTION', font=get_font('tiny', bold=True), bg=C['bg_input'], fg=C['accent']).pack()

        # Export Report Buttons
        exp_row = tk.Frame(hdr, bg=C['bg'])
        exp_row.pack(side='right')
        Btn(exp_row, '📄 HTML Report', self._export_html_report, 'ghost').pack(side='left', padx=(0, 6))
        Btn(exp_row, '📕 PDF Report', self._export_pdf_report, 'primary').pack(side='left')

        g = tk.Frame(self.content, bg=C['bg'])
        g.pack(fill='both', expand=True)
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=2)
        g.rowconfigure(0, weight=1)

        # ── Left Card: Image Input ────────────────────────
        Lc = self._card(g)
        Lc.grid(row=0, column=0, sticky='nsew', padx=(0, SP[2]))

        self._lbl(Lc, '  Image to Analyze', font_key='label', fg=C['text_dim']).pack(anchor='w', pady=(0, SP[2]))
        self._adrop = DropZone(Lc, on_click=self._browse_analyze_img, height=100)
        self._adrop.pack(fill='x', pady=(0, SP[2]))

        self._aprev = tk.Label(Lc, text='No image selected\n\nDrop or browse a PNG / BMP / WAV file', font=get_font('caption'), bg=C['bg_input'], fg=C['text_muted'], justify='center', height=7)
        self._aprev.pack(fill='x')

        self._sep(Lc)
        Btn(Lc, '🔍  Run Analysis', self._do_analyze, 'primary').pack(fill='x', pady=(SP[2], 0))
        self._astat = self._lbl(Lc, '', font_key='caption', fg=C['text_muted'])
        self._astat.pack(anchor='w', pady=(SP[2], 0))

        # ── Right Card: Results ───────────────────────────
        Rc = self._card(g)
        Rc.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))

        # Results header row with channel selector
        rf_hdr = tk.Frame(Rc, bg=C['bg_card'])
        rf_hdr.pack(fill='x', pady=(0, SP[2]))
        self._lbl(rf_hdr, '  Analysis Results', font_key='label', fg=C['text_dim']).pack(side='left')

        # Channel Filter buttons
        self.channel_var = tk.StringVar(value='all')
        chan_frame = tk.Frame(rf_hdr, bg=C['bg_card'])
        chan_frame.pack(side='right')
        self._chan_buttons = {}
        for c_id, c_label in [('all', 'All'), ('r', 'R'), ('g', 'G'), ('b', 'B'), ('lum', 'Lum')]:
            btn = tk.Button(chan_frame, text=c_label, font=get_font('tiny', bold=True), bg=C['bg_input'], fg=C['text_muted'], relief='flat', padx=6, pady=2,
                            command=lambda cid=c_id: self._set_analysis_channel(cid))
            btn.pack(side='left', padx=1)
            self._chan_buttons[c_id] = btn

        # Confidence gauge
        self._gauge_frame = tk.Frame(Rc, bg=C['bg_card'])
        self._gauge_frame.pack(fill='x', pady=(0, SP[3]))

        self._gauge_c = tk.Canvas(self._gauge_frame, height=24, bg=C['bg_input'], highlightthickness=0)
        self._gauge_c.pack(fill='x')
        self._gauge_l = self._lbl(self._gauge_frame, 'Run analysis to see results', font_key='body', fg=C['text_muted'])
        self._gauge_l.pack(anchor='w', pady=(SP[1], 0))

        self._sep(Rc)

        # Metrics grid
        self._metrics_frame = tk.Frame(Rc, bg=C['bg_card'])
        self._metrics_frame.pack(fill='x', pady=(SP[2], SP[3]))

        metrics = [
            ('Status', '--'),
            ('Chi² Score', '--'),
            ('P-Value', '--'),
            ('Confidence', '--'),
            ('LSB Ratio', '--'),
            ('Pixel Count', '--'),
        ]
        self._metric_labels = {}
        for i, (label, val) in enumerate(metrics):
            row = tk.Frame(self._metrics_frame, bg=C['bg_card'])
            row.pack(fill='x', pady=2)
            self._lbl(row, label, font_key='caption', fg=C['text_muted']).pack(side='left')
            v = self._lbl(row, val, font_key='body', fg=C['text'])
            v.pack(side='right')
            self._metric_labels[label] = v

        self._sep(Rc)

        # Verdict
        self._verdict_l = self._lbl(Rc, '', font_key='title', fg=C['text_muted'])
        self._verdict_l.pack(anchor='w', pady=(SP[2], 0))

        # Histogram Section Header & Image Label (matches PDF/HTML report graph)
        self._lbl(Rc, '📊 Pixel Frequency Spectrum (Logarithmic LSB Pairs)', font_key='caption', bold=True, fg=C['text_dim']).pack(anchor='w', pady=(SP[3], SP[1]))
        self._hist_lbl = tk.Label(Rc, bg='#080e18', highlightthickness=1, highlightbackground=C['border'])
        self._hist_lbl.pack(fill='x', pady=(0, SP[2]))

        # Auto-redraw canvases on window resize
        self._gauge_c.bind('<Configure>', lambda _: self._redraw_analysis_canvases())
        self._hist_lbl.bind('<Configure>', lambda _: self._redraw_analysis_canvases())
        self._last_analysis_result = None

    def _set_analysis_channel(self, cid):
        self.channel_var.set(cid)
        for k, btn in getattr(self, '_chan_buttons', {}).items():
            if k == cid:
                btn.config(bg=C['accent_dk'], fg='#ffffff')
            else:
                btn.config(bg=C['bg_input'], fg=C['text_muted'])
        if hasattr(self, 'analyze_img') and self.analyze_img:
            self._do_analyze()

    def _browse_analyze_img(self):
        p = filedialog.askopenfilename(title='Select Image to Analyze', filetypes=[('Image files','*.png *.bmp *.jpg *.jpeg'), ('PNG','*.png'),('BMP','*.bmp'),('JPEG','*.jpg *.jpeg')])
        if p: self._on_analyze_drop(p)

    def _on_analyze_drop(self, path):
        self.analyze_img = path
        self._adrop.set_file(os.path.basename(path))
        self._load_prev(path, self._aprev)

    def _do_analyze(self):
        if not hasattr(self, 'analyze_img') or not self.analyze_img:
            messagebox.showwarning('No Image', 'Please select an image to analyze.')
            return
        chan = getattr(self, 'channel_var', tk.StringVar(value='all')).get()
        self._astat.config(text=f'Analyzing ({chan.upper()} channel)…', fg=C['warning'])
        self.update()

        def work():
            result = core.Stego.analyze(self.analyze_img, channel=chan)
            self.after(0, lambda: self._analyze_done(result))
        threading.Thread(target=work, daemon=True).start()

    def _analyze_done(self, result):
        if 'error' in result:
            self._astat.config(text=f'Analysis failed: {result["error"]}', fg=C['danger'])
            return

        self._astat.config(text='Analysis complete', fg=C['success'])
        self._last_analysis_result = result
        self.update_idletasks()
        self._redraw_analysis_canvases()

    def _redraw_analysis_canvases(self):
        result = self._last_analysis_result
        if not result or not hasattr(self, '_gauge_c') or not self._gauge_c.winfo_exists():
            return

        conf = result['confidence']
        status = result.get('encryption_status', '')

        # Select harmonious status color based on encryption level
        if 'Unencrypted' in status:
            bar_color = C['warning']
        elif 'Encrypted' in status:
            bar_color = C['secondary']
        elif 'Lossy' in status:
            bar_color = C['danger']
        elif conf > 0.4:
            bar_color = C['accent']
        else:
            bar_color = C['text_muted']

        # Redraw confidence gauge bar
        self._gauge_c.delete('all')
        self.update_idletasks()
        w = max(200, self._gauge_c.winfo_width())
        draw_w = max(6, int(w * max(0.02, conf)))
        self._gauge_c.create_rectangle(0, 0, draw_w, 24, fill=bar_color, outline='')
        self._gauge_l.config(text=f'{conf*100:.1f}% — {result["verdict"]}', fg=bar_color)

        # Update metrics
        if hasattr(self, '_metric_labels'):
            self._metric_labels['Status'].config(text=status, fg=bar_color)
            self._metric_labels['Chi² Score'].config(text=f'{result["chi2_score"]:,.2f}')
            self._metric_labels['P-Value'].config(text=f'{result["p_value"]:.6f}')
            self._metric_labels['Confidence'].config(text=f'{result["confidence"]*100:.2f}%')
            self._metric_labels['LSB Ratio'].config(text=f'{result["lsb_ratio"]:.6f}  (ideal: 0.5000)')
            self._metric_labels['Pixel Count'].config(text=f'{result["pixel_count"]:,}')

        # Verdict label
        if hasattr(self, '_verdict_l'):
            self._verdict_l.config(text=result['verdict'], fg=bar_color)

        # Redraw histogram using PIL rendering engine for 100% exact match with Image 2 graph
        if hasattr(self, '_hist_lbl') and self._hist_lbl.winfo_exists():
            self.update_idletasks()
            hw = max(450, self._hist_lbl.winfo_width())
            hist_img = core.render_histogram_pil(result, img_w=hw, img_h=150)
            photo = ImageTk.PhotoImage(hist_img)
            self._hist_lbl.config(image=photo)
            self._hist_lbl.image = photo

    # ════════════════════════════════════════════════════════
    # BEFORE/AFTER COMPARISON POPUP
    # ════════════════════════════════════════════════════════

    def _show_comparison(self, orig_path, stego_path):
        """Open a popup window showing original vs stego image side-by-side."""
        win = tk.Toplevel(self)
        win.title('Before / After Comparison')
        win.geometry('900x520')
        win.configure(bg=C['bg'])
        win.transient(self)

        # Header
        tk.Label(win, text='Before / After Comparison', font=get_font('title', bold=True), bg=C['bg'], fg=C['text']).pack(pady=(SP[3], SP[2]))

        # Images side by side
        img_frame = tk.Frame(win, bg=C['bg'])
        img_frame.pack(fill='both', expand=True, padx=SP[4])
        img_frame.columnconfigure(0, weight=1)
        img_frame.columnconfigure(1, weight=1)

        # Original
        orig_card = tk.Frame(img_frame, bg=C['bg_card'], padx=SP[3], pady=SP[3])
        orig_card.grid(row=0, column=0, sticky='nsew', padx=(0, SP[2]))
        tk.Label(orig_card, text='Original', font=get_font('label', bold=True), bg=C['bg_card'], fg=C['text']).pack(anchor='w')
        orig_lbl = tk.Label(orig_card, bg=C['bg_input'])
        orig_lbl.pack(fill='both', expand=True, pady=(SP[1], 0))

        # Stego
        stego_card = tk.Frame(img_frame, bg=C['bg_card'], padx=SP[3], pady=SP[3])
        stego_card.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))
        tk.Label(stego_card, text='Stego Output', font=get_font('label', bold=True), bg=C['bg_card'], fg=C['text']).pack(anchor='w')
        stego_lbl = tk.Label(stego_card, bg=C['bg_input'])
        stego_lbl.pack(fill='both', expand=True, pady=(SP[1], 0))

        # Load and display images
        try:
            for path, label in [(orig_path, orig_lbl), (stego_path, stego_lbl)]:
                with Image.open(path) as img:
                    img = img.convert('RGB')
                    img.thumbnail((380, 350))
                    photo = ImageTk.PhotoImage(img)
                    label.config(image=photo)
                    label.image = photo
        except Exception as e:
            logger.warning(f"Failed loading comparison images: {e}")

        # Metrics bar
        metrics = tk.Frame(win, bg=C['bg_card'], padx=SP[4], pady=SP[2])
        metrics.pack(fill='x', padx=SP[4], pady=(SP[2], SP[3]))

        try:
            psnr_val = core.Stego.psnr(orig_path, stego_path)
            psnr_str = f'{psnr_val:.2f} dB' if psnr_val != float('inf') else 'Perfect'

            orig_size = os.path.getsize(orig_path)
            stego_size = os.path.getsize(stego_path)

            with Image.open(orig_path) as oi:
                a = np.asarray(oi.convert('RGB'), dtype=np.int16)
            with Image.open(stego_path) as si:
                b = np.asarray(si.convert('RGB'), dtype=np.int16)
            changed = int(np.sum(a != b))
            total = a.size
            pct = (changed / total) * 100 if total > 0 else 0

            items = [
                ('PSNR', psnr_str, C['secondary']),
                ('Pixels Changed', f'{changed:,} / {total:,} ({pct:.2f}%)', C['accent']),
                ('File Size', f'{orig_size:,} → {stego_size:,} bytes', C['text_muted']),
            ]
            for label, val, clr in items:
                f = tk.Frame(metrics, bg=C['bg_card'])
                f.pack(side='left', expand=True)
                tk.Label(f, text=label, font=get_font('tiny'), bg=C['bg_card'], fg=C['text_muted']).pack()
                tk.Label(f, text=val, font=get_font('body', bold=True), bg=C['bg_card'], fg=clr).pack()
        except Exception as e:
            tk.Label(metrics, text=f'Could not compute metrics: {e}', font=get_font('caption'), bg=C['bg_card'], fg=C['warning']).pack()

    def _browse_hide_keyfile(self):
        p = filedialog.askopenfilename(title='Select Keyfile (2FA)', filetypes=[('All files', '*.*')])
        if p:
            with open(p, 'rb') as fh: self._hkeyfile_bytes = fh.read()
            self._hkeyfile_lbl.config(text=os.path.basename(p), fg=C['accent'])

    def _browse_extr_keyfile(self):
        p = filedialog.askopenfilename(title='Select Keyfile (2FA)', filetypes=[('All files', '*.*')])
        if p:
            with open(p, 'rb') as fh: self._ekeyfile_bytes = fh.read()
            self._ekeyfile_lbl.config(text=os.path.basename(p), fg=C['accent'])

    def _copy_autowipe_clipboard(self):
        txt = self._rtxt.get('1.0', tk.END).strip()
        if not txt or txt == 'Extracted content will appear here…':
            messagebox.showwarning('Nothing to Copy', 'No extracted content available.')
            return
        self.clipboard_clear()
        self.clipboard_append(txt)
        messagebox.showinfo('Clipboard Copied', 'Extracted content copied to clipboard.\n\n🔒 Clipboard will be automatically cleared in 30 seconds for security.')

        def autowipe():
            import time
            time.sleep(30)
            try:
                self.clipboard_clear()
                logger.info("Clipboard auto-wiped after 30 seconds.")
            except Exception:
                pass
        threading.Thread(target=autowipe, daemon=True).start()

    def _set_analysis_channel(self, channel_id):
        self.channel_var.set(channel_id)
        if hasattr(self, 'analyze_img') and self.analyze_img:
            self._do_analyze()

    def _export_html_report(self):
        if not hasattr(self, '_last_analysis_result') or not self._last_analysis_result:
            messagebox.showwarning('No Analysis Data', 'Please run analysis on an image first.')
            return
        out = filedialog.asksaveasfilename(title='Export HTML Forensic Report', defaultextension='.html', filetypes=[('HTML Document', '*.html')])
        if not out: return
        try:
            html = core.generate_html_report(self.analyze_img, self._last_analysis_result)
            with open(out, 'w', encoding='utf-8') as fh: fh.write(html)
            messagebox.showinfo('Report Exported', f'HTML Forensic Report exported successfully to:\n{out}')
        except Exception as e:
            messagebox.showerror('Export Failed', f'Could not export HTML report: {e}')

    def _export_pdf_report(self):
        if not hasattr(self, '_last_analysis_result') or not self._last_analysis_result:
            messagebox.showwarning('No Analysis Data', 'Please run analysis on an image first.')
            return
        out = filedialog.asksaveasfilename(title='Export PDF Forensic Report', defaultextension='.pdf', filetypes=[('PDF Document', '*.pdf')])
        if not out: return
        try:
            core.generate_pdf_report(self.analyze_img, self._last_analysis_result, out)
            messagebox.showinfo('PDF Exported', f'📕 PDF Forensic Report exported successfully with embedded histogram graph to:\n{out}')
        except Exception as e:
            messagebox.showerror('Export Failed', f'Could not export PDF report: {e}')

    # ════════════════════════════════════════════════════════
    # KEYBOARD SHORTCUT HELPERS
    # ════════════════════════════════════════════════════════

    def _shortcut_open(self):
        """Ctrl+O: open file for the current panel."""
        if self._panel == 'hide':
            self._browse_hide_img()
        elif self._panel == 'extract':
            self._browse_extr_img()
        elif self._panel == 'analyze':
            self._browse_analyze_img()


# ══════════════════════════════════════════════════════════════
# ENTRY POINT — GUI or CLI
# ══════════════════════════════════════════════════════════════
def main():
    import argparse, sys

    parser = argparse.ArgumentParser(
        prog='stegtool',
        description=f'Stegtool v{APP_VER} — Advanced Steganography Suite',
    )
    sub = parser.add_subparsers(dest='command')

    # Hide subcommand
    h = sub.add_parser('hide', help='Hide data in an image')
    h.add_argument('--image', '-i', required=True, help='Cover image path (PNG/BMP)')
    h.add_argument('--output', '-o', required=True, help='Output stego image path')
    h.add_argument('--text', '-t', help='Text to hide')
    h.add_argument('--file', '-f', help='File to hide')
    h.add_argument('--password', '-p', default='', help='Encryption password (omit for plaintext)')
    h.add_argument('--no-compress', action='store_true', help='Disable zlib compression')

    # Extract subcommand
    e = sub.add_parser('extract', help='Extract hidden data from a stego image')
    e.add_argument('--image', '-i', required=True, help='Stego image path')
    e.add_argument('--password', '-p', default='', help='Decryption password')
    e.add_argument('--output', '-o', help='Save extracted file to this path')

    # Analyze subcommand
    a = sub.add_parser('analyze', help='Run steganalysis on an image')
    a.add_argument('--image', '-i', required=True, help='Image to analyze')

    args = parser.parse_args()

    if args.command is None:
        # No CLI args — launch GUI
        StegtoolApp().mainloop()
        return

    # CLI mode
    if args.command == 'hide':
        if not args.text and not args.file:
            print('Error: provide --text or --file'); sys.exit(1)
        if args.text:
            payload = core.pack_text(args.text)
        else:
            with open(args.file, 'rb') as fh:
                payload = core.pack_file(args.file, fh.read())

        compress = not args.no_compress
        if args.password:
            ok, msg = core.Stego.hide(args.image, payload, args.password, args.output, compress=compress)
        else:
            ok, msg = core.Stego.hide_plain(args.image, payload, args.output, compress=compress)
        print(msg)
        sys.exit(0 if ok else 1)

    elif args.command == 'extract':
        ok, res = core.Stego.extract(args.image, args.password)
        if ok:
            mode, content = res
            if mode == 'text':
                print(f'[Text] {len(content):,} chars extracted')
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as fh: fh.write(content)
                    print(f'Saved to {args.output}')
                else:
                    print(content)
            else:
                fname, fdata = content
                out = args.output or fname
                with open(out, 'wb') as fh: fh.write(fdata)
                print(f'[File] "{fname}" extracted ({len(fdata):,} bytes) → {out}')
        else:
            print(f'Error: {res}')
        sys.exit(0 if ok else 1)

    elif args.command == 'analyze':
        result = core.Stego.analyze(args.image)
        if 'error' in result:
            print(f'Error: {result["error"]}'); sys.exit(1)
        print(f'Chi² Score:   {result["chi2_score"]:,.2f}')
        print(f'P-Value:      {result["p_value"]:.6f}')
        print(f'Confidence:   {result["confidence"]*100:.2f}%')
        print(f'LSB Ratio:    {result["lsb_ratio"]:.6f}  (ideal: 0.5000)')
        print(f'Pixel Count:  {result["pixel_count"]:,}')
        print(f'Verdict:      {result["verdict"]}')
        sys.exit(0)

if __name__ == '__main__':
    main()
