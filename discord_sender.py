import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import requests
import json
import os
import time
from PIL import Image, ImageTk

APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DiscordAutoSender")
os.makedirs(APP_DATA_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

BG     = "#1e1f22"
BG2    = "#2b2d31"
BG3    = "#313338"
ACCENT = "#5865f2"
ACCENT2= "#4752c4"
TEXT   = "#dbdee1"
MUTED  = "#949ba4"
GREEN  = "#23a55a"
RED    = "#f23f42"
YELLOW = "#f0b232"
BORDER = "#3f4147"

def make_entry(parent, show=None, font=("Segoe UI", 10), **kw):
    return tk.Entry(parent, bg=BG3, fg=TEXT, insertbackground=TEXT,
        relief="flat", bd=0, font=font,
        highlightthickness=1, highlightbackground=BORDER,
        highlightcolor=ACCENT, show=show or "", **kw)

def make_btn(parent, text, command, bg=ACCENT, fg="white", abg=ACCENT2,
             font=("Segoe UI", 10, "bold"), **kw):
    return tk.Button(parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
        relief="flat", bd=0, font=font, cursor="hand2", **kw)

def lbl(parent, text, fg=MUTED, bg=None, font=("Segoe UI", 9), **kw):
    return tk.Label(parent, text=text, bg=bg or parent.cget("bg"),
        fg=fg, font=font, **kw)


class DiscordSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Auto Sender")
        self.root.geometry("460x600")
        self.root.minsize(460, 600)
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self._set_icon()

        self.channels = []
        self.selected_idx = -1
        self.image_path = None
        self.running = False
        self.send_count = 0
        self.timer_thread = None
        self.stop_event = threading.Event()

        self.token_var = tk.StringVar()
        self.interval_var = tk.IntVar(value=30)
        self.message_var = tk.StringVar()

        self._load_config()
        self._build_ui()

    # ── ICON ──────────────────────────────────────────────────────────────────

    def _get_resource_path(self, filename):
        """Путь к файлу: внутри exe (PyInstaller _MEIPASS) или рядом со скриптом."""
        import sys
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, filename)

    def _set_icon(self):
        import sys, shutil
        stored_ico = os.path.join(APP_DATA_DIR, "icon.ico")
        stored_png = os.path.join(APP_DATA_DIR, "icon.png")

        # Если иконки ещё нет в AppData — извлекаем из встроенных ресурсов exe
        for fname, stored in [("icon.ico", stored_ico), ("icon.png", stored_png)]:
            if not os.path.exists(stored):
                src = self._get_resource_path(fname)
                if os.path.exists(src):
                    try:
                        shutil.copy2(src, stored)
                    except Exception:
                        pass

        self._header_icon_img = None
        try:
            if os.path.exists(stored_ico):
                self.root.iconbitmap(default=stored_ico)
                img = Image.open(stored_ico)
                img.thumbnail((28, 28))
                self._header_icon_img = ImageTk.PhotoImage(img)
            elif os.path.exists(stored_png):
                img = Image.open(stored_png)
                big = img.copy()
                big.thumbnail((256, 256))
                ph_big = ImageTk.PhotoImage(big)
                self.root.iconphoto(True, ph_big)
                self._taskbar_icon = ph_big
                img.thumbnail((28, 28))
                self._header_icon_img = ImageTk.PhotoImage(img)
        except Exception:
            pass

    # ── BUILD UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG2, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        if self._header_icon_img:
            tk.Label(hdr, image=self._header_icon_img,
                bg=BG2).pack(side="left", padx=(14, 8), pady=12)
        else:
            c = tk.Canvas(hdr, width=28, height=28, bg=ACCENT, highlightthickness=0)
            c.pack(side="left", padx=(14, 10), pady=12)
        tk.Label(hdr, text="Discord Auto Sender", bg=BG2,
            fg=TEXT, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(hdr, text="made by ATOKI", bg=ACCENT2,
            fg="#c4c9ff", font=("Segoe UI", 8), padx=7, pady=3).pack(
            side="left", padx=(10, 0))

        # Tab bar
        tab_bar = tk.Frame(self.root, bg=BG3, height=40)
        tab_bar.pack(fill="x")
        tab_bar.pack_propagate(False)
        self.tab_btns = {}
        tabs = [("main","▶  Главная"), ("token","🔑  Токен"),
                ("channels","#  Каналы"), ("message","✉  Сообщение")]
        for key, label in tabs:
            b = tk.Button(tab_bar, text=label, bg=BG3, fg=MUTED,
                activebackground=BG2, activeforeground=TEXT,
                relief="flat", bd=0, font=("Segoe UI", 9),
                cursor="hand2", padx=12, pady=10,
                command=lambda k=key: self._switch_tab(k))
            b.pack(side="left")
            self.tab_btns[key] = b

        # Pages
        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True)
        self.page_main     = tk.Frame(self.container, bg=BG)
        self.page_token    = tk.Frame(self.container, bg=BG)
        self.page_channels = tk.Frame(self.container, bg=BG)
        self.page_message  = tk.Frame(self.container, bg=BG)

        self._build_main()
        self._build_token()
        self._build_channels()
        self._build_message()
        self._switch_tab("main")

    def _switch_tab(self, key):
        for k, b in self.tab_btns.items():
            b.config(bg=BG2 if k == key else BG3,
                     fg=TEXT if k == key else MUTED)
        pages = {"main": self.page_main, "token": self.page_token,
                 "channels": self.page_channels, "message": self.page_message}
        for k, pg in pages.items():
            pg.pack_forget()
        pages[key].pack(fill="both", expand=True)

    # ── MAIN PAGE ─────────────────────────────────────────────────────────────

    def _build_main(self):
        p = self.page_main

        # Status card
        sc = tk.Frame(p, bg=BG2)
        sc.pack(fill="x", padx=20, pady=(16, 8))
        si = tk.Frame(sc, bg=BG2)
        si.pack(fill="x", padx=14, pady=10)
        dr = tk.Frame(si, bg=BG2)
        dr.pack(fill="x")
        self.status_dot = tk.Canvas(dr, width=10, height=10,
            bg=BG2, highlightthickness=0)
        self.status_dot.pack(side="left", padx=(0,7))
        self.status_dot.create_oval(2,2,8,8, fill=MUTED, outline="", tags="dot")
        self.status_lbl = tk.Label(dr, text="Ожидание запуска...",
            bg=BG2, fg=TEXT, font=("Segoe UI", 10))
        self.status_lbl.pack(side="left")


        # Progress bar
        self.prog_canvas = tk.Canvas(p, height=5, bg=BORDER, highlightthickness=0)
        self.prog_canvas.pack(fill="x", padx=20, pady=(0,2))
        self.countdown_lbl = tk.Label(p, text="", bg=BG, fg=MUTED, font=("Segoe UI",8))
        self.countdown_lbl.pack(anchor="e", padx=20)

        # Interval card
        ic = tk.Frame(p, bg=BG2)
        ic.pack(fill="x", padx=20, pady=(6,0))
        ii = tk.Frame(ic, bg=BG2)
        ii.pack(fill="x", padx=14, pady=(10,4))
        lbl(ii, "Интервал отправки", bg=BG2).pack(side="left")
        self.interval_lbl = tk.Label(ii, text=f"{self.interval_var.get()} мин",
            bg=BG2, fg=TEXT, font=("Segoe UI",10,"bold"))
        self.interval_lbl.pack(side="right")
        sw = tk.Frame(ic, bg=BG2)
        sw.pack(fill="x", padx=14, pady=(0,10))
        self.slider = tk.Scale(sw, from_=1, to=120, variable=self.interval_var,
            orient="horizontal", bg=BG2, fg=MUTED,
            troughcolor=BORDER, activebackground=ACCENT,
            background="#72767d", cursor="hand2",
            highlightthickness=0, bd=0, showvalue=False,
            sliderrelief="flat", command=self._on_interval)
        self.slider.pack(fill="x")

        def _slider_click(e):
            w = self.slider.winfo_width()
            slider_x = int((self.interval_var.get() - 1) / (120 - 1) * w)
            if abs(e.x - slider_x) > 25:
                val = round(1 + (e.x / w) * (120 - 1))
                val = max(1, min(120, val))
                self.interval_var.set(val)
                self._on_interval(val)
                return "break"
        self.slider.bind("<Button-1>", _slider_click)

        # Badges row
        br = tk.Frame(p, bg=BG)
        br.pack(fill="x", padx=20, pady=(10,0))
        self.badge_token   = self._badge(br, "Токен")
        self.badge_channel = self._badge(br, "Канал")
        self.badge_msg     = self._badge(br, "Сообщение")
        self._refresh_badges()

        # Buttons
        bf = tk.Frame(p, bg=BG)
        bf.pack(fill="x", padx=20, pady=(12,0))
        self.start_btn = make_btn(bf, "▶  Начать отправку", self._start,
            disabledforeground="#a0a8ff")
        self.start_btn.pack(fill="x", ipady=10)
        self.stop_btn = make_btn(bf, "■  Остановить", self._stop,
            bg=BORDER, fg=RED, abg=RED)
        self.stop_btn.pack(fill="x", ipady=8, pady=(6,0))
        self.stop_btn.config(state="disabled")

        # Log
        lf = tk.Frame(p, bg=BG2)
        lf.pack(fill="both", expand=True, padx=20, pady=(12,0))
        lbl(lf, "Последние события", bg=BG2).pack(anchor="w", padx=12, pady=(6,2))
        self.log_text = tk.Text(lf, height=7, state="disabled",
            bg=BG3, fg=MUTED, relief="flat", bd=0,
            font=("Consolas", 9), padx=8, pady=5, highlightthickness=0)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0,8))
        self.log_text.tag_config("ok", foreground=GREEN)
        self.log_text.tag_config("err", foreground=RED)

    def _badge(self, parent, title):
        f = tk.Frame(parent, bg=BG2)
        f.pack(side="left", fill="x", expand=True, padx=(0,5))
        lbl(f, title, bg=BG2).pack(anchor="w", padx=8, pady=(6,0))
        v = tk.Label(f, text="...", bg=BG2, fg=MUTED, font=("Segoe UI",9,"bold"))
        v.pack(anchor="w", padx=8, pady=(0,6))
        return v

    def _refresh_badges(self):
        self.badge_token.config(
            text="задан ✓" if self.token_var.get().strip() else "не задан",
            fg=GREEN if self.token_var.get().strip() else RED)
        if 0 <= self.selected_idx < len(self.channels):
            self.badge_channel.config(
                text=f"# {self.channels[self.selected_idx]['name']}", fg=GREEN)
        else:
            self.badge_channel.config(text="не выбран", fg=RED)
        msg = self.message_var.get().strip()
        has_img = bool(self.image_path)
        if msg or has_img:
            parts = (["текст ✓"] if msg else []) + (["фото ✓"] if has_img else [])
            self.badge_msg.config(text=" + ".join(parts), fg=GREEN)
        else:
            self.badge_msg.config(text="пусто", fg=RED)

    # ── TOKEN PAGE ────────────────────────────────────────────────────────────

    TOKEN_SCRIPT = (
        "window.__token = null; "
        "Object.entries(webpackChunkdiscord_app.__proto__).forEach(([k,v])=>{"
        "try{const t=v?.default?.getToken?.();if(t)window.__token=t}catch(e){}"
        "}); "
        "const chunks=webpackChunkdiscord_app; "
        "for(const id in chunks.c||{}){"
        "try{const m=chunks.c[id]?.exports; "
        "const t=m?.default?.getToken?.()||m?.getToken?.(); "
        "if(t){window.__token=t;break}}catch(e){}"
        "} "
        "window.__token || copy(window.__token)"
    )
    TOKEN_SCRIPT_ALT = (
        "/* Способ через Network (если скрипт не сработал): */\n"
        "/* 1. Открой вкладку Network (Сеть) */\n"
        "/* 2. Обнови страницу F5 */\n"
        "/* 3. Нажми на любой запрос /api/ */\n"
        "/* 4. Headers → Request Headers → authorization */"
    )

    def _build_token(self):
        p = self.page_token
        tk.Label(p, text="Токен пользователя", bg=BG, fg=TEXT,
            font=("Segoe UI",12,"bold")).pack(anchor="w", padx=20, pady=(20,4))

        # Инструкция
        steps = tk.Frame(p, bg=BG2)
        steps.pack(fill="x", padx=20, pady=(6,10))
        si = tk.Frame(steps, bg=BG2)
        si.pack(fill="x", padx=14, pady=12)
        tk.Label(si, text="Как найти токен пользователя:", bg=BG2,
            fg=TEXT, font=("Segoe UI",9,"bold")).pack(anchor="w", pady=(0,4))
        for text in [
            "1. Открой свой профиль на сайте discord.com в браузере",
            "2. Нажми F12 → вкладка Network (Сеть)",
            "3. Обнови страницу — F5",
            "4. В строке фильтра введи:  /api",
            "5. Кликни на любой запрос к discord.com/api/...",
            "6. Справа открой Headers → Request Headers",
            "7. Найди строку Authorization — это токен",
        ]:
            tk.Label(si, text=text, bg=BG2, fg=TEXT,
                font=("Segoe UI",9)).pack(anchor="w", pady=1)

        warn = tk.Frame(p, bg="#2a2000")
        warn.pack(fill="x", padx=20, pady=(0,10))
        tk.Frame(warn, bg=YELLOW, width=4).pack(side="left", fill="y")
        tk.Label(warn, text="  ⚠  Не передавай токен третьим лицам.",
            bg="#2a2000", fg=YELLOW, font=("Segoe UI",9)).pack(
            side="left", padx=8, pady=8)

        card = tk.Frame(p, bg=BG2)
        card.pack(fill="x", padx=20)
        inner = tk.Frame(card, bg=BG2)
        inner.pack(fill="x", padx=14, pady=14)

        lbl(inner, "Токен", bg=BG2).pack(anchor="w", pady=(0,4))
        self.token_entry = make_entry(inner, show="•", font=("Consolas",10))
        self.token_entry.pack(fill="x", ipady=7)
        self.token_entry.insert(0, self.token_var.get())
        self._bind_entry_hotkeys(self.token_entry)
        self._bind_entry_context_menu(self.token_entry)

        br = tk.Frame(inner, bg=BG2)
        br.pack(fill="x", pady=(8,0))
        make_btn(br, "показать / скрыть", self._toggle_token,
            bg=BORDER, fg=TEXT, abg=BG3, font=("Segoe UI",9)).pack(side="left")
        make_btn(br, "Сохранить", self._save_token,
            font=("Segoe UI",9,"bold")).pack(side="right", ipadx=10, ipady=5)

        self.token_ok_lbl = tk.Label(inner, text="", bg=BG2,
            fg=GREEN, font=("Segoe UI",9))
        self.token_ok_lbl.pack(anchor="w", pady=(6,0))

    def _copy_script(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.TOKEN_SCRIPT)
        self.copy_script_lbl.config(text="✓ Скрипт скопирован!")
        self.root.after(2000, lambda: self.copy_script_lbl.config(text=""))

    def _toggle_token(self):
        self.token_entry.config(
            show="" if self.token_entry.cget("show") == "•" else "•")

    def _save_token(self):
        self.token_var.set(self.token_entry.get().strip())
        self.token_ok_lbl.config(text="✓ Токен сохранён")
        self._save_config()
        self._refresh_badges()
        self.root.after(2000, lambda: self.token_ok_lbl.config(text=""))

    # ── CHANNELS PAGE ─────────────────────────────────────────────────────────

    def _build_channels(self):
        p = self.page_channels
        tk.Label(p, text="Каналы для отправки", bg=BG, fg=TEXT,
            font=("Segoe UI",12,"bold")).pack(anchor="w", padx=20, pady=(20,4))
        lbl(p, "Добавь каналы и выбери один").pack(anchor="w", padx=20, pady=(0,6))

        # Гайд как найти ID канала
        guide = tk.Frame(p, bg=BG3,
            highlightthickness=1, highlightbackground=BORDER)
        guide.pack(fill="x", padx=20, pady=(0,10))
        gf = tk.Frame(guide, bg=BG3)
        gf.pack(fill="x", padx=12, pady=8)
        tk.Label(gf, text="Как найти ID канала:", bg=BG3,
            fg=TEXT, font=("Segoe UI",9,"bold")).pack(anchor="w", pady=(0,4))
        for step in [
            "1. Открой Discord → Настройки (шестерёнка внизу)",
            "2. Расширенные → включи  Режим разработчика",
            "3. Вернись в сервер, нажми ПКМ на нужный канал",
            "4. Нажми Копировать ID канала — готово!",
        ]:
            tk.Label(gf, text=step, bg=BG3, fg=TEXT,
                font=("Segoe UI",9)).pack(anchor="w", pady=1)

        add = tk.Frame(p, bg=BG2)
        add.pack(fill="x", padx=20, pady=(0,10))
        ai = tk.Frame(add, bg=BG2)
        ai.pack(fill="x", padx=14, pady=12)
        row = tk.Frame(ai, bg=BG2)
        row.pack(fill="x", pady=(0,6))
        nf = tk.Frame(row, bg=BG2)
        nf.pack(side="left", fill="x", expand=True, padx=(0,8))
        lbl(nf, "Название", bg=BG2).pack(anchor="w", pady=(0,3))
        self.ch_name_e = make_entry(nf, width=12)
        self.ch_name_e.pack(fill="x", ipady=6)
        self._bind_entry_hotkeys(self.ch_name_e)
        self._bind_entry_context_menu(self.ch_name_e)
        idf = tk.Frame(row, bg=BG2)
        idf.pack(side="left", fill="x", expand=True)
        lbl(idf, "ID канала (числа)", bg=BG2).pack(anchor="w", pady=(0,3))
        self.ch_id_e = make_entry(idf)
        self.ch_id_e.pack(fill="x", ipady=6)
        self._bind_entry_hotkeys(self.ch_id_e)
        self._bind_entry_context_menu(self.ch_id_e)
        make_btn(ai, "+ Добавить", self._add_channel,
            font=("Segoe UI",9,"bold")).pack(fill="x", ipady=7, pady=(4,0))

        # Скроллируемый список каналов (без видимого скроллбара)
        list_outer = tk.Frame(p, bg=BG)
        list_outer.pack(fill="both", expand=True, padx=20, pady=(0,10))

        ch_canvas = tk.Canvas(list_outer, bg=BG, highlightthickness=0)
        self.ch_list = tk.Frame(ch_canvas, bg=BG)
        self._ch_canvas = ch_canvas

        self.ch_list.bind("<Configure>", lambda e: ch_canvas.configure(
            scrollregion=ch_canvas.bbox("all")))

        ch_win = ch_canvas.create_window((0, 0), window=self.ch_list, anchor="nw")
        ch_canvas.pack(fill="both", expand=True)

        # Растягиваем ширину внутреннего фрейма по канвасу
        ch_canvas.bind("<Configure>",
            lambda e: ch_canvas.itemconfig(ch_win, width=e.width))

        def _on_mousewheel(e):
            # Скролл только если список выходит за пределы канваса
            if self.ch_list.winfo_height() > ch_canvas.winfo_height():
                ch_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        ch_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.ch_list.bind("<MouseWheel>", _on_mousewheel)

        self._render_channels()

    def _add_channel(self):
        name = self.ch_name_e.get().strip()
        cid  = ''.join(filter(str.isdigit, self.ch_id_e.get().strip()))
        if not name or not cid:
            messagebox.showwarning("Ошибка", "Введи название и ID канала")
            return
        self.channels.append({"name": name, "id": cid})
        if self.selected_idx == -1:
            self.selected_idx = 0
        self.ch_name_e.delete(0, "end")
        self.ch_id_e.delete(0, "end")
        self._render_channels()
        self._save_config()
        self._refresh_badges()

    def _render_channels(self):
        for w in self.ch_list.winfo_children():
            w.destroy()
        if not self.channels:
            lbl(self.ch_list, "Каналов нет. Добавь первый выше.").pack(pady=10)
            return
        for i, ch in enumerate(self.channels):
            sel = (i == self.selected_idx)
            rbg = "#313b6e" if sel else BG2

            row = tk.Frame(self.ch_list, bg=rbg,
                highlightthickness=1,
                highlightbackground=ACCENT if sel else BORDER,
                cursor="hand2")
            row.pack(fill="x", pady=(0,5))

            def _select(e, idx=i):
                self._select_channel(idx)
                return "break"

            dot = tk.Label(row, text="●" if sel else "○", bg=rbg,
                fg=ACCENT if sel else MUTED,
                font=("Segoe UI",10), cursor="hand2")
            dot.pack(side="left", padx=(10,6), pady=9)

            name_lbl = tk.Label(row, text=f"# {ch['name']}", bg=rbg,
                fg=TEXT, font=("Segoe UI",10,
                    "bold" if sel else "normal"), cursor="hand2")
            name_lbl.pack(side="left")

            id_lbl = tk.Label(row, text=ch['id'], bg=rbg,
                fg=MUTED, font=("Consolas",8), cursor="hand2")
            id_lbl.pack(side="left", padx=8)

            make_btn(row, "✕", lambda idx=i: self._remove_channel(idx),
                bg=rbg, fg=RED, abg=RED,
                font=("Segoe UI",9)).pack(side="right", padx=8)

            # Привязываем клик и скролл ко всем элементам строки
            def _scroll(e):
                if self.ch_list.winfo_height() > self._ch_canvas.winfo_height():
                    self._ch_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            for widget in (row, dot, name_lbl, id_lbl):
                widget.bind("<Button-1>", _select)
                widget.bind("<MouseWheel>", _scroll)

    def _select_channel(self, idx):
        self.selected_idx = idx
        self._render_channels()
        self._save_config()
        self._refresh_badges()

    def _remove_channel(self, idx):
        self.channels.pop(idx)
        if self.selected_idx >= len(self.channels):
            self.selected_idx = len(self.channels) - 1
        self._render_channels()
        self._save_config()
        self._refresh_badges()

    # ── MESSAGE PAGE ──────────────────────────────────────────────────────────

    def _build_message(self):
        p = self.page_message
        tk.Label(p, text="Сообщение", bg=BG, fg=TEXT,
            font=("Segoe UI",12,"bold")).pack(anchor="w", padx=20, pady=(20,4))
        lbl(p, "Текст и/или фото будут отправлены в выбранный канал"
            ).pack(anchor="w", padx=20, pady=(0,10))

        card = tk.Frame(p, bg=BG2)
        card.pack(fill="x", padx=20)
        inner = tk.Frame(card, bg=BG2)
        inner.pack(fill="x", padx=14, pady=14)

        lbl(inner, "Текст сообщения", bg=BG2).pack(anchor="w", pady=(0,4))
        self.msg_entry = tk.Text(inner, height=5, bg=BG3, fg=TEXT,
            insertbackground=TEXT, relief="flat", bd=0,
            font=("Segoe UI",10), wrap="word",
            highlightthickness=1, highlightbackground=BORDER,
            highlightcolor=ACCENT, padx=8, pady=6)
        self.msg_entry.pack(fill="x")
        self.msg_entry.insert("1.0", self.message_var.get())
        self._bind_hotkeys(self.msg_entry)
        self._bind_context_menu(self.msg_entry)

        lbl(inner, "Фотография", bg=BG2).pack(anchor="w", pady=(12,4))
        ir = tk.Frame(inner, bg=BG2)
        ir.pack(fill="x")
        make_btn(ir, "📎  Выбрать файл", self._pick_image,
            bg=BORDER, fg=TEXT, abg=BG3,
            font=("Segoe UI",9)).pack(side="left", ipady=6, ipadx=8)
        make_btn(ir, "✕ Убрать", self._clear_image,
            bg=BORDER, fg=RED, abg=RED,
            font=("Segoe UI",9)).pack(side="left", padx=(8,0), ipady=6, ipadx=6)

        self.img_name_lbl = tk.Label(inner, text="Файл не выбран",
            bg=BG2, fg=MUTED, font=("Segoe UI",9))
        self.img_name_lbl.pack(anchor="w", pady=(6,0))
        self.img_preview = tk.Label(inner, bg=BG2)
        self.img_preview.pack(anchor="w", pady=(4,0))

        make_btn(inner, "Сохранить сообщение", self._save_message
            ).pack(fill="x", ipady=8, pady=(14,0))
        self.msg_ok_lbl = tk.Label(inner, text="", bg=BG2,
            fg=GREEN, font=("Segoe UI",9))
        self.msg_ok_lbl.pack(anchor="w", pady=(4,0))

        if self.image_path and os.path.exists(self.image_path):
            self.img_name_lbl.config(text=os.path.basename(self.image_path))
            self._show_img_preview(self.image_path)

    def _bind_context_menu(self, widget):
        """Контекстное меню ПКМ для текстового поля."""
        menu = tk.Menu(widget, tearoff=0,
            bg=BG2, fg=TEXT, activebackground=ACCENT,
            activeforeground="white", bd=0,
            font=("Segoe UI", 9), relief="flat")

        def do_cut():
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.get("sel.first", "sel.last"))
                widget.delete("sel.first", "sel.last")
            except tk.TclError: pass

        def do_copy():
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.get("sel.first", "sel.last"))
            except tk.TclError: pass

        def do_paste():
            try:
                text = widget.clipboard_get()
                try: widget.delete("sel.first", "sel.last")
                except tk.TclError: pass
                widget.insert("insert", text)
            except tk.TclError: pass

        def do_select_all():
            widget.tag_add("sel", "1.0", "end")

        def do_clear():
            widget.delete("1.0", "end")

        menu.add_command(label="  Вырезать        Ctrl+X", command=do_cut)
        menu.add_command(label="  Копировать     Ctrl+C", command=do_copy)
        menu.add_command(label="  Вставить         Ctrl+V", command=do_paste)
        menu.add_separator()
        menu.add_command(label="  Выделить всё  Ctrl+A", command=do_select_all)
        menu.add_separator()
        menu.add_command(label="  Очистить", command=do_clear)

        def show_menu(e):
            try: menu.tk_popup(e.x_root, e.y_root)
            finally: menu.grab_release()

        widget.bind("<Button-3>", show_menu)

    def _bind_hotkeys(self, widget):
        """Привязка горячих клавиш через keycode — работает на любой раскладке."""
        def select_all(e):
            widget.tag_add("sel", "1.0", "end")
            return "break"
        def copy(e):
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.get("sel.first", "sel.last"))
            except tk.TclError:
                pass
            return "break"
        def cut(e):
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.get("sel.first", "sel.last"))
                widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            return "break"
        def paste(e):
            try:
                text = widget.clipboard_get()
                try:
                    widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                widget.insert("insert", text)
            except tk.TclError:
                pass
            return "break"
        def undo(e):
            try: widget.edit_undo()
            except: pass
            return "break"
        def redo(e):
            try: widget.edit_redo()
            except: pass
            return "break"

        widget.config(undo=True, maxundo=50)

        # Keycodes не зависят от раскладки клавиатуры (Windows)
        # A=65, C=67, X=88, V=86, Z=90, Y=89
        KEYMAP = {
            65: select_all,   # Ctrl+A
            67: copy,         # Ctrl+C
            88: cut,          # Ctrl+X
            86: paste,        # Ctrl+V
            90: undo,         # Ctrl+Z
            89: redo,         # Ctrl+Y
        }

        def on_key(e):
            if e.state & 0x4:  # Ctrl зажат
                fn = KEYMAP.get(e.keycode)
                if fn:
                    return fn(e)

        widget.bind("<KeyPress>", on_key)

    def _bind_entry_hotkeys(self, widget):
        """Горячие клавиши для tk.Entry через keycode — работает на любой раскладке."""
        def select_all(e):
            widget.select_range(0, "end")
            widget.icursor("end")
            return "break"
        def copy(e):
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.selection_get())
            except tk.TclError: pass
            return "break"
        def cut(e):
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.selection_get())
                widget.delete("sel.first", "sel.last")
            except tk.TclError: pass
            return "break"
        def paste(e):
            try:
                text = widget.clipboard_get()
                try: widget.delete("sel.first", "sel.last")
                except tk.TclError: pass
                widget.insert("insert", text)
            except tk.TclError: pass
            return "break"

        KEYMAP = {65: select_all, 67: copy, 88: cut, 86: paste}
        def on_key(e):
            if e.state & 0x4:
                fn = KEYMAP.get(e.keycode)
                if fn: return fn(e)
        widget.bind("<KeyPress>", on_key)

    def _bind_entry_context_menu(self, widget):
        """Контекстное меню ПКМ для tk.Entry."""
        menu = tk.Menu(widget, tearoff=0,
            bg=BG2, fg=TEXT, activebackground=ACCENT,
            activeforeground="white", bd=0,
            font=("Segoe UI", 9), relief="flat")

        def do_cut():
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.selection_get())
                widget.delete("sel.first", "sel.last")
            except tk.TclError: pass
        def do_copy():
            try:
                widget.clipboard_clear()
                widget.clipboard_append(widget.selection_get())
            except tk.TclError: pass
        def do_paste():
            try:
                text = widget.clipboard_get()
                try: widget.delete("sel.first", "sel.last")
                except tk.TclError: pass
                widget.insert("insert", text)
            except tk.TclError: pass
        def do_select_all():
            widget.select_range(0, "end")
            widget.icursor("end")
        def do_clear():
            widget.delete(0, "end")

        menu.add_command(label="  Вырезать        Ctrl+X", command=do_cut)
        menu.add_command(label="  Копировать     Ctrl+C", command=do_copy)
        menu.add_command(label="  Вставить         Ctrl+V", command=do_paste)
        menu.add_separator()
        menu.add_command(label="  Выделить всё  Ctrl+A", command=do_select_all)
        menu.add_separator()
        menu.add_command(label="  Очистить", command=do_clear)

        def show_menu(e):
            try: menu.tk_popup(e.x_root, e.y_root)
            finally: menu.grab_release()
        widget.bind("<Button-3>", show_menu)

    def _save_message(self):
        self.message_var.set(self.msg_entry.get("1.0", "end").strip())
        self._save_config()
        self._refresh_badges()
        self.msg_ok_lbl.config(text="✓ Сообщение сохранено")
        self.root.after(2000, lambda: self.msg_ok_lbl.config(text=""))

    def _pick_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images","*.png *.jpg *.jpeg *.gif *.webp"),("All","*.*")])
        if path:
            self.image_path = path
            self.img_name_lbl.config(text=os.path.basename(path))
            self._show_img_preview(path)
            self._refresh_badges()

    def _show_img_preview(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((80,80))
            ph = ImageTk.PhotoImage(img)
            self.img_preview.config(image=ph)
            self.img_preview.image = ph
        except:
            pass

    def _clear_image(self):
        self.image_path = None
        self.img_name_lbl.config(text="Файл не выбран")
        self.img_preview.config(image="")
        self._refresh_badges()

    # ── SEND LOGIC ────────────────────────────────────────────────────────────

    def _send_message(self):
        token = self.token_var.get().strip()
        if not token or self.selected_idx < 0 or self.selected_idx >= len(self.channels):
            return False
        ch = self.channels[self.selected_idx]
        text = self.message_var.get().strip()
        url = f"https://discord.com/api/v9/channels/{ch['id']}/messages"
        headers = {"Authorization": token}
        try:
            if self.image_path and os.path.exists(self.image_path):
                with open(self.image_path, "rb") as f:
                    resp = requests.post(url, headers=headers,
                        files={"files[0]": (os.path.basename(self.image_path), f)},
                        data={"payload_json": json.dumps(
                            {"content": text} if text else {})},
                        timeout=15)
            else:
                headers["Content-Type"] = "application/json"
                resp = requests.post(url, headers=headers,
                    json={"content": text}, timeout=15)

            if resp.status_code in (200, 201):
                self.send_count += 1
                n, c = self.send_count, ch['name']
                self.root.after(0, lambda: self._log(f"#{c} — отправлено #{n}", "ok"))
                self.root.after(0, lambda: self._set_status(GREEN, f"#{c} · Отправлено: {n}"))

                return True
            else:
                err = resp.json().get("message", str(resp.status_code))
                self.root.after(0, lambda: self._log(f"Ошибка: {err}", "err"))
                self.root.after(0, lambda: self._set_status(RED, f"Ошибка: {err}"))
                return False
        except Exception as ex:
            self.root.after(0, lambda: self._log(f"Сетевая ошибка: {ex}", "err"))
            self.root.after(0, lambda: self._set_status(RED, "Сетевая ошибка"))
            return False

    def _run_loop(self):
        while self.running:
            self.root.after(0, lambda: self._draw_progress(100))
            self.root.after(0, lambda: self.countdown_lbl.config(text="Отправка..."))
            self._send_message()
            interval_sec = self.interval_var.get() * 60
            start = time.time()
            while self.running:
                if self.stop_event.wait(timeout=0.5):
                    return
                elapsed = time.time() - start
                if elapsed >= interval_sec:
                    break
                remaining = int(interval_sec - elapsed)
                pct = (elapsed / interval_sec) * 100
                m, s = divmod(remaining, 60)
                self.root.after(0, lambda p=pct: self._draw_progress(p))
                self.root.after(0, lambda m=m, s=s: self.countdown_lbl.config(
                    text=f"Следующая отправка через {m}:{s:02d}"))

    def _draw_progress(self, pct):
        w = self.prog_canvas.winfo_width()
        self.prog_canvas.delete("bar")
        if w > 1:
            self.prog_canvas.create_rectangle(
                0, 0, int(w * pct / 100), 5,
                fill=ACCENT, outline="", tags="bar")

    def _start(self):
        if not self.token_var.get().strip():
            messagebox.showwarning("Ошибка", "Задай токен во вкладке 🔑 Токен")
            self._switch_tab("token"); return
        if self.selected_idx < 0 or self.selected_idx >= len(self.channels):
            messagebox.showwarning("Ошибка", "Добавь и выбери канал во вкладке # Каналы")
            self._switch_tab("channels"); return
        if not self.message_var.get().strip() and not self.image_path:
            messagebox.showwarning("Ошибка", "Добавь текст или фото во вкладке ✉ Сообщение")
            self._switch_tab("message"); return

        self.running = True
        self.send_count = 0
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._set_status(GREEN, "Запуск...")
        self._save_config()
        self.timer_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.timer_thread.start()

    def _stop(self):
        self.running = False
        self.stop_event.set()        # немедленно прерывает таймер
        self._save_config()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._draw_progress(0)
        self.countdown_lbl.config(text="")
        self._set_status(MUTED, f"Остановлено · Отправлено: {self.send_count}")

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def _set_status(self, color, text):
        self.status_dot.delete("dot")
        self.status_dot.create_oval(2,2,8,8, fill=color, outline="", tags="dot")
        self.status_lbl.config(text=text)

    def _on_interval(self, val):
        self.interval_lbl.config(text=f"{int(float(val))} мин")

    def _log(self, text, tag=""):
        self.log_text.config(state="normal")
        self.log_text.insert("end",
            f"[{time.strftime('%H:%M:%S')}] {text}\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "token":      self.token_var.get(),
                    "channels":   self.channels,
                    "selected":   self.selected_idx,
                    "interval":   self.interval_var.get(),
                    "message":    self.message_var.get(),
                    "image_path": self.image_path or ""
                }, f, ensure_ascii=False)
        except:
            pass

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, encoding="utf-8") as f:
                    d = json.load(f)
                self.token_var.set(d.get("token",""))
                self.channels      = d.get("channels",[])
                self.selected_idx  = d.get("selected",-1)
                self.interval_var.set(d.get("interval",30))
                self.message_var.set(d.get("message",""))
                img = d.get("image_path","")
                self.image_path = img if img and os.path.exists(img) else None
        except:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = DiscordSenderApp(root)
    root.mainloop()
