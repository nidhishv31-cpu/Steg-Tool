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
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt as _scrypt
import os, struct, math, threading, re
import numpy as np

# ══════════════════════════════════════════════════════════════
# HIGH-DPI SCALING ENHANCEMENT
# ══════════════════════════════════════════════════════════════
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2) # Per-monitor DPI aware (Windows 8.1+)
except Exception:
    try:
        windll.user32.SetProcessDPIAware() # Fallback for older systems
    except Exception:
        pass # Non-Windows OS fallback

# ══════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════
APP_VER   = '2.0'
DELIM     = b'<|STEGv4|>'           # version-tagged delimiter
SALT_BITS = 256                     # first 256 channels = 32-byte KDF salt (sequential)
PLAIN_HDR = b'\xCE\xFB\x04\x01'    # 4-byte magic for unencrypted mode

# ══════════════════════════════════════════════════════════════
# 8 PREMIUM MINIMALIST COLOR PRESETS
# ══════════════════════════════════════════════════════════════
PALETTES = {
    "Obsidian (Dark)": {
        'bg': '#0a0a0f', 'bg_card': '#12121e', 'bg_input': '#181829',
        'bg_hover': '#222238', 'bg_press': '#1c1c2e', 'sidebar': '#0f0f18',
        'border': '#29293f', 'border_hi': '#4f46e5',
        'accent': '#818cf8', 'accent_dk': '#6366f1',
        'secondary': '#22d3ee', 'sec_dk': '#0ea5e9',
        'danger': '#f87171', 'warning': '#fbbf24', 'success': '#34d399',
        'text': '#f1f5f9', 'text_muted': '#64748b', 'text_dim': '#94a3b8',
        's1': '#f87171', 's2': '#fb923c', 's3': '#fbbf24', 's4': '#34d399', 's5': '#22d3ee',
    },
    "Nord Ice (Dark)": {
        'bg': '#0f1722', 'bg_card': '#1a2333', 'bg_input': '#222d3f',
        'bg_hover': '#2c3b53', 'bg_press': '#243247', 'sidebar': '#141d2a',
        'border': '#33445c', 'border_hi': '#88c0d0',
        'accent': '#88c0d0', 'accent_dk': '#5e81ac',
        'secondary': '#8fbcbb', 'sec_dk': '#4c566a',
        'danger': '#bf616a', 'warning': '#ebcb8b', 'success': '#a3be8c',
        'text': '#eceff4', 'text_muted': '#6a7890', 'text_dim': '#d8dee9',
        's1': '#bf616a', 's2': '#d08770', 's3': '#ebcb8b', 's4': '#a3be8c', 's5': '#b48ead',
    },
    "Forest Edge (Dark)": {
        'bg': '#090d0b', 'bg_card': '#111814', 'bg_input': '#17221d',
        'bg_hover': '#23322b', 'bg_press': '#1c2822', 'sidebar': '#0d120f',
        'border': '#283a31', 'border_hi': '#52b788',
        'accent': '#74c69d', 'accent_dk': '#52b788',
        'secondary': '#95d5b2', 'sec_dk': '#40916c',
        'danger': '#ff8787', 'warning': '#ffd166', 'success': '#52b788',
        'text': '#edf7f4', 'text_muted': '#5c786c', 'text_dim': '#b7e4c7',
        's1': '#ff8787', 's2': '#f4a261', 's3': '#ffd166', 's4': '#52b788', 's5': '#95d5b2',
    },
    "Deep Steel (Dark)": {
        'bg': '#12161a', 'bg_card': '#1b2026', 'bg_input': '#242b33',
        'bg_hover': '#323c47', 'bg_press': '#2b333d', 'sidebar': '#171c21',
        'border': '#394452', 'border_hi': '#00bcd4',
        'accent': '#00bcd4', 'accent_dk': '#0097a7',
        'secondary': '#80deea', 'sec_dk': '#00838f',
        'danger': '#ff5252', 'warning': '#ffd740', 'success': '#69f0ae',
        'text': '#e0e6ed', 'text_muted': '#78909c', 'text_dim': '#b0bec5',
        's1': '#ff5252', 's2': '#ffab40', 's3': '#ffd740', 's4': '#69f0ae', 's5': '#80deea',
    },
    "Cyberpunk Neon (Dark)": {
        'bg': '#030008', 'bg_card': '#0d021a', 'bg_input': '#16042b',
        'bg_hover': '#250847', 'bg_press': '#1a0633', 'sidebar': '#080112',
        'border': '#3d0c75', 'border_hi': '#ff007f',
        'accent': '#ff007f', 'accent_dk': '#bc005e',
        'secondary': '#39ff14', 'sec_dk': '#20cc0a',
        'danger': '#ff0055', 'warning': '#ffff00', 'success': '#39ff14',
        'text': '#f5f0ff', 'text_muted': '#80689e', 'text_dim': '#ccb3e6',
        's1': '#ff0055', 's2': '#ff5500', 's3': '#ffff00', 's4': '#39ff14', 's5': '#00ffff',
    },
    "Rose Quartz (Light)": {
        'bg': '#f7f3f5', 'bg_card': '#ffffff', 'bg_input': '#f3ebee',
        'bg_hover': '#ebdbe2', 'bg_press': '#dfcbd4', 'sidebar': '#faf6f8',
        'border': '#d8cbd2', 'border_hi': '#d63384',
        'accent': '#d63384', 'accent_dk': '#b11e68',
        'secondary': '#6c757d', 'sec_dk': '#495057',
        'danger': '#dc3545', 'warning': '#ffc107', 'success': '#198754',
        'text': '#2b1b22', 'text_muted': '#8a747e', 'text_dim': '#5e4e56',
        's1': '#dc3545', 's2': '#fd7e14', 's3': '#ffc107', 's4': '#198754', 's5': '#20c997',
    },
    "Slate Light (Light)": {
        'bg': '#f1f5f9', 'bg_card': '#ffffff', 'bg_input': '#f8fafc',
        'bg_hover': '#e2e8f0', 'bg_press': '#cbd5e1', 'sidebar': '#f8fafc',
        'border': '#cbd5e1', 'border_hi': '#0f172a',
        'accent': '#0f172a', 'accent_dk': '#334155',
        'secondary': '#475569', 'sec_dk': '#64748b',
        'danger': '#ef4444', 'warning': '#f59e0b', 'success': '#10b981',
        'text': '#0f172a', 'text_muted': '#64748b', 'text_dim': '#334155',
        's1': '#ef4444', 's2': '#f97316', 's3': '#f59e0b', 's4': '#10b981', 's5': '#475569',
    },
    "Sepia Warmth (Light)": {
        'bg': '#f4efe6', 'bg_card': '#faf8f5', 'bg_input': '#ebe4d5',
        'bg_hover': '#dfd6c4', 'bg_press': '#cfc2ad', 'sidebar': '#f0eae0',
        'border': '#d3c7b1', 'border_hi': '#8c6239',
        'accent': '#8c6239', 'accent_dk': '#5c3f21',
        'secondary': '#7f8c8d', 'sec_dk': '#5d6d7e',
        'danger': '#c0392b', 'warning': '#f39c12', 'success': '#27ae60',
        'text': '#332a21', 'text_muted': '#8a7f72', 'text_dim': '#5e544a',
        's1': '#c0392b', 's2': '#d35400', 's3': '#f39c12', 's4': '#27ae60', 's5': '#2980b9',
    }
}

