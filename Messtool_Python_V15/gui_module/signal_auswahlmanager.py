"""
Signal Auswahlmanager - Signalauswahl-Verwaltung
================================================
Verwaltet das Signalauswahl-Fenster mit Listbox,
Gruppen-Management und Export-Funktionen.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as tb
import numpy as np
import logging
from hilfsklassen.zentrales_logging import get_protocol_logger

logger = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

from gui_module.plot_manager import PlotManager
from hilfsklassen.daten_verarbeiter import DataProcessor
from Messtool_Python_V15.setup import Cfg


class SignalAuswahlManager:
    """Verwaltet das Signal-Auswahl-Fenster"""

    def __init__(self, gui_manager, plot_window_manager):
        self.gui = gui_manager
        self.plot_window_manager = plot_window_manager
        self.filter_char_button = None

    def show_multi_signal_overlay_window(self, active_window=None):
        """Öffnet ein Fenster zur Auswahl beliebig vieler Signale und zeigt sie gemeinsam in einem Plot."""
        protocol_logger.info("OVERLAY_WINDOW_OPEN")

        # Prüfen ob bereits ein Fenster geöffnet ist
        if active_window is not None:
            try:
                if active_window.winfo_exists():
                    return
                else:
                    active_window = None
            except:
                active_window = None

        if not self.gui.signals or not self.gui.headers or self.gui.t is None:
            logger.info("Keine Daten verfügbar")
            return

        exclude_columns = Cfg.Data.EXCLUDE_COLUMNS
        selectable_headers = [
            h for i, h in enumerate(self.gui.headers)
            if h not in exclude_columns and i < len(self.gui.signals)
        ]

        def get_unit(h):
            idx = self.gui.headers.index(h)
            if idx < len(self.gui.units):
                return self.gui.units[idx].lower()
            return ""
        selectable_headers.sort(key=get_unit)

        header_to_signal_idx = {
            h: self.gui.headers.index(h) for h in selectable_headers
            if self.gui.headers.index(h) < len(self.gui.signals)
        }

        unit_colors = {}
        color_palette = Cfg.Colors.UNIT_PALETTE

        unique_units = sorted(set(
            self.gui.units[self.gui.headers.index(h)].strip()
            if self.gui.headers.index(h) < len(self.gui.units) else ""
            for h in selectable_headers
        ))
        for i, unit in enumerate(unique_units):
            unit_colors[unit] = color_palette[i % len(color_palette)]

        selected_list = []
        last_clicked_index = [None]

        select_window = None

        def on_window_close():
            self.plot_window_manager.active_signal_window = None
            if hasattr(self.gui, 'overview_window_button'):
                self.gui.overview_window_button.config(state="normal")
            if select_window is not None:
                select_window.destroy()

        layout = self.gui.layout_manager.create_signal_selection_layout(on_window_close)
        select_window = layout["select_window"]

        self.plot_window_manager.active_signal_window = select_window

        if hasattr(self.gui, 'overview_window_button'):
            self.gui.overview_window_button.config(state="disabled")

        search_var = layout["search_var"]
        search_entry = layout["search_entry"]
        selected_display_var = layout["selected_display_var"]

        def update_selected_display():
            if selected_list:
                selected_display_var.set(", ".join(selected_list))
            else:
                selected_display_var.set(Cfg.Texts.STATUS_KEIN_SIGNAL)

        listbox = layout["listbox"]

        visible_items = []

        def selection_clear_all():
            selected = listbox.selection()
            if selected:
                listbox.selection_remove(*selected)

        def selection_set_index(index: int):
            item_ids = listbox.get_children("")
            if 0 <= index < len(item_ids):
                listbox.selection_add(item_ids[index])

        def selection_clear_index(index: int):
            item_ids = listbox.get_children("")
            if 0 <= index < len(item_ids):
                listbox.selection_remove(item_ids[index])

        def get_selected_indices():
            item_ids = listbox.get_children("")
            selected = set(listbox.selection())
            return [i for i, iid in enumerate(item_ids) if iid in selected]

        def nearest_index(y_pos: int):
            item_ids = listbox.get_children("")
            if not item_ids:
                return -1
            row_id = listbox.identify_row(y_pos)
            if not row_id:
                return -1
            try:
                return item_ids.index(row_id)
            except ValueError:
                return -1

        def update_listbox(filter_text: str = ""):
            nonlocal visible_items
            current_items = listbox.get_children()
            if current_items:
                listbox.delete(*current_items)
            ft = filter_text.lower().strip()
            source = selectable_headers
            visible_items = [h for h in source if ft in h.lower()] if ft else source

            if not visible_items:
                placeholder = "Kein Signal gefunden"
                listbox.insert("", tk.END, text=placeholder)
                selection_clear_all()
                return

            for unit, color in unit_colors.items():
                tag_name = f"unit_{unit}" if unit else "unit_none"
                listbox.tag_configure(tag_name, background=color)

            for h in visible_items:
                idx = self.gui.headers.index(h)
                unit = self.gui.units[idx].strip() if idx < len(self.gui.units) else ""
                tag_name = f"unit_{unit}" if unit else "unit_none"
                listbox.insert("", tk.END, text=h, tags=(tag_name,))

            selection_clear_all()
            for i, h in enumerate(visible_items):
                if h in selected_list:
                    selection_set_index(i)

        update_listbox()

        # Gruppen-Anzeige-Frame
        style = ttk.Style(select_window)
        style.configure("Group.TFrame")
        style.configure("GroupSelected.TFrame", background=Cfg.Colors.GROUP_SELECTED_BG)
        style.configure("Group.TLabel", foreground=Cfg.Colors.GROUP_LABEL)
        style.configure("GroupSelected.TLabel", foreground=Cfg.Colors.GROUP_LABEL, background=Cfg.Colors.GROUP_SELECTED_BG)
        groups_container = layout["groups_container"]

        selected_group_indices = {"indices": []}

        def update_group_display():
            """Aktualisiert die Anzeige aller Gruppen"""
            for widget in groups_container.winfo_children():
                widget.destroy()

            for i, group in enumerate(self.gui.signal_groups):
                is_selected = i in selected_group_indices["indices"]

                group_frame = ttk.Frame(groups_container)
                group_frame.pack(fill=tk.X, padx=5, pady=2)

                if is_selected: group_frame.configure(relief="solid", borderwidth=2)

                signal_text = ", ".join(group[:3])
                if len(group) > 3:
                    signal_text += "..."

                group_label = ttk.Label(
                    group_frame,
                    text=f"Gruppe {i+1}: ({signal_text})",
                    font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold") if is_selected else (Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL),
                    anchor="w",
                )
                group_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

                if len(group) > 3:
                    def _show_all_signals(group_idx=i):
                        group_signals = self.gui.signal_groups[group_idx]
                        all_signals = "\n".join(group_signals)
                        messagebox.showinfo(
                            f"Gruppe {group_idx+1} - Alle Signale",
                            all_signals
                        )

                    mehr_button = ttk.Button(group_frame, text="mehr", command=_show_all_signals)
                    mehr_button.pack(side=tk.RIGHT, padx=5)

                def _make_group_click_handler(idx):
                    return lambda event: _select_group(idx)

                group_label.bind("<Button-1>", _make_group_click_handler(i))
                group_frame.bind("<Button-1>", _make_group_click_handler(i))

        def _select_group(idx: int):
            """Wählt/Entwählt eine Gruppe (Toggle)"""
            if idx >= len(self.gui.signal_groups):
                return

            if idx in selected_group_indices["indices"]:
                selected_group_indices["indices"].remove(idx)
            else:
                selected_group_indices["indices"].append(idx)

            update_group_display()

        update_group_display()

        group_selection_active = {"active": False}
        opts_frame_ref = {"frame": None}
        action_widgets = []

        def _set_children_state(parent, enabled: bool):
            """Aktiviert/Deaktiviert rekursiv alle untergeordneten Widgets"""
            for child in parent.winfo_children():
                try:
                    if isinstance(child, ttk.Widget):
                        child.state(["!disabled"] if enabled else ["disabled"])
                    else:
                        child.config(state="normal" if enabled else "disabled")
                except Exception:
                    pass
                _set_children_state(child, enabled)

        def set_group_selection_mode(active: bool):
            """Schaltet den Gruppenauswahl-Modus ein/aus"""
            group_selection_active["active"] = active
            if opts_frame_ref["frame"] is not None:
                _set_children_state(opts_frame_ref["frame"], not active)
            for widget in action_widgets:
                try:
                    if isinstance(widget, ttk.Widget):
                        widget.state(["!disabled"] if not active else ["disabled"])
                    else:
                        widget.config(state="normal" if not active else "disabled")
                except Exception:
                    pass

        def create_group_manually():
            """Erstellt eine neue Gruppe"""
            if not group_selection_active["active"]:
                if not get_selected_indices() and not selected_list:
                    set_group_selection_mode(True)
                    messagebox.showinfo(
                        "Signale auswählen",
                        "Bitte wählen Sie die Signale für die Gruppe aus.\n"
                        "Hinweis: Am besten ähnliche Signale für eine übersichtliche Gruppe.",
                        parent=select_window
                    )
                    return

            selected_list[:] = [
                visible_items[i]
                for i in get_selected_indices()
                if i < len(visible_items)
            ]

            if len(selected_list) <= 3:
                messagebox.showwarning(
                    "Zu wenige Signale",
                    "Bitte mehr als 3 Signale auswählen, um eine Gruppe zu erstellen.",
                    parent=select_window
                )
                return

            if len(self.gui.signal_groups) >= self.gui.max_groups:
                messagebox.showwarning(
                    "Maximale Gruppen erreicht",
                    f"Es können maximal {self.gui.max_groups} Gruppen erstellt werden.",
                    parent=select_window
                )
                return

            self.gui.signal_groups.append(selected_list.copy())
            messagebox.showinfo(
                "Gruppe erstellt",
                f"Gruppe {len(self.gui.signal_groups)} wurde erstellt mit {len(selected_list)} Signal(en).",
                parent=select_window
            )

            selected_list.clear()
            selection_clear_all()
            update_selected_display()
            update_group_display()
            set_group_selection_mode(False)

        def cancel_group_selection():
            """Bricht die Gruppenauswahl ab oder löscht Gruppen"""
            if group_selection_active["active"]:
                selected_list.clear()
                selection_clear_all()
                update_selected_display()
                set_group_selection_mode(False)
                return

            if not selected_group_indices["indices"]:
                messagebox.showinfo(
                    "Keine Gruppe gewählt",
                    "Bitte mindestens eine Gruppe anklicken.",
                    parent=select_window
                )
                return

            anzahl = len(selected_group_indices["indices"])
            if anzahl == 1:
                idx = selected_group_indices["indices"][0]
                result = messagebox.askyesno(
                    "Gruppe löschen",
                    f"Möchten Sie Gruppe {idx + 1} wirklich löschen?",
                    parent=select_window
                )
            else:
                gruppen_text = ", ".join([f"Gruppe {i+1}" for i in sorted(selected_group_indices["indices"])])
                result = messagebox.askyesno(
                    "Gruppen löschen",
                    f"Möchten Sie wirklich {anzahl} Gruppen löschen?\n\n{gruppen_text}",
                    parent=select_window
                )

            if result:
                for idx in sorted(selected_group_indices["indices"], reverse=True):
                    if idx < len(self.gui.signal_groups):
                        del self.gui.signal_groups[idx]

                selected_group_indices["indices"].clear()
                update_group_display()

        # Buttons für Gruppen-Verwaltung
        group_buttons_frame = layout["group_buttons_frame"]

        ttk.Button(group_buttons_frame, text=Cfg.Texts.BTN_GRUPPE_ERSTELLEN, command=create_group_manually).pack(side=tk.LEFT, padx=5)
        ttk.Button(group_buttons_frame, text=Cfg.Texts.BTN_GRUPPE_LOESCHEN, command=cancel_group_selection).pack(side=tk.LEFT, padx=5)

        opts_frame = layout["opts_frame"]
        opts_frame_ref["frame"] = opts_frame

        show_avg_var = tk.BooleanVar(value=False)
        show_rms_var = tk.BooleanVar(value=False)
        show_diff_var = tk.BooleanVar(value=False)
        show_integral_var = tk.BooleanVar(value=False)
        show_fft_var = tk.BooleanVar(value=False)
        show_varianz_var = tk.BooleanVar(value=False)

        show_filtered_var = self.gui.use_filtered_var

        warning_shown = False

        def on_listbox_click(event):
            """Behandelt Klicks auf die Listbox mit Shift-Unterstützung"""
            nonlocal selected_list
            nonlocal warning_shown

            clicked_index = nearest_index(event.y)
            if clicked_index < 0 or clicked_index >= len(visible_items):
                return

            clicked_header = visible_items[clicked_index]

            if event.state & 0x1:  # Shift-Taste
                if last_clicked_index[0] is not None:
                    start = min(last_clicked_index[0], clicked_index)
                    end = max(last_clicked_index[0], clicked_index)

                    for i in range(start, end + 1):
                        if i < len(visible_items):
                            header = visible_items[i]
                            if header not in selected_list:
                                selected_list.append(header)
                            selection_set_index(i)
                else:
                    if clicked_header in selected_list:
                        selected_list.remove(clicked_header)
                        selection_clear_index(clicked_index)
                    else:
                        selected_list.append(clicked_header)
                        selection_set_index(clicked_index)
            else:
                if clicked_header in selected_list:
                    selected_list.remove(clicked_header)
                    selection_clear_index(clicked_index)
                else:
                    selected_list.append(clicked_header)
                    selection_set_index(clicked_index)

            if len(selected_list) >= 4 and not group_selection_active["active"] and not warning_shown:
                warning_shown = True
                messagebox.showwarning(
                    "Hinweis: Viele Signale ausgewählt",
                    "Es wird empfohlen, ab 3 Signalen eine Gruppe zu erstellen\n"
                    "für bessere Übersichtlichkeit und Performance.\n\n"
                    "Sie können aber weiterhin alle Signale einzeln plotten.",
                    parent=select_window
                )

            last_clicked_index[0] = clicked_index
            update_selected_display()

        listbox.bind("<ButtonRelease-1>", on_listbox_click)

        def open_filter_popup():
            protocol_logger.info("FILTER_DIALOG_OPEN")
            popup = tb.Toplevel(select_window)
            popup.title("Filter einstellen")
            popup.geometry("500x220")
            popup.transient(select_window)
            popup.grab_set()

            ttk.Label(popup, text="Filter wählen:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
            filter_type_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_TYPEN, state="readonly", width=20)
            filter_type_cb.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="ew")

            ttk.Label(popup, text="Grenzfrequenz 1 z.B. 2").grid(row=1, column=0, padx=10, pady=5, sticky="w")
            freq1_entry = ttk.Entry(popup, width=15)
            freq1_entry.insert(0, str(Cfg.Defaults.GRENZFREQUENZ_1))
            freq1_entry.config(state="disabled")
            freq1_entry.grid(row=1, column=1, padx=10, pady=5)

            ttk.Label(popup, text="Grenzfrequenz 2 z.B. 6").grid(row=1, column=2, padx=10, pady=5, sticky="w")
            freq2_entry = ttk.Entry(popup, width=15)
            freq2_entry.insert(0, str(Cfg.Defaults.GRENZFREQUENZ_2))
            freq2_entry.config(state="disabled")
            freq2_entry.grid(row=1, column=3, padx=10, pady=5)

            char_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_CHARAKTERISTIKEN, state="disabled", width=20)
            char_cb.set("Charakteristik auswählen:")
            char_cb.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

            order_cb = ttk.Combobox(popup, values=Cfg.Defaults.FILTER_ORDNUNGEN, state="disabled", width=20)
            order_cb.set("Ordnung auswählen:")
            order_cb.grid(row=2, column=2, columnspan=2, padx=10, pady=5, sticky="ew")

            def on_filter_type_change(event=None):
                ftype = filter_type_cb.get()
                if ftype == Cfg.Defaults.FILTER_TYP:
                    freq1_entry.config(state="disabled")
                    freq2_entry.config(state="disabled")
                    char_cb.config(state="disabled")
                    order_cb.config(state="disabled")
                elif ftype == "Bandpass":
                    freq1_entry.config(state="normal")
                    freq2_entry.config(state="normal")
                    char_cb.config(state="readonly")
                    order_cb.config(state="readonly")
                else:
                    freq1_entry.config(state="normal")
                    freq2_entry.config(state="disabled")
                    char_cb.config(state="readonly")
                    order_cb.config(state="readonly")

            filter_type_cb.bind("<<ComboboxSelected>>", on_filter_type_change)

            def apply_filter():
                ftype = filter_type_cb.get()
                defaults_used = False

                if ftype == Cfg.Defaults.FILTER_TYP or ftype == "":
                    ftype = "Tiefpass"
                    filter_type_cb.set(ftype)
                    defaults_used = True

                freq1 = freq1_entry.get().strip()
                freq2_str = freq2_entry.get().strip()

                # VALIDIERUNG: Bandpass benötigt BEIDE Frequenzen
                if ftype == "Bandpass":
                    if not freq1 or not freq2_str:
                        messagebox.showerror(
                            "Fehler - Fehlende Grenzfrequenz",
                            "Bandpass-Filter benötigt BEIDE Grenzfrequenzen!\n\n"
                            "Bitte geben Sie sowohl die untere als auch die obere Grenzfrequenz ein."
                        )
                        return

                    try:
                        freq1_float = float(freq1)
                        freq2_float = float(freq2_str)
                    except ValueError:
                        messagebox.showerror(
                            "Fehler - Ungültige Eingabe",
                            "Beide Grenzfrequenzen müssen gültige Zahlen sein!"
                        )
                        return

                    if freq1_float >= freq2_float:
                        messagebox.showerror(
                            "Fehler - Ungültige Frequenzreihenfolge",
                            f"Die untere Grenzfrequenz ({freq1_float} Hz) muss kleiner sein\n"
                            f"als die obere Grenzfrequenz ({freq2_float} Hz)!"
                        )
                        return

                if freq1 == "" or freq1 == str(Cfg.Defaults.GRENZFREQUENZ_1):
                    freq1 = str(Cfg.Defaults.GRENZFREQUENZ_1)
                    defaults_used = True

                characteristic = char_cb.get()
                if characteristic == "" or characteristic == "Charakteristik auswählen:":
                    characteristic = Cfg.Defaults.FILTER_CHARAKTERISTIK
                    char_cb.set(characteristic)
                    defaults_used = True

                order = order_cb.get()
                if order == "" or order == "Ordnung auswählen:":
                    order = Cfg.Defaults.FILTER_ORDNUNG
                    order_cb.set(order)
                    defaults_used = True

                if defaults_used:
                    messagebox.showinfo("Standardwerte", "Default Werte übernommen")

                order_int = 1
                try:
                    order_int = int(order.split('.')[0])
                except (ValueError, IndexError):
                    order_int = 1

                try:
                    freq1_float = float(freq1)
                except ValueError:
                    freq1_float = float(Cfg.Defaults.GRENZFREQUENZ_1)

                freq2_float = None
                freq2_str = freq2_entry.get().strip()
                if freq2_str:
                    try:
                        freq2_float = float(freq2_str)
                    except ValueError:
                        freq2_float = None

                fs = float(Cfg.Defaults.SAMPLERATE)
                try:
                    fs_text = self.gui.entry5.get().strip()
                    if fs_text and fs_text != "Samplefrequenz z.B. 20":
                        fs = float(fs_text)
                except (ValueError, AttributeError):
                    fs = 20.0

                self.gui.filter_manager.set_filter_parameters(ftype, freq1_float, fs, cutoff_frequency2=freq2_float)
                self.gui.filter_manager.set_filter_characteristics(characteristic, order_int)

                protocol_logger.info(
                    "FILTER_SET type=%s | cutoff1=%s | cutoff2=%s | characteristic=%s | order=%s | fs=%s",
                    ftype,
                    freq1_float,
                    freq2_float,
                    characteristic,
                    order_int,
                    fs,
                )

                if ftype == Cfg.Defaults.FILTER_TYP:
                    show_filtered_var.set(False)
                else:
                    show_filtered_var.set(True)
                    if hasattr(self, "filter_char_button"):
                        self.filter_char_button.config(state="normal")

                self.plot_window_manager.update_all_plot_windows()
                popup.destroy()

            filter_type_cb.set(self.gui.filter_manager.filter_type if self.gui.filter_manager.filter_type else "Tiefpass")
            if self.gui.filter_manager.cutoff_frequency:
                freq1_entry.config(state="normal")
                freq1_entry.delete(0, tk.END)
                freq1_entry.insert(0, str(self.gui.filter_manager.cutoff_frequency))
            if self.gui.filter_manager.cutoff_frequency2:
                freq2_entry.config(state="normal")
                freq2_entry.delete(0, tk.END)
                freq2_entry.insert(0, str(self.gui.filter_manager.cutoff_frequency2))
            if self.gui.filter_manager.characteristic:
                char_cb.set(self.gui.filter_manager.characteristic)
            if self.gui.filter_manager.order:
                order_cb.set(f"{self.gui.filter_manager.order}.Ordnung")
            on_filter_type_change()
            ttk.Button(popup, text="Anwenden", command=apply_filter).grid(row=3, column=1, columnspan=2, pady=15)

        def on_filtered_master_toggled():
            """Handler für Filter-Master-Toggle"""
            self.plot_window_manager.update_all_plot_windows()

        ttk.Button(opts_frame, text=Cfg.Texts.BTN_FILTER, command=open_filter_popup).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Filter aktiv", variable=self.gui.use_filtered_var, command=on_filtered_master_toggled).pack(side=tk.LEFT, padx=6)

        self.filter_char_button = ttk.Button(opts_frame, text="Filtercharakteristik", state="disabled", command=lambda: self.gui.ui_control.show_filter_characteristic_window())
        self.filter_char_button.pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(opts_frame, text="AVG", variable=show_avg_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="RMS", variable=show_rms_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Differential", variable=show_diff_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Integral", variable=show_integral_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="FFT", variable=show_fft_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(opts_frame, text="Statistik", variable=show_varianz_var).pack(side=tk.LEFT, padx=6)

        def on_search_change(*args):
            update_listbox(search_var.get())

        search_var.trace_add("write", on_search_change)

        def _get_selected_groups():
            """Gibt ausgewählte Gruppen als Liste von Signallisten zurück"""
            selected_groups = []
            for idx in sorted(selected_group_indices["indices"]):
                if idx < len(self.gui.signal_groups):
                    group = self.gui.signal_groups[idx]
                    if group:
                        selected_groups.append(group)
            return selected_groups

        def plot_selected():
            """Button-Callback - öffnet Notebook mit Tabs für jede Analyseart"""
            selected_groups = _get_selected_groups()
            grouped_headers = None

            if selected_groups:
                grouped_headers = [list(dict.fromkeys(group)) for group in selected_groups]
                effective_selected = [h for group in grouped_headers for h in group]
            else:
                effective_selected = selected_list.copy()

            if not effective_selected:
                self.gui.status_label.config(text="Keine Signale ausgewählt.")
                return

            selected_analyses = []
            if show_avg_var.get():
                selected_analyses.append("AVG")
            if show_rms_var.get():
                selected_analyses.append("RMS")
            if show_fft_var.get():
                selected_analyses.append("FFT")
            if show_diff_var.get():
                selected_analyses.append("Differential")
            if show_integral_var.get():
                selected_analyses.append("Integral")
            if show_varianz_var.get():
                selected_analyses.append("Statistik")

            if not selected_analyses:
                selected_analyses = ["Signal"]

            self.gui.selected_signal = effective_selected[-1]
            self.gui.selected_signals = effective_selected.copy()

            zeitbereich_analysen = [a for a in selected_analyses if a in ["AVG", "RMS", "FFT"]]
            direkt_analysen = [a for a in selected_analyses if a not in ["AVG", "RMS", "FFT"]]

            signal_indices = []
            for signal_name in effective_selected:
                try:
                    signal_indices.append(self.gui.headers.index(signal_name))
                except ValueError:
                    continue

            use_filtered = self.gui.use_filtered_var.get() and self.gui._is_filter_ready()

            protocol_logger.info(
                "PLOT_SELECTION signals=%s | analyses=%s | filtered=%s | grouped=%s",
                effective_selected,
                selected_analyses,
                use_filtered,
                bool(selected_groups),
            )

            if zeitbereich_analysen:
                t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

                selected_signal = ", ".join(effective_selected[:3])
                if len(effective_selected) > 3:
                    selected_signal += f" (+{len(effective_selected) - 3} weitere)"

                is_filtered = use_filtered
                filter_info = None
                if is_filtered and hasattr(self.gui, 'filter_manager'):
                    filter_info = self.gui.filter_manager.get_filter_info()

                def on_zeitbereich(result):
                    alle_analysen = zeitbereich_analysen + direkt_analysen
                    if not alle_analysen:
                        alle_analysen = ["Signal"]

                    self.plot_window_manager._create_notebook_window(
                        select_window=select_window,
                        selected_list=effective_selected,
                        signal_indices=signal_indices,
                        selected_analyses=alle_analysen,
                        header_to_signal_idx=header_to_signal_idx,
                        use_filtered=use_filtered,
                        zeitbereiche_dict=result,
                        grouped_headers=grouped_headers
                    )

                PlotManager.show_zeitbereich_dialog(
                    parent=select_window,
                    t_max=t_max,
                    callback=on_zeitbereich,
                    title="Zeitbereich für Analyse auswählen",
                    selected_signal=selected_signal,
                    is_filtered=is_filtered,
                    filter_info=filter_info,
                    analyse_typen=zeitbereich_analysen
                )
            else:
                self.plot_window_manager._create_notebook_window(
                    select_window=select_window,
                    selected_list=effective_selected,
                    signal_indices=signal_indices,
                    selected_analyses=direkt_analysen if direkt_analysen else ["Signal"],
                    header_to_signal_idx=header_to_signal_idx,
                    use_filtered=use_filtered,
                    zeitbereiche_dict={},
                    grouped_headers=grouped_headers
                )

        def clear_all():
            selected_list.clear()
            selected_group_indices["indices"].clear()
            self.gui.signal_groups.clear()
            set_group_selection_mode(False)

            update_group_display()
            update_listbox("")
            update_selected_display()
            logger.info("Alle Auswahlen gelöscht.")

            search_entry.select_clear()
            search_entry.delete(0, tk.END)
            search_entry.focus_set()

            show_avg_var.set(False)
            show_rms_var.set(False)
            show_diff_var.set(False)
            show_integral_var.set(False)
            show_fft_var.set(False)
            show_varianz_var.set(False)

            self.plot_window_manager.overlay_filter_state['type'] = 'Kein Filter'
            self.plot_window_manager.overlay_filter_state['freq1'] = ''
            self.plot_window_manager.overlay_filter_state['freq2'] = ''
            self.plot_window_manager.overlay_filter_state['characteristic'] = 'butterworth'
            self.plot_window_manager.overlay_filter_state['order'] = '1.Ordnung'
            self.plot_window_manager.overlay_filter_state['enabled'] = False
            self.gui.use_filtered_var.set(False)

            protocol_logger.info("SELECTION_CLEAR_ALL")

            if hasattr(self, 'filter_char_button'):
                self.filter_char_button.config(state="disabled")

        def export_selected():
            """Button-Callback - öffnet Dialog und ruft DataProcessor auf"""
            if not selected_list:
                self.gui.status_label.config(text="Keine Signale ausgewählt.")
                return
            if self.gui.t is None or self.gui.dt is None or not self.gui.signals or not self.gui.headers:
                self.gui.status_label.config(text="Keine verarbeiteten Daten vorhanden.")
                return

            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile="MultiSignals_Export.xlsx")

            if not save_path:
                self.gui.status_label.config(text="Export abgebrochen.")
                return

            protocol_logger.info(
                "EXPORT_MULTI path=%s | signals=%s | avg=%s | rms=%s | diff=%s | integral=%s | filtered=%s",
                save_path,
                selected_list,
                show_avg_var.get(),
                show_rms_var.get(),
                show_diff_var.get(),
                show_integral_var.get(),
                self.gui.use_filtered_var.get() and self.gui._is_filter_ready(),
            )

            success, message = DataProcessor.export_signals_to_excel(
                save_path=save_path,
                selected_headers=selected_list,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                add_avg=show_avg_var.get(),
                add_rms=show_rms_var.get(),
                add_diff=show_diff_var.get(),
                add_int=show_integral_var.get(),
                use_filtered=self.gui.use_filtered_var.get() and self.gui._is_filter_ready(),
                filter_manager=self.gui.filter_manager,
                window_type=self.gui.entry6.get().strip() if hasattr(self.gui, "entry6") else Cfg.Defaults.FENSTERTYP
            )

            self.gui.status_label.config(text=message)

        actions_frame = layout["actions_frame"]

        btn_plot = ttk.Button(actions_frame, text="Anzeigen", command=plot_selected)
        btn_plot.pack(pady=10)
        btn_export = ttk.Button(actions_frame, text="Exportieren", command=export_selected)
        btn_export.pack(pady=5)
        btn_clear = ttk.Button(actions_frame, text="Alle löschen", command=clear_all)
        btn_clear.pack(pady=5)

        action_widgets.extend([btn_plot, btn_export, btn_clear])
