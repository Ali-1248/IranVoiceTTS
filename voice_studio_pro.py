"""
AI Voice Studio Pro  v3.0
─────────────────────────
fixes:
  • inline rename dialog (no ugly OS popup)
  • playback-end polling → row resets automatically when audio finishes
  • surgical row updates → no full list rebuild on play/pause/rename/delete
  • full-rebuild only when: file count changes, search query changes, lang/theme switch
"""

import customtkinter as ctk
import requests
import threading
import pygame
import os, sys, time
import subprocess
import tkinter.font as tkfont

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
VOICE_DIR   = "voices"
API_URL     = "https://ai.igap.net/api/v1/voice/tts/"
API_TOKEN   = "Bearer 18qNMvTdL8PRYVIOSgJkktycBgMH3Y"
APP_VERSION = "3.0"
FONT_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Lalezar-Regular.ttf")

os.makedirs(VOICE_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
#  THEMES
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "Dark": {
        "bg":        "#0d0d14",
        "surface":   "#1a1a2e",
        "surface2":  "#20203a",
        "border":    "#2a2a45",
        "accent":    "#7c6af7",
        "accent2":   "#5b4fcf",
        "success":   "#22c55e",
        "danger":    "#f43f5e",
        "warning":   "#f59e0b",
        "blue":      "#38bdf8",
        "text":      "#f1f0ff",
        "text2":     "#a09dc0",
        "text3":     "#5a5780",
        "header_bg": "#0f0f1a",
        "scrollbar": "#2a2a45",
        "del_bg":    "#2d1520",
        "input_bg":  "#12121e",
        "overlay":   "#0d0d14cc",
    },
    "Light": {
        "bg":        "#f0eeff",
        "surface":   "#ffffff",
        "surface2":  "#f4f2ff",
        "border":    "#d4cff5",
        "accent":    "#6d54f0",
        "accent2":   "#5540d0",
        "success":   "#16a34a",
        "danger":    "#e11d48",
        "warning":   "#d97706",
        "blue":      "#0284c7",
        "text":      "#1a1535",
        "text2":     "#5b5380",
        "text3":     "#9d9abf",
        "header_bg": "#e8e4ff",
        "scrollbar": "#c4bff0",
        "del_bg":    "#fff0f3",
        "input_bg":  "#f8f6ff",
        "overlay":   "#f0eeffcc",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  LANGUAGE
# ─────────────────────────────────────────────────────────────────────────────
LANG = {
    "fa": {
        "title":        "استودیو صوت هوشمند",
        "subtitle":     f"نسخه {APP_VERSION}",
        "input_label":  "متن برای تبدیل به صدا",
        "btn_gen":      "▶  ساخت صدا",
        "btn_clear":    "پاک کردن",
        "history":      "تاریخچه صداها",
        "no_files":     "هنوز فایلی ساخته نشده",
        "search_ph":    "جستجو در فایل‌ها...",
        "volume":       "حجم صدا",
        "chars":        "حرف",
        "generating":   "⏳  در حال ساخت...",
        "rename":       "✏️",
        "rename_title": "تغییر نام فایل",
        "rename_ph":    "نام جدید را وارد کنید...",
        "rename_ok":    "ذخیره",
        "rename_cancel":"لغو",
        "delete":       "✕",
        "folder":       "📁",
        "ask_del":      "آیا از حذف این فایل مطمئن هستید؟",
        "delete_confirm":"بله، حذف کن",
        "ok":           "✓  ویس با موفقیت ساخته شد",
        "err":          "خطا در ارتباط با سرور",
        "err_empty":    "⚠  متن خالی است!",
        "err_timeout":  "زمان اتصال به پایان رسید",
        "deleted":      "✓  فایل حذف شد",
        "renamed":      "✓  نام فایل تغییر کرد",
        "export_all":   "باز کردن پوشه",
        "lang_switch":  "EN",
    },
    "en": {
        "title":        "AI Voice Studio",
        "subtitle":     f"v{APP_VERSION}",
        "input_label":  "Text to Speech",
        "btn_gen":      "▶  Generate Voice",
        "btn_clear":    "Clear",
        "history":      "Voice History",
        "no_files":     "No voices yet — generate your first!",
        "search_ph":    "Search files...",
        "volume":       "Volume",
        "chars":        "chars",
        "generating":   "⏳  Generating...",
        "rename":       "✏️",
        "rename_title": "Rename File",
        "rename_ph":    "Enter new name...",
        "rename_ok":    "Save",
        "rename_cancel":"Cancel",
        "delete":       "✕",
        "folder":       "📁",
        "ask_del":      "Are you sure you want to delete this file?",
        "delete_confirm":"Yes, Delete",
        "ok":           "✓  Voice generated successfully",
        "err":          "Server connection error",
        "err_empty":    "⚠  Text field is empty!",
        "err_timeout":  "Connection timed out",
        "deleted":      "✓  File deleted",
        "renamed":      "✓  File renamed",
        "export_all":   "Open Folder",
        "lang_switch":  "FA",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
#  FONT
# ─────────────────────────────────────────────────────────────────────────────
def load_lalezar():
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.gdi32.AddFontResourceExW(FONT_PATH, 0x10, 0)
        elif sys.platform == "linux":
            d = os.path.expanduser("~/.fonts")
            os.makedirs(d, exist_ok=True)
            dst = os.path.join(d, "Lalezar-Regular.ttf")
            if not os.path.exists(dst):
                import shutil; shutil.copy(FONT_PATH, dst)
                subprocess.run(["fc-cache", "-f"], capture_output=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  INLINE RENAME DIALOG  (CTkToplevel, themed)
# ─────────────────────────────────────────────────────────────────────────────
class DeleteDialog(ctk.CTkToplevel):
    """Themed confirmation dialog for delete — no ugly OS popup."""

    def __init__(self, parent, filename: str, T: dict, C: dict, fn: str):
        super().__init__(parent)
        self.confirmed = False

        self.title(T["delete"])
        self.geometry("380x190")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.grab_set()
        self.focus_set()

        # Center over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - 190
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 95
        self.geometry(f"+{px}+{py}")

        # Header
        hdr = ctk.CTkFrame(self, fg_color=C["danger"], corner_radius=0, height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"🗑  {T['delete']}",
                     font=(fn, 14, "bold"), text_color="#fff"
                     ).pack(side="left", padx=18, pady=10)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        name = os.path.splitext(filename)[0]
        ctk.CTkLabel(
            body,
            text=f"{T['ask_del']}\n「{name}」",
            font=(fn, 13), text_color=C["text"],
            wraplength=330, justify="center"
        ).pack(pady=(0, 16))

        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text=T["rename_cancel"],
            height=40, corner_radius=11,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=(fn, 13), text_color=C["text2"],
            command=self.destroy
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            btn_row, text=T["delete_confirm"],
            height=40, corner_radius=11,
            fg_color=C["danger"], hover_color="#c0192f",
            font=(fn, 13, "bold"), text_color="#fff",
            command=self._confirm
        ).pack(side="left", fill="x", expand=True)

        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self.destroy())

    def _confirm(self):
        self.confirmed = True
        self.destroy()


class RenameDialog(ctk.CTkToplevel):
    """Sleek themed rename dialog — returns new name via .result."""

    def __init__(self, parent, current_name: str, T: dict, C: dict, fn: str):
        super().__init__(parent)
        self.result = None
        self.T = T
        self.C = C
        self.fn = fn

        # Window setup
        self.title(T["rename_title"])
        self.geometry("420x210")
        self.resizable(False, False)
        self.configure(fg_color=C["bg"])
        self.grab_set()                      # modal
        self.focus_set()

        # Center over parent
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width()  // 2 - 210
        py = parent.winfo_rooty() + parent.winfo_height() // 2 - 105
        self.geometry(f"+{px}+{py}")

        self._build(current_name)
        self.bind("<Return>",  lambda e: self._save())
        self.bind("<Escape>",  lambda e: self._cancel())

    def _build(self, current_name: str):
        C, T, fn = self.C, self.T, self.fn

        # Title bar area
        hdr = ctk.CTkFrame(self, fg_color=C["header_bg"], corner_radius=0, height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"✏  {T['rename_title']}",
                     font=(fn, 14, "bold"), text_color=C["text"]
                     ).pack(side="left", padx=18, pady=10)

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Strip .mp3 for display
        display = current_name[:-4] if current_name.endswith(".mp3") else current_name

        self.entry = ctk.CTkEntry(
            body,
            font=(fn, 14),
            height=44,
            corner_radius=12,
            fg_color=C["input_bg"],
            border_color=C["accent"],
            border_width=2,
            text_color=C["text"],
            placeholder_text=T["rename_ph"],
            placeholder_text_color=C["text3"],
        )
        self.entry.pack(fill="x", pady=(0, 14))
        self.entry.insert(0, display)
        self.entry.select_range(0, "end")
        self.entry.focus()

        # Buttons
        btn_row = ctk.CTkFrame(body, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text=T["rename_cancel"],
            height=40, corner_radius=11,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=(fn, 13), text_color=C["text2"],
            command=self._cancel
        ).pack(side="left", padx=(0, 10), fill="x", expand=True)

        ctk.CTkButton(
            btn_row, text=T["rename_ok"],
            height=40, corner_radius=11,
            fg_color=C["accent"], hover_color=C["accent2"],
            font=(fn, 13, "bold"), text_color="#fff",
            command=self._save
        ).pack(side="left", fill="x", expand=True)

    def _save(self):
        val = self.entry.get().strip()
        if val:
            self.result = val if val.endswith(".mp3") else val + ".mp3"
        self.destroy()

    def _cancel(self):
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  ROW WIDGET  (self-contained, surgically updatable)
# ─────────────────────────────────────────────────────────────────────────────
class VoiceRow(ctk.CTkFrame):
    """One history row — can update its own play-state without list rebuild."""

    def __init__(self, master, idx: int, filename: str, app: "VoiceStudio"):
        C = app.C
        super().__init__(
            master,
            fg_color=C["surface"],
            corner_radius=16,
            border_width=1,
            border_color=C["border"])
        self.grid_columnconfigure(1, weight=1)

        self.app       = app
        self.filename  = filename
        self.idx       = idx

        self._build(idx, filename)

    # ── build internal layout ─────────────────────────────────────────────────
    def _build(self, idx: int, filename: str):
        app  = self.app
        C, T = app.C, app.T
        fn   = app.fn
        path = os.path.join(VOICE_DIR, filename)

        # Badge
        self._badge = ctk.CTkFrame(
            self, fg_color=C["surface2"],
            corner_radius=10, width=38, height=38)
        self._badge.grid(row=0, column=0, padx=(14, 10), pady=14)
        self._badge.grid_propagate(False)
        self._badge_lbl = ctk.CTkLabel(
            self._badge, text=str(idx + 1),
            font=(fn, 11, "bold"), text_color=C["text3"])
        self._badge_lbl.place(relx=.5, rely=.5, anchor="center")

        # Info
        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=10)

        self._name_lbl = ctk.CTkLabel(
            info, text=os.path.splitext(filename)[0],
            font=(fn, 14, "bold"), text_color=C["text"], anchor="w")
        self._name_lbl.pack(anchor="w")

        size_kb = os.path.getsize(path) / 1024
        mtime   = time.strftime(
            "%Y/%m/%d  %H:%M", time.localtime(os.path.getmtime(path)))
        ctk.CTkLabel(
            info, text=f"{size_kb:.1f} KB  ·  {mtime}",
            font=(fn, 10), text_color=C["text3"], anchor="w"
        ).pack(anchor="w")

        # Actions
        acts = ctk.CTkFrame(self, fg_color="transparent")
        acts.grid(row=0, column=2, padx=12)

        self._btn_play = ctk.CTkButton(
            acts, text="▶",
            width=42, height=38, corner_radius=11,
            fg_color=C["surface2"], hover_color=C["accent2"],
            border_width=1, border_color=C["border"],
            font=("Segoe UI Emoji", 15), text_color=C["text"],
            command=self._on_play)
        self._btn_play.pack(side="left", padx=3)

        ctk.CTkButton(
            acts, text=T["folder"],
            width=42, height=38, corner_radius=11,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=("Segoe UI Emoji", 15), text_color=C["text2"],
            command=self._on_folder
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            acts, text=T["rename"],
            width=42, height=38, corner_radius=11,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=("Segoe UI Emoji", 16), text_color=C["blue"],
            command=self._on_rename
        ).pack(side="left", padx=3)

        ctk.CTkButton(
            acts, text=T["delete"],
            width=46, height=38, corner_radius=11,
            fg_color=C["del_bg"], hover_color=C["danger"],
            border_width=1, border_color=C["danger"],
            font=(fn, 13, "bold"), text_color=C["danger"],
            command=self._on_delete
        ).pack(side="left", padx=(8, 0))

    # ── public: update play-state visuals only ────────────────────────────────
    def set_playing(self, playing: bool):
        C = self.app.C
        if playing:
            self.configure(fg_color=C["surface2"], border_color=C["accent"])
            self._badge.configure(fg_color=C["accent"])
            self._badge_lbl.configure(text_color="#fff")
            self._btn_play.configure(
                text="⏸", fg_color=C["accent"],
                border_width=0, text_color="#fff")
        else:
            self.configure(fg_color=C["surface"], border_color=C["border"])
            self._badge.configure(fg_color=C["surface2"])
            self._badge_lbl.configure(text_color=C["text3"])
            self._btn_play.configure(
                text="▶", fg_color=C["surface2"],
                border_width=1, border_color=C["border"],
                text_color=C["text"])

    # ── public: update name label after rename ────────────────────────────────
    def update_name(self, new_filename: str):
        self.filename = new_filename
        self._name_lbl.configure(text=os.path.splitext(new_filename)[0])

    # ── callbacks ─────────────────────────────────────────────────────────────
    def _on_play(self):
        self.app._toggle_play(self.filename, self)

    def _on_folder(self):
        self.app._show_in_folder(self.filename)

    def _on_rename(self):
        self.app._rename(self.filename, self)

    def _on_delete(self):
        self.app._delete(self.filename, self)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class VoiceStudio(ctk.CTk):

    def __init__(self):
        super().__init__()
        load_lalezar()

        available = tkfont.families()
        self.fn = "Lalezar" if "Lalezar" in available else "Tahoma"

        # State
        self.lang_key      = "fa"
        self.mode          = "Dark"
        self.is_generating = False
        self.playing_file  = None      # filename currently playing
        self.playing_row   = None      # VoiceRow widget currently lit up
        self._rows: dict   = {}        # filename → VoiceRow
        self.logo_path     = None      # custom logo image path
        self.search_var    = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_history())

        pygame.mixer.init()
        ctk.set_appearance_mode(self.mode)
        ctk.set_default_color_theme("blue")

        self.title("AI Voice Studio Pro")
        self.geometry("880x960")
        self.minsize(740, 700)
        self.configure(fg_color=self.C["bg"])

        self._build_ui()
        self.refresh_history()
        self._start_playback_watcher()  # polling loop for end-of-track

    # ── shorthands ────────────────────────────────────────────────────────────
    @property
    def C(self): return THEMES[self.mode]
    @property
    def T(self): return LANG[self.lang_key]
    def font(self, size=14, bold=False):
        return (self.fn, size, "bold" if bold else "normal")

    # ─────────────────────────────────────────────────────────────────────────
    #  PLAYBACK WATCHER  — polls every 400 ms; resets row when track ends
    # ─────────────────────────────────────────────────────────────────────────
    def _start_playback_watcher(self):
        def _tick():
            if self.playing_file and not pygame.mixer.music.get_busy():
                # Track finished naturally → reset UI
                self.playing_file = None
                if self.playing_row and self.playing_row.winfo_exists():
                    self.playing_row.set_playing(False)
                self.playing_row = None
            self.after(400, _tick)
        self.after(400, _tick)

    # ─────────────────────────────────────────────────────────────────────────
    #  UI BUILD
    # ─────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_body()
        self._build_toast()
        self.bind("<Control-Return>", lambda e: self._on_generate())

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _build_header(self):
        C = self.C
        self.header = ctk.CTkFrame(
            self, fg_color=C["header_bg"], corner_radius=0, height=72)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)

        # Logo pill — click to set custom logo
        self.logo_pill = ctk.CTkFrame(
            self.header, fg_color=C["accent"],
            corner_radius=14, width=46, height=46,
            cursor="hand2")
        self.logo_pill.grid(row=0, column=0, padx=(20, 12), pady=13)
        self.logo_pill.grid_propagate(False)
        self.logo_pill.bind("<Button-1>", lambda e: self._pick_logo())

        self.logo_label = ctk.CTkLabel(
            self.logo_pill, text="🎙",
            font=("Segoe UI Emoji", 22), text_color="#fff")
        self.logo_label.place(relx=.5, rely=.5, anchor="center")
        self.logo_label.bind("<Button-1>", lambda e: self._pick_logo())

        # Title
        ts = ctk.CTkFrame(self.header, fg_color="transparent")
        ts.grid(row=0, column=1, sticky="w")
        self.lbl_title = ctk.CTkLabel(ts, text=self.T["title"],
                                      font=self.font(20, True), text_color=C["text"])
        self.lbl_title.pack(anchor="w")
        self.lbl_sub = ctk.CTkLabel(ts, text=self.T["subtitle"],
                                    font=self.font(11), text_color=C["text3"])
        self.lbl_sub.pack(anchor="w")

        # Controls
        ctrl = ctk.CTkFrame(self.header, fg_color="transparent")
        ctrl.grid(row=0, column=2, padx=20)

        self.btn_theme = ctk.CTkButton(
            ctrl, text="☀️", width=42, height=42, corner_radius=12,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=("Segoe UI Emoji", 17), text_color=C["text"],
            command=self._toggle_theme)
        self.btn_theme.pack(side="left", padx=(0, 8))

        self.btn_lang = ctk.CTkButton(
            ctrl, text=self.T["lang_switch"],
            width=52, height=42, corner_radius=12,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"],
            font=self.font(13, True), text_color=C["accent"],
            command=self._toggle_lang)
        self.btn_lang.pack(side="left")

    # ── BODY ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        C = self.C
        self.body = ctk.CTkScrollableFrame(
            self, fg_color=C["bg"], corner_radius=0,
            scrollbar_button_color=C["scrollbar"],
            scrollbar_button_hover_color=C["accent"])
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_columnconfigure(0, weight=1)

        self._build_input_card()
        self._build_controls_bar()
        self._build_history_area()

    # ── INPUT CARD ────────────────────────────────────────────────────────────
    def _build_input_card(self):
        C = self.C
        self.input_card = ctk.CTkFrame(
            self.body, fg_color=C["surface"], corner_radius=20,
            border_width=1, border_color=C["border"])
        self.input_card.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 10))
        self.input_card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self.input_card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 6))
        top.grid_columnconfigure(0, weight=1)

        self.lbl_input = ctk.CTkLabel(
            top, text=self.T["input_label"],
            font=self.font(13, True), text_color=C["text2"])
        self.lbl_input.grid(row=0, column=0, sticky="w")

        self.lbl_chars = ctk.CTkLabel(
            top, text=f"0 {self.T['chars']}",
            font=self.font(11), text_color=C["text3"])
        self.lbl_chars.grid(row=0, column=1, sticky="e")

        self.textbox = ctk.CTkTextbox(
            self.input_card, height=160, font=self.font(14),
            fg_color=C["input_bg"],
            border_width=1, border_color=C["border"],
            corner_radius=14, text_color=C["text"],
            scrollbar_button_color=C["scrollbar"],
            scrollbar_button_hover_color=C["accent"])
        self.textbox.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.textbox.bind("<KeyRelease>", self._on_key)

        self.progress = ctk.CTkProgressBar(
            self.input_card, height=3, corner_radius=2,
            fg_color=C["border"], progress_color=C["accent"])
        self.progress.set(0)

        btn_row = ctk.CTkFrame(self.input_card, fg_color="transparent")
        btn_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 18))

        self.btn_clear = ctk.CTkButton(
            btn_row, text=self.T["btn_clear"], width=110, height=44,
            fg_color=C["surface2"], hover_color=C["border"],
            border_width=1, border_color=C["border"], corner_radius=12,
            font=self.font(13), text_color=C["text2"],
            command=self._clear_text)
        self.btn_clear.pack(side="left", padx=(0, 10))

        self.btn_gen = ctk.CTkButton(
            btn_row, text=self.T["btn_gen"], height=44,
            fg_color=C["accent"], hover_color=C["accent2"],
            corner_radius=12, font=self.font(14, True), text_color="#fff",
            command=self._on_generate)
        self.btn_gen.pack(side="left", fill="x", expand=True)

    # ── CONTROLS BAR ─────────────────────────────────────────────────────────
    def _build_controls_bar(self):
        C = self.C
        bar = ctk.CTkFrame(self.body, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=24, pady=(6, 4))
        bar.grid_columnconfigure(1, weight=1)
        self.controls_bar = bar

        self.vol_pill = ctk.CTkFrame(bar, fg_color=C["surface"], corner_radius=12,
                                     border_width=1, border_color=C["border"])
        self.vol_pill.grid(row=0, column=0)

        self.lbl_vol = ctk.CTkLabel(
            self.vol_pill, text=f"🔊  {self.T['volume']}",
            font=self.font(12), text_color=C["text2"])
        self.lbl_vol.pack(side="left", padx=(14, 6), pady=9)

        self.vol_slider = ctk.CTkSlider(
            self.vol_pill, from_=0, to=1, width=100,
            button_color=C["accent"], button_hover_color=C["accent2"],
            progress_color=C["accent"], fg_color=C["border"],
            command=lambda v: pygame.mixer.music.set_volume(float(v)))
        self.vol_slider.set(0.8)
        self.vol_slider.pack(side="left", padx=(0, 14))
        pygame.mixer.music.set_volume(0.8)

        self.search_entry = ctk.CTkEntry(
            bar, placeholder_text=self.T["search_ph"],
            textvariable=self.search_var,
            height=42, corner_radius=12,
            fg_color=C["surface"], border_color=C["border"],
            text_color=C["text"], placeholder_text_color=C["text3"],
            font=self.font(12))
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=10)

        self.btn_folder = ctk.CTkButton(
            bar, text=f"📁  {self.T['export_all']}",
            height=42, width=150,
            fg_color=C["surface"], hover_color=C["surface2"],
            border_width=1, border_color=C["border"], corner_radius=12,
            font=self.font(12), text_color=C["text2"],
            command=self._open_folder)
        self.btn_folder.grid(row=0, column=2)

    # ── HISTORY AREA ──────────────────────────────────────────────────────────
    def _build_history_area(self):
        self.hist_hdr_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self.hist_hdr_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(16, 8))
        self._rebuild_hist_header()

        self.hist_container = ctk.CTkFrame(self.body, fg_color="transparent")
        self.hist_container.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 28))
        self.hist_container.grid_columnconfigure(0, weight=1)

    def _rebuild_hist_header(self):
        for w in self.hist_hdr_frame.winfo_children(): w.destroy()
        C = self.C
        ctk.CTkFrame(self.hist_hdr_frame, width=4, height=26,
                     fg_color=C["accent"], corner_radius=2
                     ).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(self.hist_hdr_frame, text=self.T["history"],
                     font=self.font(16, True), text_color=C["text"]
                     ).pack(side="left")

    # ── FULL HISTORY REBUILD (only when list changes) ─────────────────────────
    def refresh_history(self):
        for w in self.hist_container.winfo_children(): w.destroy()
        self._rows.clear()

        q     = self.search_var.get().lower()
        files = [f for f in os.listdir(VOICE_DIR)
                 if f.endswith(".mp3") and q in f.lower()]
        files.sort(key=lambda x: os.path.getmtime(
            os.path.join(VOICE_DIR, x)), reverse=True)

        if not files:
            self._build_empty_state()
            return

        for i, f in enumerate(files):
            row = VoiceRow(self.hist_container, i, f, self)
            row.grid(row=i, column=0, sticky="ew", pady=4)
            # Restore play state if this file is still playing
            if f == self.playing_file and pygame.mixer.music.get_busy():
                row.set_playing(True)
                self.playing_row = row
            self._rows[f] = row

    def _build_empty_state(self):
        C = self.C
        box = ctk.CTkFrame(self.hist_container, fg_color=C["surface"],
                           corner_radius=20, border_width=1, border_color=C["border"])
        box.grid(row=0, column=0, sticky="ew", pady=6)
        ctk.CTkLabel(box, text="🎵", font=("Segoe UI Emoji", 38)).pack(pady=(30, 6))
        ctk.CTkLabel(box, text=self.T["no_files"],
                     font=self.font(14), text_color=C["text3"]).pack(pady=(0, 30))

    # ── TOAST ─────────────────────────────────────────────────────────────────
    def _build_toast(self):
        self.toast = ctk.CTkFrame(self, corner_radius=14, fg_color=self.C["success"])
        self.toast_lbl = ctk.CTkLabel(
            self.toast, text="", font=self.font(13), text_color="#fff")
        self.toast_lbl.pack(padx=28, pady=12)
        self.toast.place(relx=0.5, rely=1.2, anchor="s")

    def _show_toast(self, msg, color=None):
        color = color or self.C["success"]
        self.toast.configure(fg_color=color)
        self.toast_lbl.configure(text=f"  {msg}  ")
        self.toast.lift()
        self.toast.place(relx=0.5, rely=0.96, anchor="s")
        threading.Timer(2.8, lambda: self.toast.place(
            relx=0.5, rely=1.2, anchor="s")).start()

    # ─────────────────────────────────────────────────────────────────────────
    #  AUDIO — surgical, no list rebuild
    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_play(self, filename: str, row: VoiceRow):
        # Same file → pause
        if self.playing_file == filename and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.playing_file = None
            self.playing_row  = None
            row.set_playing(False)
            return

        # Different file was playing → reset it
        if self.playing_row and self.playing_row.winfo_exists():
            self.playing_row.set_playing(False)

        p = os.path.join(VOICE_DIR, filename)
        if not os.path.exists(p):
            return

        pygame.mixer.music.load(p)
        pygame.mixer.music.play()
        self.playing_file = filename
        self.playing_row  = row
        row.set_playing(True)

    # ─────────────────────────────────────────────────────────────────────────
    #  GENERATE
    # ─────────────────────────────────────────────────────────────────────────
    def _on_generate(self):
        if self.is_generating: return
        threading.Thread(target=self._generate, daemon=True).start()

    def _generate(self):
        text = self.textbox.get("1.0", "end-1c").strip()
        T    = self.T
        if not text:
            self._show_toast(T["err_empty"], self.C["warning"]); return

        self.is_generating = True
        self.btn_gen.configure(state="disabled", text=T["generating"])
        self.progress.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 4))
        self.progress.start()

        idx = 1
        while os.path.exists(os.path.join(VOICE_DIR, f"Voice_{idx}.mp3")):
            idx += 1
        out = os.path.join(VOICE_DIR, f"Voice_{idx}.mp3")

        try:
            pygame.mixer.music.unload()
            res = requests.post(API_URL, json={"input_text": text},
                                headers={"Authorization": API_TOKEN}, timeout=30)
            if res.status_code == 200:
                with open(out, "wb") as f: f.write(res.content)
                self.refresh_history()
                self._show_toast(T["ok"], self.C["success"])
            else:
                self._show_toast(f"{T['err']} ({res.status_code})", self.C["danger"])
        except requests.exceptions.Timeout:
            self._show_toast(T["err_timeout"], self.C["danger"])
        except Exception as e:
            self._show_toast(f"Error: {e}", self.C["danger"])
        finally:
            self.progress.stop(); self.progress.set(0); self.progress.grid_remove()
            self.btn_gen.configure(state="normal", text=self.T["btn_gen"])
            self.is_generating = False

    # ─────────────────────────────────────────────────────────────────────────
    #  FILE OPS — surgical, no list rebuild unless necessary
    # ─────────────────────────────────────────────────────────────────────────
    def _delete(self, filename: str, row: VoiceRow):
        T, C = self.T, self.C
        dlg = DeleteDialog(self, filename, T, C, self.fn)
        self.wait_window(dlg)
        if not getattr(dlg, "confirmed", False):
            return
        try:
            if self.playing_file == filename:
                pygame.mixer.music.unload()
                self.playing_file = None
                self.playing_row  = None
            os.remove(os.path.join(VOICE_DIR, filename))
            self._rows.pop(filename, None)
            self._show_toast(T["deleted"], self.C["success"])
            self.refresh_history()          # list count changed → full rebuild OK
        except Exception as e:
            self._show_toast(f"Error: {e}", self.C["danger"])

    def _rename(self, filename: str, row: VoiceRow):
        """Open inline themed dialog; on confirm update only the row label."""
        T, C = self.T, self.C
        dlg = RenameDialog(self, filename, T, C, self.fn)
        self.wait_window(dlg)              # blocks until dialog closes

        new_name = getattr(dlg, "result", None)
        if not new_name or new_name == filename:
            return

        try:
            if self.playing_file == filename:
                pygame.mixer.music.unload()
                self.playing_file = new_name
            os.rename(os.path.join(VOICE_DIR, filename),
                      os.path.join(VOICE_DIR, new_name))
            # Surgical update: just rename in _rows dict + update label
            self._rows.pop(filename, None)
            self._rows[new_name] = row
            row.update_name(new_name)
            self._show_toast(T["renamed"], self.C["success"])
        except Exception as e:
            self._show_toast(f"Error: {e}", self.C["danger"])

    def _show_in_folder(self, filename: str):
        path = os.path.abspath(os.path.join(VOICE_DIR, filename))
        if sys.platform == "win32":
            subprocess.run(["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", path])
        else:
            subprocess.run(["xdg-open", os.path.dirname(path)])

    def _open_folder(self):
        path = os.path.abspath(VOICE_DIR)
        if sys.platform == "win32":    subprocess.run(["explorer", path])
        elif sys.platform == "darwin": subprocess.run(["open", path])
        else:                          subprocess.run(["xdg-open", path])

    # ─────────────────────────────────────────────────────────────────────────
    #  LOGO PICKER
    # ─────────────────────────────────────────────────────────────────────────
    def _pick_logo(self):
        """Let user pick a PNG/JPG/ICO as app logo — shown in header pill."""
        from tkinter import filedialog
        from PIL import Image, ImageTk  # pillow required

        path = filedialog.askopenfilename(
            title="انتخاب لوگو" if self.lang_key == "fa" else "Select Logo",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.ico *.webp"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            img = img.resize((36, 36), Image.LANCZOS)

            # Circular crop
            import io
            mask = Image.new("L", (36, 36), 0)
            from PIL import ImageDraw
            ImageDraw.Draw(mask).ellipse((0, 0, 35, 35), fill=255)
            result = Image.new("RGBA", (36, 36), (0, 0, 0, 0))
            result.paste(img, mask=mask)

            self._logo_ctk = ctk.CTkImage(light_image=result, dark_image=result,
                                          size=(36, 36))
            self.logo_path  = path
            self.logo_label.configure(image=self._logo_ctk, text="")
            self.logo_pill.configure(fg_color="transparent")
            # Also set as window icon (ico or png)
            try:
                self.iconphoto(False, ImageTk.PhotoImage(
                    Image.open(path).resize((32, 32))))
            except Exception:
                pass
        except ImportError:
            self._show_toast("Pillow not installed: pip install pillow",
                             self.C["warning"])
        except Exception as e:
            self._show_toast(f"Logo error: {e}", self.C["danger"])

    # ─────────────────────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────────────────────
    def _clear_text(self):
        self.textbox.delete("1.0", "end"); self._on_key()

    def _on_key(self, _=None):
        count = len(self.textbox.get("1.0", "end-1c").strip())
        self.lbl_chars.configure(text=f"{count} {self.T['chars']}")

    # ─────────────────────────────────────────────────────────────────────────
    #  THEME TOGGLE
    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self.mode = "Light" if self.mode == "Dark" else "Dark"
        ctk.set_appearance_mode(self.mode)
        self.btn_theme.configure(text="🌙" if self.mode == "Light" else "☀️")
        self._recolor_all()

    def _recolor_all(self):
        C = self.C
        self.configure(fg_color=C["bg"])

        # Header
        self.header.configure(fg_color=C["header_bg"])
        self.lbl_title.configure(text_color=C["text"])
        self.lbl_sub.configure(text_color=C["text3"])
        self.btn_theme.configure(fg_color=C["surface2"], hover_color=C["border"],
                                 border_color=C["border"], text_color=C["text"])
        self.btn_lang.configure(fg_color=C["surface2"], hover_color=C["border"],
                                border_color=C["border"], text_color=C["accent"])

        # Body
        self.body.configure(fg_color=C["bg"],
                            scrollbar_button_color=C["scrollbar"],
                            scrollbar_button_hover_color=C["accent"])

        # Input card
        self.input_card.configure(fg_color=C["surface"], border_color=C["border"])
        self.lbl_input.configure(text_color=C["text2"])
        self.lbl_chars.configure(text_color=C["text3"])
        self.textbox.configure(fg_color=C["input_bg"], border_color=C["border"],
                               text_color=C["text"],
                               scrollbar_button_color=C["scrollbar"],
                               scrollbar_button_hover_color=C["accent"])
        self.progress.configure(fg_color=C["border"], progress_color=C["accent"])
        self.btn_clear.configure(fg_color=C["surface2"], hover_color=C["border"],
                                 border_color=C["border"], text_color=C["text2"])
        self.btn_gen.configure(fg_color=C["accent"], hover_color=C["accent2"])

        # Controls bar
        self.vol_pill.configure(fg_color=C["surface"], border_color=C["border"])
        self.lbl_vol.configure(text_color=C["text2"])
        self.vol_slider.configure(button_color=C["accent"],
                                  button_hover_color=C["accent2"],
                                  progress_color=C["accent"], fg_color=C["border"])
        self.search_entry.configure(fg_color=C["surface"], border_color=C["border"],
                                    text_color=C["text"],
                                    placeholder_text_color=C["text3"])
        self.btn_folder.configure(fg_color=C["surface"], hover_color=C["surface2"],
                                  border_color=C["border"], text_color=C["text2"])

        self._rebuild_hist_header()
        self.refresh_history()

    # ─────────────────────────────────────────────────────────────────────────
    #  LANG TOGGLE
    # ─────────────────────────────────────────────────────────────────────────
    def _toggle_lang(self):
        self.lang_key = "en" if self.lang_key == "fa" else "fa"
        T = self.T
        self.btn_lang.configure(text=T["lang_switch"])
        self.lbl_title.configure(text=T["title"])
        self.lbl_sub.configure(text=T["subtitle"])
        self.lbl_input.configure(text=T["input_label"])
        self.btn_clear.configure(text=T["btn_clear"])
        self.btn_gen.configure(text=T["btn_gen"])
        self.lbl_vol.configure(text=f"🔊  {T['volume']}")
        self.search_entry.configure(placeholder_text=T["search_ph"])
        self.btn_folder.configure(text=f"📁  {T['export_all']}")
        self._on_key()
        self._rebuild_hist_header()
        self.refresh_history()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = VoiceStudio()
    app.mainloop()