# Mutable state values loaded from Obsidian theme by default
C = dict(PALETTES["Obsidian (Dark)"])

SP = {1:4, 2:8, 3:12, 4:16, 5:20, 6:24, 8:32}

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

# ══════════════════════════════════════════════════════════════
# CRYPTO & UTILS (SCRYPT KDF / AES-GCM)
# ══════════════════════════════════════════════════════════════
def pw_strength(pw):
    if not pw: return 0, '', 'border'
    s  = (len(pw)>=8) + (len(pw)>=12)
    s += bool(re.search(r'[A-Z]',pw) and re.search(r'[a-z]',pw))
    s += bool(re.search(r'\d',pw))
    s += bool(re.search(r'[^a-zA-Z0-9]',pw))
    return s, ['','Weak','Fair','Good','Strong','Very Strong'][s], \
              ['border','s1','s2','s3','s4','s5'][s]

class KDF:
    SALT_LEN = 32
    _N, _r, _p = 2**17, 8, 1
    @classmethod
    def derive(cls, pw: str, salt: bytes):
        km = _scrypt(pw.encode(), salt, key_len=64, N=cls._N, r=cls._r, p=cls._p)
        return km[:32], int.from_bytes(km[32:40], 'big')

class AESGCM:
    NONCE, TAG = 12, 16
    @classmethod
    def encrypt(cls, plain, key):
        nonce = os.urandom(cls.NONCE)
        ct, tag = AES.new(key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(plain)
        return nonce + tag + ct
    @classmethod
    def decrypt(cls, data, key):
        if len(data) < cls.NONCE + cls.TAG: raise ValueError('Blob too short')
        n, t = cls.NONCE, cls.TAG
        return AES.new(key, AES.MODE_GCM, nonce=data[:n]).decrypt_and_verify(data[n+t:], data[n:n+t])

_MT = b'\x01';  _MF = b'\x02'
def pack_text(text): return _MT + text.encode('utf-8')
def pack_file(path, data):
    fn = os.path.basename(path).encode('utf-8')
    return _MF + struct.pack('>H', len(fn)) + fn + data
def unpack(plain):
    if not plain: raise ValueError('Empty payload')
    m, r = plain[:1], plain[1:]
    if m == _MT: return 'text', r.decode('utf-8')
    if m == _MF:
        fl = struct.unpack('>H', r[:2])[0]
        return 'file', (r[2:2+fl].decode('utf-8'), r[2+fl:])
    raise ValueError(f'Unknown mode byte {m!r}')

def _lsb_match(arr: np.ndarray, indices: np.ndarray, bits: np.ndarray, seed: int):
    vals = arr[indices].astype(np.int32)
    miss = (vals & 1) != bits.astype(np.int32)
    if not np.any(miss): return
    rng  = np.random.default_rng(seed)
    n    = int(miss.sum())
    d    = np.where(rng.integers(0, 2, n) == 0, 1, -1)
    mv   = vals[miss]
    d    = np.where(mv ==   0,  1, d)
    d    = np.where(mv == 255, -1, d)
    arr[indices[miss]] = np.clip(mv + d, 0, 255).astype(np.uint8)

class Stego:
    @staticmethod
    def _scatter(seed: int, n: int) -> np.ndarray:
        return np.random.default_rng(seed).permutation(n).astype(np.int64)

    @staticmethod
    def capacity(path: str, encrypted: bool = True) -> int:
        try:
            img = Image.open(path).convert('RGB')
            N = img.size[0] * img.size[1] * 3
            if encrypted:
                sn = max(0, N - SALT_BITS)
                oh = 4 + AESGCM.NONCE + AESGCM.TAG + len(DELIM)
                return max(0, sn // 8 - oh)
            else:
                oh = len(PLAIN_HDR) + 4 + len(DELIM)
                return max(0, N // 8 - oh)
        except Exception: return 0

    @staticmethod
    def estimate_psnr(path: str, size_bytes: int) -> float:
        try:
            img = Image.open(path).convert('RGB')
            N   = img.size[0] * img.size[1] * 3
            mse = (size_bytes * 8 / N) * 0.25
            return 10 * math.log10(255**2 / mse) if mse > 0 else float('inf')
        except Exception: return 0.0

    @staticmethod
    def psnr(orig: str, stego: str) -> float:
        try:
            a = np.asarray(Image.open(orig).convert('RGB'),  dtype=np.float64)
            b = np.asarray(Image.open(stego).convert('RGB'), dtype=np.float64)
            mse = np.mean((a - b) ** 2)
            return float('inf') if mse == 0 else 10 * math.log10(255**2 / mse)
        except Exception: return 0.0

    @classmethod
    def hide(cls, img_path, plain, pw, out, cb=None):
        try:
            img = Image.open(img_path).convert('RGB')
            arr = np.asarray(img, dtype=np.uint8).ravel().copy()
            N   = len(arr)
            if N <= SALT_BITS: return False, 'Image too small.'
            sn = N - SALT_BITS
            if cb: cb(0.02)
            salt = os.urandom(KDF.SALT_LEN)
            aes_key, seed = KDF.derive(pw, salt)
            if cb: cb(0.25)
            enc  = AESGCM.encrypt(plain, aes_key)
            wire = struct.pack('>I', len(enc)) + enc + DELIM
            wb   = np.unpackbits(np.frombuffer(wire, dtype=np.uint8))
            nb   = len(wb)
            if nb > sn: return False, f'Too large: needs {nb//8:,} B, holds {sn//8:,} B.'
            if cb: cb(0.36)
            sb = np.unpackbits(np.frombuffer(salt, dtype=np.uint8))
            _lsb_match(arr, np.arange(SALT_BITS, dtype=np.int64), sb, int.from_bytes(os.urandom(8), 'big'))
            if cb: cb(0.46)
            sc = cls._scatter(seed, sn)[:nb] + SALT_BITS
            _lsb_match(arr, sc, wb, seed ^ 0xCAFE_BABE)
            if cb: cb(0.87)
            Image.fromarray(arr.reshape(img.size[1], img.size[0], 3), 'RGB').save(out)
            if cb: cb(1.0)
            return True, f'Hidden {len(plain):,} bytes (encrypted)'
        except MemoryError: return False, 'Insufficient memory — try a smaller image.'
        except OSError as e: return False, f'File error: {e}'
        except Exception as e: return False, f'Embedding failed: {e}'

    @classmethod
    def hide_plain(cls, img_path, plain, out, cb=None):
        try:
            img = Image.open(img_path).convert('RGB')
            arr = np.asarray(img, dtype=np.uint8).ravel().copy()
            N   = len(arr)
            wire = PLAIN_HDR + struct.pack('>I', len(plain)) + plain + DELIM
            wb   = np.unpackbits(np.frombuffer(wire, dtype=np.uint8))
            nb   = len(wb)
            if nb > N: return False, f'Too large: needs {nb//8:,} B, holds {N//8:,} B.'
            if cb: cb(0.10)
            _lsb_match(arr, np.arange(nb, dtype=np.int64), wb, int.from_bytes(os.urandom(8), 'big'))
            if cb: cb(0.85)
            Image.fromarray(arr.reshape(img.size[1], img.size[0], 3), 'RGB').save(out)
            if cb: cb(1.0)
            return True, f'Hidden {len(plain):,} bytes (plain)'
        except Exception as e: return False, f'Embedding failed: {e}'

    @classmethod
    def extract(cls, img_path, pw=''):
        try:
            img = Image.open(img_path).convert('RGB')
            arr = np.asarray(img, dtype=np.uint8).ravel()
            N   = len(arr)
            # Try plain
            hb = len(PLAIN_HDR) * 8
            if N >= hb + 32:
                magic = bytes(np.packbits((arr[:hb] & 1).astype(np.uint8)))
                if magic == PLAIN_HDR:
                    try:
                        plen = struct.unpack('>I', bytes(np.packbits((arr[hb:hb+32] & 1).astype(np.uint8))))[0]
                    except struct.error: plen = 0
                    if 0 < plen <= N // 8:
                        ps = hb + 32
                        nb = plen * 8 + len(DELIM) * 8
                        if ps + nb <= N:
                            pb = np.packbits((arr[ps:ps+nb] & 1).astype(np.uint8))
                            if bytes(pb[plen:plen+len(DELIM)]) == DELIM:
                                return True, unpack(bytes(pb[:plen]))

            # Try encrypted
            if not pw: return False, 'No password provided. If unencrypted, headers are missing or corrupted.'
            if N <= SALT_BITS: return False, 'Image too small.'
            sn = N - SALT_BITS
            salt    = bytes(np.packbits((arr[:SALT_BITS] & 1).astype(np.uint8)))
            aes_key, seed = KDF.derive(pw, salt)
            sc      = cls._scatter(seed, sn)
            if len(sc) < 32: return False, 'Image too small.'
            try: enc_len = struct.unpack('>I', bytes(np.packbits((arr[sc[:32]+SALT_BITS] & 1).astype(np.uint8))))[0]
            except struct.error: return False, 'Corrupted stego data.'
            if enc_len == 0 or enc_len > sn // 8 or enc_len > 200_000_000: return False, 'Wrong password or empty.'
            nb  = enc_len * 8 + len(DELIM) * 8
            if 32 + nb > len(sc): return False, 'Corrupted data.'
            pb   = np.packbits((arr[sc[32:32+nb]+SALT_BITS] & 1).astype(np.uint8))
            blob = bytes(pb[:enc_len])
            if bytes(pb[enc_len:enc_len+len(DELIM)]) != DELIM: return False, 'Wrong password or empty.'
            try: plain = AESGCM.decrypt(blob, aes_key)
            except ValueError: return False, 'Wrong password or GCM verification failed.'
            return True, unpack(plain)
        except Exception as e: return False, f'Extraction failed: {e}'

# ══════════════════════════════════════════════════════════════
# CUSTOM WINDOWS/THEMED WIDGETS
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
        super().__init__(parent, text=text, command=cmd, font=get_font('body'),
                         bg=bg, fg=fg, activebackground=hbg, activeforeground=fg,
                         relief='flat', padx=SP[4], pady=6,
                         cursor='hand2', highlightthickness=0, borderwidth=0, **kw)
        self.bind('<Enter>',           lambda _: self.config(bg=hbg))
        self.bind('<Leave>',           lambda _: self.config(bg=bg))
        self.bind('<Button-1>',        lambda _: self.config(bg=pbg))
        self.bind('<ButtonRelease-1>', lambda _: self.config(bg=hbg))

class DropZone(tk.Frame):
    _DEF = 'Drag & drop image here\\nor click  Browse'
    def __init__(self, parent, on_click=None, **kw):
        super().__init__(parent, bg=C['bg_input'], highlightbackground=C['border'], highlightthickness=1, relief='flat', **kw)
        self._base = C['border'];  self._hi = C['accent']
        self._ico = tk.Label(self, text='⬆', font=get_font('display'), bg=C['bg_input'], fg=C['text_dim'])
        self._ico.pack(pady=(SP[3], SP[1]))
        self._lbl = tk.Label(self, text=self._DEF, font=get_font('caption'), bg=C['bg_input'], fg=C['text_muted'], justify='center')
        self._lbl.pack(pady=(0, SP[3]))
        if on_click:
            for w in (self, self._ico, self._lbl):
                w.bind('<Button-1>', lambda _: on_click())
                w.configure(cursor='hand2')
    def highlight(self, on): self.config(highlightbackground=self._hi if on else self._base)
    def set_file(self, name):
        self._ico.config(text='◉', fg=C['secondary'])
        self._lbl.config(text=f'✓  {name}', fg=C['secondary'])
    def reset(self):
        self._ico.config(text='⬆', fg=C['text_dim'])
        self._lbl.config(text=self._DEF, fg=C['text_muted'])

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

        # Persistent stego states
        self._panel     = 'hide'
        self.hide_img   = ''
        self.extr_img   = ''
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

        self._build()
        self._center()

    def _on_drop(self, event):
        path = self._parse_dnd(event.data)
        if not os.path.isfile(path): return
        (self._on_hide_drop if self._panel == 'hide' else self._on_extr_drop)(path)
        self._drag_reset()

    @staticmethod
    def _parse_dnd(data):
        raw = data.strip()
        p   = raw[1:raw.find('}')] if raw.startswith('{') else raw.split()[0]
        return p.replace('/', '\\')

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
        if hasattr(self, '_hpw'):    s['h_pw']  = self._hpw.get()
        if hasattr(self, '_hpw2'):   s['h_pw2'] = self._hpw2.get()
        if hasattr(self, '_secret'): s['h_txt'] = self._secret.get('1.0', tk.END)
        if hasattr(self, '_epw'):    s['e_pw']  = self._epw.get()
        s['encrypt'] = self._enc_var.get()
        self._snap   = s

    def _restore(self):
        s = self._snap
        if 'encrypt' in s: self._enc_var.set(s['encrypt'])
        if hasattr(self, '_hpw'):
            if s.get('h_pw'):  self._hpw.insert(0, s['h_pw'])
            if s.get('h_pw2'): self._hpw2.insert(0, s['h_pw2'])
            if s.get('h_txt','').strip(): self._secret.insert('1.0', s['h_txt'].strip())
            self._upd_strength()
            self._chk_match()
        if hasattr(self, '_epw') and s.get('e_pw'): self._epw.insert(0, s['e_pw'])

        # Restore images
        if self.hide_img and hasattr(self, '_hdrop'):
            self._hdrop.set_file(os.path.basename(self.hide_img))
            self._load_prev(self.hide_img, self._hprev)
            self._upd_cap()
            if os.path.splitext(self.hide_img)[1].lower() in ('.jpg', '.jpeg'):
                self._jpeg_w.pack(anchor='w', pady=(0, SP[1]))
        if self.extr_img and hasattr(self, '_edrop'):
            self._edrop.set_file(os.path.basename(self.extr_img))
            self._load_prev(self.extr_img, self._eprev)
        if self.hide_file and hasattr(self, '_flbl') and os.path.exists(self.hide_file):
            sz = os.path.getsize(self.hide_file)
            self._flbl.config(text=f'{os.path.basename(self.hide_file)}  ({sz:,} B)', fg=C['text'])

        if hasattr(self, '_on_enc_change'): self._on_enc_change(init=True)

    # ─── Customize Modal Panel ────────────────────────────────

    def _open_customize_modal(self):
        """Creates an independent customizable modal dialog window."""
        modal = tk.Toplevel(self)
        modal.title("Customize Theme & Fonts")
        modal.geometry("380x420")
        modal.resizable(False, False)
        modal.configure(bg=C['bg_card'])
        modal.transient(self)
        modal.grab_set()

        # Center relative to parent
        self.update_idletasks()
        rx, ry = self.winfo_rootx(), self.winfo_rooty()
        rw, rh = self.winfo_width(), self.winfo_height()
        modal.geometry(f"+{rx + (rw-380)//2}+{ry + (rh-420)//2}")

        pad = SP[4]
        frame = tk.Frame(modal, bg=C['bg_card'], padx=pad, pady=pad)
        frame.pack(fill='both', expand=True)

        tk.Label(frame, text="Customize Workspace", font=get_font('title', bold=True),
                 bg=C['bg_card'], fg=C['text']).pack(anchor='w', pady=(0, SP[4]))

        # Style themes
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Modal.TCombobox", 
                         fieldbackground=C['bg_input'],
                         background=C['bg_card'],
                         foreground=C['text'],
                         arrowcolor=C['text_dim'])

        # Themes
        tk.Label(frame, text="Color Palette Presets", font=get_font('label'),
                 bg=C['bg_card'], fg=C['text_dim']).pack(anchor='w', pady=(SP[2], 2))
        combo_theme = ttk.Combobox(frame, textvariable=self.theme_var, values=list(PALETTES.keys()), 
                                   state="readonly", style="Modal.TCombobox")
        combo_theme.pack(fill='x', pady=(0, SP[3]))

        # Font family
        tk.Label(frame, text="Font Family", font=get_font('label'),
                 bg=C['bg_card'], fg=C['text_dim']).pack(anchor='w', pady=(SP[2], 2))
        combo_font = ttk.Combobox(frame, textvariable=self.font_var, 
                                  values=["Segoe UI", "Arial", "Consolas", "Courier New", "Verdana"], 
                                  state="readonly", style="Modal.TCombobox")
        combo_font.pack(fill='x', pady=(0, SP[3]))

        # Sizing scale
        tk.Label(frame, text="Font Scale", font=get_font('label'),
                 bg=C['bg_card'], fg=C['text_dim']).pack(anchor='w', pady=(SP[2], 2))
        combo_size = ttk.Combobox(frame, textvariable=self.size_var, 
                                  values=["Small", "Normal", "Large", "Huge"], 
                                  state="readonly", style="Modal.TCombobox")
        combo_size.pack(fill='x', pady=(0, SP[3]))

        # Action Buttons
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
            
            self._snapshot()
            self._build()
            self._restore()
            modal.destroy()

        self._sep(frame, pady=SP[4])
        
        btn_box = tk.Frame(frame, bg=C['bg_card'])
        btn_box.pack(fill='x', side='bottom')
        
        Btn(btn_box, "Apply Settings", apply_changes, 'success').pack(side='right')
        Btn(btn_box, "Cancel", modal.destroy, 'ghost').pack(side='right', padx=(0, SP[2]))

    # ─── Build Sidebar and Main ──────────────────────────────

    def _build(self):
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
        logo.pack(fill='x', pady=(SP[6], SP[3]))
        tk.Label(logo, text='◈', font=get_font('display'), bg=C['sidebar'], fg=C['accent']).pack()
        tk.Label(logo, text='Stegtool', font=get_font('display', bold=True), bg=C['sidebar'], fg=C['text']).pack()
        tk.Label(logo, text=f'v{APP_VER}', font=get_font('tiny'), bg=C['sidebar'], fg=C['accent']).pack(pady=(0, SP[4]))

        tk.Frame(sb, bg=C['border'], height=1).pack(fill='x', padx=SP[4])

        # Navigation
        nav = tk.Frame(sb, bg=C['sidebar'])
        nav.pack(fill='x', padx=SP[2], pady=SP[2])
        self._nb_h = self._mknav(nav, '⬆  Hide Data',    self._show_hide)
        self._nb_e = self._mknav(nav, '⬇  Extract Data', self._show_extr)
        self._nb_c = self._mknav(nav, '⚙  Customize',    self._open_customize_modal) # Launches Popup Window
        
        self._nb_h.pack(fill='x', pady=SP[1])
        self._nb_e.pack(fill='x', pady=SP[1])
        self._nb_c.pack(fill='x', pady=SP[1])

        # Footer
        tk.Label(sb, text='AES-256-GCM · scrypt KDF', font=get_font('tiny'), bg=C['sidebar'], fg=C['text_muted']).pack(side='bottom', pady=SP[3])

        # ── Content Panel ────────────────────────────────────
        self.content = tk.Frame(root, bg=C['bg'])
        self.content.pack(side='right', fill='both', expand=True, padx=SP[4], pady=SP[4])

        self._show_hide()

    def _mknav(self, parent, text, cmd):
        f = tk.Frame(parent, bg=C['sidebar'])
        f._active = False
        ind = tk.Frame(f, bg=C['sidebar'], width=3)
        ind.pack(side='left', fill='y')
        lbl = tk.Label(f, text=text, font=get_font('body'), bg=C['sidebar'], fg=C['text_muted'], padx=SP[3], pady=SP[2], cursor='hand2', anchor='w')
        lbl.pack(side='left', fill='x', expand=True)
        f._ind = ind;  f._lbl = lbl

        def click(_=None): cmd()
        def hover(_=None):
            if not f._active:
                f.config(bg=C['bg_hover']); lbl.config(bg=C['bg_hover'], fg=C['text'])
                ind.config(bg=C['bg_hover'])
        def leave(_=None):
            if not f._active:
                f.config(bg=C['sidebar']); lbl.config(bg=C['sidebar'], fg=C['text_muted'])
                ind.config(bg=C['sidebar'])

        for w in (f, lbl): w.bind('<Button-1>', click); w.bind('<Enter>', hover); w.bind('<Leave>', leave)
        return f

    def _set_nav(self, active):
        for f in (self._nb_h, self._nb_e, self._nb_c):
            f._active = False
            f.config(bg=C['sidebar']); f._lbl.config(bg=C['sidebar'], fg=C['text_muted'])
            f._ind.config(bg=C['sidebar'])
        # Highlight target
        active._active = True
        active.config(bg=C['bg_hover']); active._lbl.config(bg=C['bg_hover'], fg=C['text'])
        active._ind.config(bg=C['accent'])

    def _clr(self):
        for w in self.content.winfo_children(): w.destroy()

    # ════════════════════════════════════════════════════════
    # HIDE PANEL
    # ════════════════════════════════════════════════════════

    def _show_hide(self):
        self._panel = 'hide'
        self._clr()
        self._set_nav(self._nb_h)

        tk.Label(self.content, text='Hide Data', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(anchor='w', pady=(0, SP[3]))

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

        self._plain_note = tk.Frame(Lc, bg=C['bg_card'])
        tk.Label(self._plain_note, text='⚠  No encryption — anyone with Stegtool can extract\n    the hidden content without a password.', font=get_font('caption'), bg=C['bg_card'], fg=C['warning'], justify='left', wraplength=200).pack(anchor='w', pady=(SP[1], 0))

        self._on_enc_change(init=True)

        # ── Right Card ───────────────────────────────────────
        Rc = self._card(g)
        Rc.grid(row=0, column=1, sticky='nsew', padx=(SP[2], 0))

        mf = tk.Frame(Rc, bg=C['bg_card'])
        mf.pack(fill='x', pady=(0, SP[3]))
        self._lbl(mf, 'Data Type:', font_key='label').pack(side='left')
        for val, txt in [('text', '  Text'), ('file', '  File')]:
            ttk.Radiobutton(mf, text=txt, variable=self.mode_var, value=val, command=self._toggle_mode).pack(side='left', padx=(SP[2], 0))

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

        self._toggle_mode()

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
        self._lbl(parent, 'Password:', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[3], SP[1]))
        self._hpw = self._mk_entry(parent, show='*')
        self._hpw.pack(fill='x', ipady=5)
        self._hpw.bind('<KeyRelease>', lambda _: self._upd_strength())

        self._str_c = tk.Canvas(parent, height=4, bg=C['bg_input'], highlightthickness=0)
        self._str_c.pack(fill='x', pady=(2, 0))
        self._str_l = self._lbl(parent, '', font_key='tiny', fg=C['text_muted'])
        self._str_l.pack(anchor='e')

        self._lbl(parent, 'Confirm:', font_key='caption', fg=C['text_muted']).pack(anchor='w', pady=(SP[2], SP[1]))
        self._hpw2 = self._mk_entry(parent, show='*')
        self._hpw2.pack(fill='x', ipady=5)
        self._hpw2.bind('<KeyRelease>', lambda _: self._chk_match())

        self._pmatch = self._lbl(parent, '', font_key='tiny', fg=C['text_muted'])
        self._pmatch.pack(anchor='w', pady=(2, 0))

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
            ep = Stego.estimate_psnr(self.hide_img, size)
            if ep == float('inf'): self._est_l.config(text='Est. PSNR: Perfect', fg=C['success'])
            elif ep > 40: self._est_l.config(text=f'Est. PSNR: ~{ep:.1f} dB  ✓', fg=C['secondary'])
            else: self._est_l.config(text=f'Est. PSNR: ~{ep:.1f} dB  ⚠', fg=C['warning'])
        except Exception: pass

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

    def _load_prev(self, path, lbl, mx=(255, 155)):
        try:
            img = Image.open(path); img.thumbnail(mx)
            ph  = ImageTk.PhotoImage(img)
            lbl.config(image=ph, text=''); lbl.image = ph
        except Exception: lbl.config(image='', text='Preview unavailable')

    def _upd_cap(self):
        if not self.hide_img: return
        enc = self._enc_var.get() if hasattr(self, '_enc_var') else True
        cap = Stego.capacity(self.hide_img, encrypted=enc)
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

        if self.mode_var.get() == 'text':
            txt = self._secret.get('1.0', tk.END).strip()
            if not txt: messagebox.showwarning('Empty', 'Please enter a secret message.'); return
            plain = pack_text(txt)
        else:
            if not self.hide_file or not os.path.exists(self.hide_file): messagebox.showwarning('No File', 'Please select a file to hide.'); return
            with open(self.hide_file, 'rb') as fh: plain = pack_file(self.hide_file, fh.read())

        cap = Stego.capacity(self.hide_img, encrypted=encrypt)
        if len(plain) > cap: messagebox.showerror('Too Large', f'Data is {len(plain):,} B but image holds only {cap:,} B.'); return

        out = filedialog.asksaveasfilename(title='Save Stego Image', defaultextension='.png', filetypes=[('PNG','*.png'),('BMP','*.bmp')])
        if not out: return

        self._hbtn.config(state='disabled', text='Working…')
        self._going = True; self._prog = 0.0
        self._poll()
        self.update()

        def work():
            def cb(v): self._prog = v
            if encrypt: ok, msg = Stego.hide(self.hide_img, plain, pw, out, cb)
            else: ok, msg = Stego.hide_plain(self.hide_img, plain, out, cb)
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
            p  = Stego.psnr(self.hide_img, out)
            pt = f'PSNR: {p:.2f} dB' if p != float('inf') else 'PSNR: Perfect'
            self._hstat.config(text=f'{msg}  ·  {pt}', fg=C['success'])
            Toast(self, f'{msg}', kind='success')
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

        tk.Label(self.content, text='Extract Data', font=get_font('display', bold=True), bg=C['bg'], fg=C['text']).pack(anchor='w', pady=(0, SP[3]))

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

        self._lbl(Lc, 'Leave blank for unencrypted images', font_key='tiny', fg=C['text_muted']).pack(anchor='w', pady=(2, SP[3]))

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
        Btn(self._sf, '⬇  Save as File', self._save_extr, 'primary').pack(side='left')
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
        self._estat.config(text='Extracting…  (if encrypted, deriving keys takes ~1s)', fg=C['warning'])
        self.update()
        def work():
            ok, res = Stego.extract(self.extr_img, pw)
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


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main():
    StegtoolApp().mainloop()

if __name__ == '__main__':
    main()
