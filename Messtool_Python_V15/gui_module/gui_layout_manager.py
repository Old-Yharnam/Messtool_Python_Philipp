"""
GUI Layout Manager - Benutzeroberflächen-Aufbau
===============================================
Erstellt und verwaltet das komplette GUI-Layout:
Frames, Buttons, Eingabefelder, Comboboxen und deren
Positionierung im Hauptfenster.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from PIL import Image, ImageTk
import os
import logging

from Messtool_Python_V15.setup import Cfg

logger = logging.getLogger(__name__)

class GuiLayoutManager:
    """Erstellt und verwaltet das Layout der GUI (Frames, Buttons, Comboboxen)."""

    def __init__(self, gui_manager):
        self.gui = gui_manager
        self.pad_x_medium = 10
        self.pad_y_medium = 8

    def blink_tab(self, tab_index, times=15, interval=300):
        if not hasattr(self.gui, 'bottom_notebook'):
            return
        self._blinking = True
        self._blink_tab_index = tab_index
        notebook = self.gui.bottom_notebook
        original_text = notebook.tab(tab_index, "text")
        style = ttk.Style()

        colors = {0: Cfg.Colors.TAB_INPUT, 1: Cfg.Colors.TAB_OUTPUT}
        blink_color = colors.get(tab_index, "#0d6efd")

        notebook.select(tab_index)

        def do_blink(count):
            if count <= 0:
                self._blinking = False
                notebook.tab(tab_index, text=original_text)
                self._on_tab_changed()
                return
            if count % 2 == 0:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", blink_color), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            else:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", Cfg.Colors.TAB_INACTIVE), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_INACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            notebook.after(interval, lambda: do_blink(count - 1))

        do_blink(times * 2)

        def do_blink(count):
            if count <= 0:
                self._blinking = False
                notebook.tab(tab_index, text=original_text)
                self._on_tab_changed()
                return
            if count % 2 == 0:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", blink_color), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            else:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", Cfg.Colors.TAB_INACTIVE), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_INACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            notebook.after(interval, lambda: do_blink(count - 1))

        do_blink(times * 2)

        def do_blink(count):
            if count <= 0:
                notebook.tab(tab_index, text=original_text)
                self._on_tab_changed()
                return
            if count % 2 == 0:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", blink_color), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            else:
                style.map("Custom.TNotebook.Tab",
                    background=[("selected", Cfg.Colors.TAB_INACTIVE), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                    foreground=[("selected", Cfg.Colors.TAB_TEXT_INACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
                )
            notebook.after(interval, lambda: do_blink(count - 1))

        do_blink(times * 2)

    def _on_tab_changed(self, event=None):
        if getattr(self, '_blinking', False) and event is not None:
            self.gui.bottom_notebook.select(self._blink_tab_index)
            return
        style = ttk.Style()
        notebook = self.gui.bottom_notebook
        selected = notebook.index(notebook.select())
        if selected == 0:
            style.map("Custom.TNotebook.Tab",
                background=[("selected", Cfg.Colors.TAB_INPUT), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
            )
        else:
            style.map("Custom.TNotebook.Tab",
                background=[("selected", Cfg.Colors.TAB_OUTPUT), ("!selected", Cfg.Colors.TAB_INACTIVE)],
                foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
            )

    def create_gui(self):
        """Erstellt ausschließlich das Hauptfenster-Layout."""
        self.gui.root = tb.Window(themename="cosmo")
        self.gui.root.title(Cfg.Texts.WINDOW_TITLE)

        screen_width = self.gui.root.winfo_screenwidth()
        screen_height = self.gui.root.winfo_screenheight()
        self.gui.root.geometry(f"{screen_width}x{screen_height}+0+0")

        main_pane = ttk.Panedwindow(self.gui.root, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew")

        self.gui.root.grid_rowconfigure(0, weight=1)
        self.gui.root.grid_columnconfigure(0, weight=1)

        sidebar_frame = ttk.Frame(main_pane, padding=(0, 0))
        sidebar_frame.pack_propagate(False)
        sidebar_frame.config(width=Cfg.Layout.SIDEBAR_WIDTH)
        main_pane.add(sidebar_frame, weight=0)

        sidebar_canvas = tk.Canvas(sidebar_frame, highlightthickness=0, bd=0)
        sidebar_scrollbar = ttk.Scrollbar(sidebar_frame, orient="vertical", command=sidebar_canvas.yview)
        sidebar_inner = ttk.Frame(sidebar_canvas, padding=(10, 10))

        sidebar_inner.bind("<Configure>", lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_window_id = sidebar_canvas.create_window((0, 0), window=sidebar_inner, anchor="nw")
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        sidebar_canvas.bind("<Configure>", lambda e: sidebar_canvas.itemconfig(sidebar_window_id, width=e.width))

        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sidebar_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_sidebar_mousewheel(event):
            if event.delta:
                sidebar_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            elif event.num == 4:
                sidebar_canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                sidebar_canvas.yview_scroll(3, "units")

        def _bind_mousewheel(event):
            sidebar_canvas.bind_all("<MouseWheel>", _on_sidebar_mousewheel)
            sidebar_canvas.bind_all("<Button-4>", _on_sidebar_mousewheel)
            sidebar_canvas.bind_all("<Button-5>", _on_sidebar_mousewheel)

        def _unbind_mousewheel(event):
            sidebar_canvas.unbind_all("<MouseWheel>")
            sidebar_canvas.unbind_all("<Button-4>")
            sidebar_canvas.unbind_all("<Button-5>")

        sidebar_canvas.bind("<Enter>", _bind_mousewheel)
        sidebar_canvas.bind("<Leave>", _unbind_mousewheel)

        self.gui.sidebar_canvas = sidebar_canvas
        self.gui.sidebar_inner = sidebar_inner

        right_container = ttk.Frame(main_pane, padding=(8, 8))
        main_pane.add(right_container, weight=1)

        right_container.grid_rowconfigure(0, weight=1)
        right_container.grid_columnconfigure(0, weight=1)

        self._create_sidebar_header(sidebar_inner)
        self._create_sidebar_content(sidebar_inner)

        right_pane = ttk.Panedwindow(right_container, orient=tk.VERTICAL)
        right_pane.pack(fill=tk.BOTH, expand=True)

        top_region = ttk.Frame(right_pane, padding=(4, 4))
        mid_region = ttk.Frame(right_pane, padding=(4, 4))
        self.gui.mid_region = mid_region
        bottom_region = ttk.Frame(right_pane, padding=(4, 4))

        right_pane.add(top_region, weight=0)
        right_pane.add(mid_region, weight=1)
        right_pane.add(bottom_region, weight=0)

        self._create_status_bar(top_region)
        self._create_logo_background(mid_region)

        self.gui.bottom_notebook = ttk.Notebook(bottom_region)
        self.gui.bottom_notebook.pack(fill=tk.BOTH, expand=True)

        input_tab = ttk.Frame(self.gui.bottom_notebook)
        output_tab = ttk.Frame(self.gui.bottom_notebook)

        self._create_input_section(input_tab)
        self._create_output_section(output_tab)

        self.gui.bottom_notebook.add(input_tab, text=Cfg.Texts.TAB_EINGABE)
        self.gui.bottom_notebook.add(output_tab, text=Cfg.Texts.TAB_AUSGABE)

        style = ttk.Style()
        style.configure(".", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.TABS))
        style.configure("Custom.TNotebook.Tab", padding=[12, 4], font=(Cfg.Fonts.FAMILY, Cfg.Fonts.TABS))
        style.map("Custom.TNotebook.Tab",
            background=[("selected", Cfg.Colors.TAB_INPUT), ("!selected", Cfg.Colors.TAB_INACTIVE)],
            foreground=[("selected", Cfg.Colors.TAB_TEXT_ACTIVE), ("!selected", Cfg.Colors.TAB_TEXT_INACTIVE)]
        )
        self.gui.bottom_notebook.configure(style="Custom.TNotebook")
        self.gui.bottom_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        return self.gui.root

    def _create_sidebar_header(self, parent):
        # Canvas mit grauem Hintergrund
        canvas = tk.Canvas(
            parent,
            height=70,
            bg=Cfg.Colors.SIDEBAR_HEADER_BG,
            highlightthickness=0
        )
        canvas.pack(fill=tk.X, pady=(0, 10))

        # Dynamische Breite holen
        def draw_rectangles(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()

            # Außen
            canvas.create_rectangle(
                10, 10, w - 10, 60,
                fill=Cfg.Colors.SIDEBAR_INNER_BG,
                outline=""
            )

            # Innen
            canvas.create_rectangle(
                20, 20, w - 20, 50,
                fill=Cfg.Colors.SIDEBAR_TEXT_BG,
                outline=""
            )

            # Text zentriert
            canvas.create_text(
                w // 2, 35,
                text=Cfg.Texts.DASHBOARD,
                fill="white",
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.HEADER, "bold")
            )

        # Redraw bei Größenänderung
        canvas.bind("<Configure>", draw_rectangles)

    def _create_sidebar_content(self, parent):
        """Erstellt alle Sidebar-Sektionen mit nummeriertem Workflow-Design."""

        def create_step_card(parent, step_num, title, color, icon, expand=False):
            colors = Cfg.Colors.CARD_MAP
            bg = colors.get(color, "#6c757d")

            card = tk.Frame(parent, bg=bg, bd=0, relief="flat", highlightthickness=0)
            card.configure(background=bg)
            card.pack(fill=tk.BOTH, expand=expand, pady=(0, 10))

            header = tk.Label(
                card,
                text=f"  {icon}  {step_num}. {title}",
                anchor="w",
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"),
                fg="white",
                bg=bg,
            )
            header.pack(fill=tk.X, padx=8, pady=(6, 4))

            content = ttk.Frame(card)
            content.pack(fill=tk.BOTH, expand=expand, padx=8, pady=(0, 6))

            return content

        # === Hilfsfunktion: Allgemeines-Karte (ohne Nummer) ===
        def create_info_card(parent, title, color, icon="", expand=False):
            colors = Cfg.Colors.CARD_MAP
            bg = colors.get(color, "#6c757d")

            card = tk.Frame(parent, bg=bg, bd=0, relief="flat", highlightthickness=0)
            card.configure(background=bg)
            card.pack(fill=tk.BOTH, expand=expand, pady=(0, 10))

            header = tk.Label(
                card,
                text=f"  {icon}  {title}" if icon else f"  {title}",
                anchor="w",
                font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"),
                fg="white",
                bg=bg,
            )
            header.pack(fill=tk.X, padx=8, pady=(6, 4))

            content = ttk.Frame(card)
            content.pack(fill=tk.BOTH, expand=expand, padx=8, pady=(0, 6))

            return content

        # ========== 1. Datenimport ==========
        import_content = create_step_card(parent, "1", Cfg.Texts.CARD_IMPORT_TITLE, "wine", Cfg.Texts.CARD_IMPORT_ICON)

        self.gui.sheet_combobox = ttk.Combobox(import_content, values=[Cfg.Texts.CB_CSV_DEFAULT], state="readonly")
        self.gui.sheet_combobox.set(Cfg.Texts.CB_CSV_DEFAULT)
        self.gui.sheet_combobox.pack(fill=tk.X, pady=4, padx=6)
        self.gui.sheet_combobox.bind('<<ComboboxSelected>>', self.gui.on_sheet_selected)

        self.gui.import_button = tb.Button(import_content, text=Cfg.Texts.BTN_IMPORT, command=self.gui.load_data, bootstyle="danger", padding=(4, 2))
        self.gui.import_button.pack(fill=tk.X, pady=4, padx=6)

        # ========== 2. Verarbeitung ==========
        ver_content = create_step_card(parent, "2", Cfg.Texts.CARD_VERARBEITUNG_TITLE, "primary", Cfg.Texts.CARD_VERARBEITUNG_ICON)

        self.gui.save_mode = tk.StringVar(value="none")

        self.gui.rb_plots = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_PLOTS, value="plots",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="primary",
        )
        self.gui.rb_plots.state(["disabled"])
        self.gui.rb_plots.pack(fill=tk.X, pady=2, padx=6)

        self.gui.rb_spectrum = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_SPEKTRUM, value="spectrum",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="primary",
        )
        self.gui.rb_spectrum.state(["disabled"])
        self.gui.rb_spectrum.pack(fill=tk.X, pady=2, padx=6)

        self.gui.rb_none = tb.Radiobutton(
            ver_content, text=Cfg.Texts.RB_NICHTS, value="none",
            variable=self.gui.save_mode, command=self.gui.log_save_options, bootstyle="primary",
        )
        self.gui.rb_none.state(["disabled"])
        self.gui.rb_none.pack(fill=tk.X, pady=2, padx=6)

        self.gui.Verarbeitung_button = tb.Button(ver_content, text=Cfg.Texts.BTN_VERARBEITUNG,
                                                  command=self.gui.verarbeitung_button_setup,
                                                  state="disabled", bootstyle="primary", padding=(4, 2))
        self.gui.Verarbeitung_button.pack(fill=tk.X, pady=(6, 4), padx=6)

        # ========== 3. Signalverarbeitung ==========
        sig_content = create_step_card(parent, "3", "Signalverarbeitung", "success", Cfg.Texts.CARD_SIGNAL_ICON)

        self.gui.overview_window_button = tb.Button(sig_content, text=Cfg.Texts.BTN_SIGNALE,
                                                     command=self.gui.show_multi_signal_overlay_window,
                                                     state="disabled", bootstyle="success", padding=(4, 2))
        self.gui.overview_window_button.pack(fill=tk.X, pady=4, padx=6)

        # ========== Allgemeines ==========
        allg_content = create_info_card(parent, Cfg.Texts.CARD_ALLGEMEIN_TITLE, "secondary", Cfg.Texts.CARD_ALLGEMEIN_ICON, expand=False)

        help_button = tb.Button(
            allg_content, text=Cfg.Texts.BTN_HILFE,
            command=self.gui.show_help, bootstyle="secondary", padding=(4, 2)
        )
        help_button.pack(fill=tk.X, pady=(8, 6), padx=6)

        ttk.Separator(allg_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4, padx=6)

        pfad_label = tb.Label(allg_content, text=Cfg.Texts.LBL_PFAD, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM, "bold"))
        pfad_label.pack(anchor="w", pady=(4, 2), padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_HERKUNFTSPFAD,
            command=lambda: self.gui.show_path_window("Datei Herkunftspfad"),
            bootstyle="outline-secondary", padding=(4, 2)
        ).pack(fill=tk.X, pady=2, padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_SPEICHERPFAD,
            command=lambda: self.gui.show_path_window("Spektrum Speicherpfad"),
            bootstyle="outline-secondary", padding=(4, 2)
        ).pack(fill=tk.X, pady=2, padx=6)

        ttk.Separator(allg_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4, padx=6)

        reset_label = tb.Label(allg_content, text=Cfg.Texts.LBL_RESET, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.MEDIUM, "bold"))
        reset_label.pack(anchor="w", pady=(4, 2), padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_RESET_KOMPLETT,
            command=lambda: self.gui.on_reset_selected("Komplett zurücksetzen"),
            bootstyle="outline-warning", padding=(4, 2)
        ).pack(fill=tk.X, pady=2, padx=6)

        tb.Button(
            allg_content, text=Cfg.Texts.BTN_RESET_EINGABE,
            command=lambda: self.gui.on_reset_selected("Nur Eingabefelder zurücksetzen"),
            bootstyle="outline-warning", padding=(4, 2)
        ).pack(fill=tk.X, pady=2, padx=6)

    def _create_input_section(self, parent):
        """Erstellt den Eingabe-Bereich"""
        card = tk.Frame(parent, bg=Cfg.Colors.TAB_INPUT, bd=0, relief="flat", highlightthickness=0)
        card.configure(background=Cfg.Colors.TAB_INPUT)
        card.pack(fill=tk.X, pady=(0, 8))
        header = tk.Label(
            card,
            text="  📥  Eingabedaten",
            anchor="w",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold"),
            fg="white",
            bg=Cfg.Colors.TAB_INPUT,
        )
        header.pack(fill=tk.X, padx=8, pady=(6, 4))
        section = ttk.Frame(card)
        section.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 6))

        self.gui.entry1 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry1.grid(row=0, column=0, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry1.insert(0, Cfg.Ph.START_REIHE)
        self.gui.entry1._is_placeholder = True
        self.gui.entry1.config(state="disabled")

        self.gui.entry2 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry2.grid(row=0, column=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry2.insert(0, Cfg.Ph.END_REIHE)
        self.gui.entry2._is_placeholder = True
        self.gui.entry2.config(state="disabled")

        self.gui.entry3 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry3.grid(row=1, column=0, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry3.insert(0, Cfg.Ph.START_SPALTE)
        self.gui.entry3._is_placeholder = True
        self.gui.entry3.config(state="disabled")

        self.gui.entry4 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry4.grid(row=1, column=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry4.insert(0, Cfg.Ph.END_SPALTE)
        self.gui.entry4._is_placeholder = True
        self.gui.entry4.config(state="disabled")

        self.gui.entry5 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry5.grid(row=2, column=0, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry5.insert(0, Cfg.Ph.SAMPLERATE)
        self.gui.entry5._is_placeholder = True
        self.gui.entry5.config(state="disabled")

        self.gui.entry6 = ttk.Combobox(section, values=Cfg.Defaults.FENSTER_TYPEN, state="disabled")
        self.gui.entry6.set(Cfg.Ph.FENSTERTYP)
        self.gui.entry6.grid(row=2, column=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry6.bind('<<ComboboxSelected>>', self.gui.on_window_function_changed)

        section.columnconfigure(0, weight=1)
        section.columnconfigure(1, weight=1)

    def _create_output_section(self, parent):
        """Erstellt den Ausgabe-Bereich"""
        card = tk.Frame(parent, bg=Cfg.Colors.TAB_OUTPUT, bd=0, relief="flat", highlightthickness=0)
        card.configure(background=Cfg.Colors.TAB_OUTPUT)
        card.pack(fill=tk.X, pady=(0, 8))

        header = tk.Label(
            card,
            text="  📤  Ausgabedaten",
            anchor="w",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold"),
            fg="white",
            bg=Cfg.Colors.TAB_OUTPUT,
        )
        header.pack(fill=tk.X, padx=8, pady=(6, 4))

        section = ttk.Frame(card)
        section.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 6))

        self.gui.entry9 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry9.grid(row=0, column=0, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry9.delete(0, tk.END)
        self.gui.entry9.insert(0, Cfg.Ph.SAMPLES)
        self.gui.entry9.configure(style="EntryPlaceholder.TEntry", state="readonly")
        self.gui.entry9._is_placeholder = True

        self.gui.entry7 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry7.grid(row=0, column=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry7.delete(0, tk.END)
        self.gui.entry7.insert(0, Cfg.Ph.STARTZEIT)
        self.gui.entry7.configure(style="EntryPlaceholder.TEntry", state="readonly")
        self.gui.entry7._is_placeholder = True

        self.gui.entry10 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry10.grid(row=1, column=0, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry10.delete(0, tk.END)
        self.gui.entry10.insert(0, Cfg.Ph.DT)
        self.gui.entry10.configure(style="EntryPlaceholder.TEntry", state="readonly")
        self.gui.entry10._is_placeholder = True

        self.gui.entry8 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry8.grid(row=1, column=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry8.delete(0, tk.END)
        self.gui.entry8.insert(0, Cfg.Ph.ENDZEIT)
        self.gui.entry8.configure(style="EntryPlaceholder.TEntry", state="readonly")
        self.gui.entry8._is_placeholder = True

        self.gui.entry11 = ttk.Entry(section, state="normal", style="EntryPlaceholder.TEntry")
        self.gui.entry11.grid(row=2, column=0, columnspan=1, pady=2, padx=8, sticky=tk.EW)
        self.gui.entry11.delete(0, tk.END)
        self.gui.entry11.insert(0, Cfg.Ph.DF)
        self.gui.entry11.configure(style="EntryPlaceholder.TEntry", state="readonly")
        self.gui.entry11._is_placeholder = True

        section.columnconfigure(0, weight=1)
        section.columnconfigure(1, weight=1)

    def _create_status_bar(self, parent):
        """Erstellt eine Status-Leiste (ohne Logo)."""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        status_row = ttk.Frame(status_frame)
        status_row.pack(pady=(0, 5))

        self.gui.status_label = ttk.Label(status_row, text=Cfg.Texts.STATUS_BEREIT, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.STATUS))
        self.gui.status_label.pack(side=tk.LEFT, padx=(0, 10))

        self.gui.progress_label = ttk.Label(status_row, text="", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.STATUS))
        self.gui.progress_label.pack(side=tk.LEFT, padx=10)

        self.gui.flood_gauge = tb.Floodgauge(
            status_row,
            bootstyle="primary",
            text="Daten werden geladen...",
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL),
            length=200,
            mode="indeterminate",
        )
        self.gui.flood_gauge.pack(side=tk.LEFT, padx=10)
        self.gui.flood_gauge.pack_forget()

    def _create_logo_background(self, parent):
        """Stadler-Logo als Hintergrundbild in der Mid-Region."""
        try:
            bild_pfad = self.gui.get_resource_path("docs_bilder/stadler_blue_rgb.png")
            bild = Image.open(bild_pfad)
            stadler_width = Cfg.Layout.LOGO_WIDTH
            stadler_height = int(stadler_width * Cfg.Layout.LOGO_ASPECT)
            bild = bild.resize((stadler_width, stadler_height), Image.Resampling.LANCZOS)
            self.gui.stadler_img = ImageTk.PhotoImage(bild)

            logo_label = ttk.Label(parent, image=self.gui.stadler_img)
            logo_label.place(relx=0.5, rely=0.5, anchor="center")
            self.gui._logo_label = logo_label
        except Exception:
            logger.warning("Stadler-Logo konnte nicht geladen werden")

    def create_filter_characteristic_layout(self, filter_info):
        """Erstellt das reine Layout für die Filter-Charakteristik."""
        self.gui.characteristic_window = tb.Toplevel(self.gui.root)
        self.gui.characteristic_window.title("Filter-Charakteristik")
        self.gui.characteristic_window.geometry("1200x700")

        main_frame = ttk.Frame(self.gui.characteristic_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_frame = ttk.LabelFrame(main_frame, text="Filter-Parameter", padding=(10, 5))
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_labels = [
            ("Filtertyp:", filter_info.get('type', 'Unbekannt')),
            ("Charakteristik:", filter_info.get('characteristic', 'Unbekannt')),
            ("Ordnung:", str(filter_info.get('order', '-'))),
            ("Abtastrate:", f"{filter_info.get('sample_rate', '-')} Hz"),
            ("Grenzfrequenz 1:", f"{filter_info.get('cutoff', '-')} Hz"),
            ("Grenzfrequenz 2:", f"{filter_info.get('cutoff2', '-')} Hz" if filter_info.get('cutoff2') else "-"),
        ]

        for i, (label, value) in enumerate(info_labels):
            ttk.Label(info_frame, text=label, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE, "bold")).grid(row=0, column=i * 2, sticky="e", padx=5, pady=2)
            ttk.Label(info_frame, text=value, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE)).grid(row=0, column=i * 2 + 1, sticky="w", padx=5, pady=2)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        plot_frame = ttk.LabelFrame(content_frame, text="Frequenzgang", padding=(5, 5))
        plot_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.gui.filter_fig = plt.Figure(figsize=(7, 5))
        self.gui.filter_canvas = FigureCanvasTkAgg(self.gui.filter_fig, master=plot_frame)
        self.gui.filter_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        coef_frame = ttk.LabelFrame(content_frame, text="Filter-Koeffizienten", padding=(10, 5))
        coef_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        text_scroll = ttk.Scrollbar(coef_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        info_text_widget = ttk.Treeview(
            coef_frame,
            columns=("line",),
            show="headings",
            selectmode="browse",
            yscrollcommand=text_scroll.set,
        )
        info_text_widget.heading("line", text="Information")
        info_text_widget.column("line", anchor="w", stretch=True, width=520)
        info_text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        text_scroll.config(command=info_text_widget.yview)

        return {
            "window": self.gui.characteristic_window,
            "info_text_widget": info_text_widget,
        }

    def create_signal_selection_layout(self, on_window_close):
        """Erstellt das Layout des Signalauswahl-Bereichs in der Mid-Region."""
        for widget in self.gui.mid_region.winfo_children():
            if widget != getattr(self.gui, '_logo_label', None):
                widget.destroy()

        select_window = ttk.Frame(self.gui.mid_region)
        select_window.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(select_window)
        header_frame.pack(fill=tk.X, padx=10, pady=(5, 0))

        ttk.Label(header_frame, text="Wähle die Signale aus, die angezeigt werden sollen:",
                  font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE)).pack(side=tk.LEFT)

        close_btn = tb.Button(header_frame, text="✕ Schließen",
                              command=on_window_close, bootstyle="outline-danger")
        close_btn.pack(side=tk.RIGHT)

        search_var = tk.StringVar()
        search_entry = ttk.Entry(select_window, textvariable=search_var, font=(Cfg.Fonts.FAMILY, Cfg.Fonts.LARGE))
        search_entry.pack(pady=5, padx=10, fill=tk.X)

        selected_display_var = tk.StringVar(value="Keine Signale ausgewählt")
        selected_display_style = ttk.Style()
        selected_display_style.configure("SelectedDisplay.TEntry", foreground="blue")
        selected_display = ttk.Entry(
            select_window,
            textvariable=selected_display_var,
            font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL),
            state="readonly",
            style="SelectedDisplay.TEntry",
        )
        selected_display.pack(pady=5, padx=10, fill=tk.X)

        list_frame = ttk.Frame(select_window)
        list_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        listbox = ttk.Treeview(list_frame, show="tree", selectmode="extended")
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=list_scrollbar.set)

        groups_frame = ttk.LabelFrame(select_window, text="Signal-Gruppen", padding=(8, 6))
        groups_frame.pack(padx=10, pady=6, fill=tk.X)

        groups_container = ttk.Frame(groups_frame)
        groups_container.pack(fill=tk.BOTH, expand=True)

        group_buttons_frame = ttk.Frame(groups_frame)
        group_buttons_frame.pack(fill=tk.X, pady=5)

        opts_frame = ttk.LabelFrame(select_window, text="Optionen", padding=(8, 6))
        opts_frame.pack(padx=10, pady=6, fill=tk.X)

        actions_frame = ttk.Frame(select_window)
        actions_frame.pack(pady=10)

        return {
            "select_window": select_window,
            "search_var": search_var,
            "search_entry": search_entry,
            "selected_display_var": selected_display_var,
            "listbox": listbox,
            "groups_container": groups_container,
            "group_buttons_frame": group_buttons_frame,
            "opts_frame": opts_frame,
            "actions_frame": actions_frame,
        }

    def create_live_plot_layout(self, selected_signal):
        """Erstellt das reine Layout eines Live-Plot-Fensters."""
        plot_window = tb.Toplevel(self.gui.root)
        plot_window.title(f"Plot: {selected_signal}")
        plot_window.geometry("1200x700")

        plot_frame = ttk.Frame(plot_window)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig = plt.Figure(figsize=(16, 12))
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        NavigationToolbar2Tk(canvas, toolbar_frame)

        options_frame = ttk.LabelFrame(plot_frame, text="Anzeige", padding=(8, 6))
        options_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        analysis_frame = ttk.LabelFrame(plot_frame, text="Analyse", padding=(8, 6))
        analysis_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 8))

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        return {
            "window": plot_window,
            "fig": fig,
            "canvas": canvas,
            "toolbar_frame": toolbar_frame,
            "options_frame": options_frame,
            "analysis_frame": analysis_frame,
        }
