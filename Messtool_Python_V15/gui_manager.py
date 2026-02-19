"""
GUI Manager - Hauptfenster-Verwaltung
=====================================
Zentrale Klasse für die GUI-Steuerung des Messtools.
Koordiniert alle Sub-Manager (Layout, Events, Filter, Plots, Analyse)
und verwaltet den Anwendungszustand sowie die Datenverarbeitung.
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from tkinter import filedialog
import os
import sys
import subprocess
import time
import threading
from tkinter import messagebox
from datetime import datetime
from pathlib import Path
import numpy as np
import logging
from hilfsklassen.zentrales_logging import get_protocol_logger

logger = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

# Import der eigenen Klassen
from hilfsklassen.datei_handler import FileHandler
from hilfsklassen.daten_validator import DataValidator
from hilfsklassen.filter_manager import FilterManager
from gui_module.plot_manager import PlotManager
from hilfsklassen.daten_verarbeiter import DataProcessor

# Import der Manager-Klassen (modulare Architektur)
from gui_module.gui_layout_manager import GuiLayoutManager
from gui_module.plot_fenster_manager import PlotWindowManager
from gui_module.oberflaechen_steuerung import UiControlManager
from gui_module.analyse_manager import AnalysisManager

from Messtool_Python_V15.setup import Cfg

class GuiManager:    
    """Klasse für die gesamte GUI-Verwaltung als Instanz"""

    def __init__(self, get_resource_path):
        # Datenattribute als Instanzvariablen
        self.get_resource_path = get_resource_path
        self.df = None
        self.t = None
        self.nS = None
        self.dt = None
        self.CF = None     
        self.signals = []
        self.value = None
        self.headers = []
        self.units = []
        self.Gesamtpfad = None
        self.temp_df = None
        self.temp_headers = []
        self.temp_units = []
        self.reset_active = False
        self.load_data_active = False
        self.reset_gui_active = False
        self.spectrum_save_path = None
        self.selected_signal = None
        self.selected_signals = []

        # Gruppen-System (maximal 3 Gruppen)
        self.signal_groups = []  # Liste von Gruppen, jede Gruppe ist eine Liste von Signalnamen
        self.max_groups = Cfg.Defaults.MAX_GROUPS
        self.max_signals_per_selection = Cfg.Defaults.MAX_SIGNALS

        # DataValidator Instanz
        self.data_validator = DataValidator()

        # FilterManager Instanz
        self.filter_manager = FilterManager()

        # Manager-Klassen instanziieren
        self.ui_control = UiControlManager(self)  # State + Events + Dialoge
        self.plot_window_manager = PlotWindowManager(self)
        self.layout_manager = GuiLayoutManager(self)
        self.analysis_manager = AnalysisManager(self)

        # GUI-Elemente als Instanzvariablen
        self.root = None
        self.entry1 = None
        self.entry2 = None
        self.entry3 = None
        self.entry4 = None
        self.entry5 = None
        self.entry6 = None
        self.entry7 = None
        self.entry8 = None
        self.entry9 = None
        self.entry10 = None
        self.entry11 = None
        self.status_label = None
        self.progress_label = None
        self.sheet_combobox = None
        self.import_button = None
        self.Verarbeitung_button = None
        self.path_selection_combobox = None
        self.reset_combobox = None
        self.characteristic_window = None
        self.filter_info_tree = None

        # Live-Aktualisierung für Einzelplots
        self.open_plot_windows = []  # Liste der offenen Plot-Fenster

    def _setup_placeholder(self, entry, placeholder_text):
        """Delegiert an UiControlManager"""
        return self.ui_control.setup_placeholder(entry, placeholder_text)

    def create_gui(self):
        """Erstellt GUI-Layout und startet die Mainloop."""
        self.layout_manager.create_gui()
        self.use_filtered_var = tk.BooleanVar(master=self.root, value=False)
        self.ui_control.apply_visual_defaults()
        self.ui_control.configure_root_lifecycle()
        self.root.mainloop()

    def show_multi_signal_overlay_window(self):
        """Öffnet ein Fenster zur Auswahl beliebig vieler Signale und zeigt sie gemeinsam in einem Plot."""
        return self.plot_window_manager.show_multi_signal_overlay_window()

    def _prefill_from_df_and_enable(self):
        """
        1) Befüllt entry1..entry5 mit sinnvollen Zahlen aus self.df,
        ersetzt die Placeholder und schaltet die Felder frei.
        2) Aktiviert Fenster-/Filter-Einträge, soweit sinnvoll.
        3) Startet anschließend direkt die Datenverarbeitung (auto-run).
        """
        if self.df is None:
            return

        # Zeilenbereich: 2 .. letzte Zeile (wie bei dir üblich)
        try:
            end_row_default = int(self.df.index.max())
        except Exception:
            logger.debug("Fallback: end_row_default aus len(self.df)")
            end_row_default = len(self.df)
        start_row_default = Cfg.Defaults.START_ROW_PREFILL

        # Spaltenbereich: numerische Spalten bevorzugen
        try:
            numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                start_col_default = int(self.df.columns.get_loc(numeric_cols[0]))
                end_col_default   = int(self.df.columns.get_loc(numeric_cols[-1]))
            else:
                start_col_default = 0
                end_col_default   = max(0, len(self.df.columns) - 1)
        except Exception:
            logger.debug("Fallback: Spaltenbereich auf gesamte Breite")
            start_col_default = 0
            end_col_default   = max(0, len(self.df.columns) - 1)

        # Samplefrequenz (Fallback wie bisher)
        sample_rate_default = Cfg.Defaults.SAMPLERATE

        # --- Placeholder überschreiben, echte Zahlen setzen & Felder aktivieren ---
        for entry, val in [
            (self.entry1, start_row_default),  # Start Reihe
            (self.entry2, end_row_default),    # End Reihe
            (self.entry3, start_col_default),  # Start Spalte
            (self.entry4, end_col_default),    # End Spalte
            (self.entry5, sample_rate_default) # FS
        ]:
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, str(val))
            entry.configure(style="EntryNormal.TEntry")
            entry._is_placeholder = False

        # Fenster-Combobox freischalten und auf "Rechteck" setzen, wenn leer
        if hasattr(self, "entry6") and self.entry6:
            self.entry6.config(state="normal")
            if self.entry6.get().strip() in ("", Cfg.Ph.FENSTERTYP):
                self.entry6.set(Cfg.Defaults.FENSTERTYP)

        # „Datenverarbeitung“-Button kann sichtbar bleiben, ist aber redundant
        if hasattr(self, "Verarbeitung_button") and self.Verarbeitung_button:
            self.Verarbeitung_button.configure(state="normal")
            for rb in ('rb_plots', 'rb_spectrum', 'rb_none'):
                if hasattr(self, rb):
                    getattr(self, rb).state(["!disabled"])

    def _get_selected_signal_index(self):
        return self.analysis_manager._get_selected_signal_index()

    def _get_signal_for_operations(self, idx):
        return self.analysis_manager._get_signal_for_operations(idx)

    def _open_result_window(self, title, plot_func):
        return self.analysis_manager._open_result_window(title, plot_func)

    def reset_all(self):
        """Komplett-Reset aller Daten und GUI-Elemente"""
        return self.ui_control.reset_all()

    def reset_inputs(self):
        """Setzt nur die Eingabefelder zurück (Daten bleiben geladen)."""
        return self.ui_control.reset_inputs()

    def loading_animation(self):
        self.flood_gauge.pack(side=tk.LEFT, padx=10)
        self.flood_gauge.start()

        while self.loading:
            time.sleep(0.1)

        self.flood_gauge.stop()
        self.flood_gauge.pack_forget()

    def _enter_loading_state(self):
        """Startet Spinner und zeigt Lade-Status."""
        self.loading = True
        threading.Thread(target=self.loading_animation, daemon=True).start()
        self.progress_label.config(text=Cfg.Texts.STATUS_LADEN)

    def _exit_loading_state(self):
        """Stoppt den Spinner und leert das Lade-Label."""
        self.loading = False
        self.progress_label.config(text="")

    def _apply_loaded_dataset(self, result, disable_sheet=False):
        """Wendet geladene Daten auf GUI an."""
        if result[0] is None:
            return False

        self.df, self.temp_headers, self.temp_units = result
        self.temp_df = self.df.copy()
        self._prefill_from_df_and_enable()
        self._enable_entries_after_load()
        self.import_button.config(state='disabled')
        self.update_processing_button_state()

        if disable_sheet:
            self.sheet_combobox.config(state='disabled')
            self.progress_label.config(text="")

        if hasattr(self, 'layout_manager'):
            self.layout_manager.blink_tab(0)

        return True

    def _log_dataset_preview(self, context):
        if self.df is None:
            return
        try:
            columns = list(self.df.columns)
            logger.info(
                "DATA_PREVIEW %s | shape=%s | columns=%s",
                context,
                self.df.shape,
                columns,
            )
            preview_text = self.df.head(10).to_string(index=False)
            logger.info("DATA_HEAD %s\n%s", context, preview_text)
        except Exception as e:
            logger.exception("Fehler beim Loggen der Datenvorschau: %s", e)

    def _enable_entries_after_load(self):
        """Aktiviert Eingabefelder nach erfolgreichem Laden."""
        return self.ui_control.enable_entries_after_load()

    def _handle_load_failure(self, message):
        """Behandelt Fehler beim Laden."""
        self._exit_loading_state()
        logger.error("Fehler beim Laden: %s", message)
        self.status_label.config(text=f"Fehler: {message}")

    def load_data(self):
        """Lädt Daten aus ausgewählter Datei."""
        self._enter_loading_state()
        protocol_logger.info("IMPORT_CLICK")

        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")])

        if not file_path:
            protocol_logger.info("IMPORT_DIALOG_CLOSED result=cancel")
            self._exit_loading_state()
            return

        protocol_logger.info("FILE_SELECTED path=%s", file_path)

        self.Gesamtpfad = Path(file_path)

        try:
            ext = self.Gesamtpfad.suffix.lower()

            if ext in ['.xlsx', '.xls']:
                self._load_excel(file_path)
            elif ext == '.csv':
                self._load_csv(file_path)
            else:
                raise ValueError("Nicht unterstütztes Dateiformat.")

        except Exception as e:
            self._handle_load_failure(str(e))
        finally:
            pass

    def _load_excel(self, file_path):
        """Lädt Excel-Datei und aktualisiert Sheet-Combobox."""
        with open(file_path, 'rb') as f:
            excel_raw = f.read()
            logger.debug("Ecel-Rohdaten geladen: %d Bytes", len(excel_raw))

        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        protocol_logger.info("FILE_LOADED type=excel | path=%s | sheets=%s", file_path, sheet_names)

        if self.sheet_combobox is not None:
            self.sheet_combobox['values'] = sheet_names
            self.sheet_combobox.set(sheet_names[0] if sheet_names else "")
            self.sheet_combobox.config(state='readonly')

        if self.progress_label is not None:
            self.progress_label.config(text="Bitte Sheet auswählen")

    def _load_csv(self, file_path):
        """Lädt CSV-Datei und aktiviert Eingabefelder."""
        self.sheet_combobox['values'] = ['CSV']
        self.sheet_combobox.set('CSV')
        self.sheet_combobox.config(state='disabled')

        file_handler = FileHandler()
        file_handler.file_path = str(self.Gesamtpfad)
        result = file_handler.read_top(self.status_label, self.progress_label)

        if self._apply_loaded_dataset(result):
            self._log_dataset_preview("CSV")
            self._exit_loading_state()

    def on_sheet_selected(self, event):
        """Handler für Sheet-Auswahl."""
        if not (self.Gesamtpfad and self.sheet_combobox.get()):
            return

        protocol_logger.info("SHEET_SELECTED name=%s", self.sheet_combobox.get())

        try:
            file_handler = FileHandler()
            file_handler.file_path = str(self.Gesamtpfad)
            result = file_handler.read_dws_excel(
                self.sheet_combobox.get(), self.status_label, self.progress_label)
            if self._apply_loaded_dataset(result, disable_sheet=True):
                context = f"EXCEL sheet={self.sheet_combobox.get()}"
                self._log_dataset_preview(context)
        except Exception as e:
            logger.exception(f"Fehler beim Laden des Sheets")
            self.status_label.config(text="Fehler: Sheet konnte nicht geladen werden")

    def verarbeitung_button_setup(self):
        """Handler für Datenverarbeitung."""
        # Spinner starten für Verarbeitungsdauer
        self._enter_loading_state()
        self.progress_label.config(text=Cfg.Texts.STATUS_VERARBEITUNG)
        self.root.update()  # GUI sofort aktualisieren damit Spinner sichtbar wird

        protocol_logger.info(
            "PROCESSING_START rows=%s-%s cols=%s-%s fs=%s window=%s",
            self.entry1.get().strip(),
            self.entry2.get().strip(),
            self.entry3.get().strip(),
            self.entry4.get().strip(),
            self.entry5.get().strip(),
            self.entry6.get().strip() if hasattr(self, "entry6") else "",
        )

        self._apply_default_values()
        self._enable_analysis_buttons()
        self._sync_data_validator()

        result = self.data_validator.validate_and_process(
            self.entry1, self.entry2, self.entry3, self.entry4, 
            self.entry5, self.status_label)

        if all(x is not None for x in result):
            self._process_validated_data(result)
        else:
            logger.warning("Fehler: Validierung fehlgeschlagen")
            self.status_label.config(text="Fehler: Datenvalidierung fehlgeschlagen")
            self._exit_loading_state()  # Spinner stoppen bei Fehler

    def _apply_default_values(self):
        """Setzt Standardwerte für leere Eingabefelder."""
        entries = [self.entry1, self.entry2, self.entry3, self.entry4, self.entry5, self.entry6]
        placeholders = Cfg.Ph.EINGABE + [Cfg.Ph.FENSTERTYP]
        config = [
            (entry, ph, dv[0], dv[1])
            for entry, ph, dv in zip(entries, placeholders, Cfg.Defaults.VALUES_CONFIG)
        ]

        aenderungen = []
        for entry, placeholder, default_value, msg in config:
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.insert(0, default_value)
                aenderungen.append(msg)

        if aenderungen:
            messagebox.showinfo("Standardwerte", "Default Werte übernommen")

    def _enable_analysis_buttons(self):
        """Aktiviert Analyse-Buttons."""
        self.status_label.config(text=Cfg.Texts.STATUS_VERARBEITUNG)
        self.overview_window_button.config(state="normal")

    def _sync_data_validator(self):
        """Synchronisiert DataValidator mit aktuellen Daten."""
        self.data_validator.df = self.df
        self.data_validator.temp_df = self.temp_df
        self.data_validator.headers = self.temp_headers
        self.data_validator.units = self.temp_units
        self.data_validator.temp_headers = self.temp_headers
        self.data_validator.temp_units = self.temp_units
        self.data_validator.reset_active = self.reset_active

    def _process_validated_data(self, validation_result):
        """Verarbeitet validierte Daten."""
        samplerate_fs, hann_fenster, self.value, self.headers, self.units = validation_result
        logger.debug("Starte process_data mit value.shape: %s", self.value.shape)

        save_spectrum = (self.save_mode.get() == "spectrum") if hasattr(self, 'save_mode') else True
        save_plots = (self.save_mode.get() == "plots") if hasattr(self, 'save_mode') else True

        result = DataProcessor.process_data(
            samplerate_fs, hann_fenster, self.value, self.headers, self.units,
            self.entry6, self.entry7, self.entry8, self.entry9, self.entry10, self.entry11,
            self.status_label,
            save_spectrum=save_spectrum, save_plots=save_plots)

        if len(result) == 6:
            self.signals, self.headers, self.units, self.t, self.dt, self.spectrum_save_path = result
        else:
            self.signals, self.headers, self.units, self.t, self.dt = result
            self.spectrum_save_path = None

        # Spinner stoppen nach Verarbeitung
        self._exit_loading_state()
        self._finalize_after_processing()
        protocol_logger.info(
            "PROCESSING_DONE signals=%s headers=%s units=%s",
            len(self.signals) if self.signals is not None else 0,
            len(self.headers) if self.headers is not None else 0,
            len(self.units) if self.units is not None else 0,
        )


    def _finalize_after_processing(self):
        """Finalisiert GUI nach erfolgreicher Verarbeitung."""
        for entry in [self.entry1, self.entry2, self.entry3, self.entry4, self.entry5]:
            entry.config(state="disabled")

        self.entry6.config(state="disabled")
        self.Verarbeitung_button.config(state="disabled")

        if hasattr(self, 'overview_window_button'):
            self.overview_window_button.config(state="normal")

        for rb in ('rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self, rb):
                getattr(self, rb).state(["disabled"])

        if hasattr(self, 'layout_manager'):
            self.layout_manager.blink_tab(1, times=25, interval=300)

    def show_overview_window(self):
        """Zeigt den Übersichtsplot in einem separaten Fenster."""
        data_ready = bool(self.signals and self.headers and self.t is not None)
        protocol_logger.info("OVERVIEW_WINDOW_OPEN data_ready=%s", data_ready)
        if not self.signals or not self.headers or self.t is None:
            logger.info("Keine Daten für Übersichtsplot verfügbar")
            return

        for widget in self.mid_region.winfo_children():
            if widget != getattr(self, '_logo_label', None):
                widget.destroy()

        plot_frame = ttk.Frame(self.mid_region)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig = plt.Figure(figsize=(18, 14))
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)

        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        PlotManager.plot_overview(fig, self.t, self.signals, self.headers, self.units)
        canvas.draw()

    def check_processing_ready(self):
        """Prüft ob alle Voraussetzungen für Datenverarbeitung erfüllt sind"""
        if self.df is None:
            return False
        return True

    def update_processing_button_state(self):
        """Aktualisiert den Zustand des Verarbeitung-Buttons"""
        return self.ui_control.update_processing_button_state()

    def log_save_options(self):
        """Protokolliert die Speicheroptionen."""
        mode = self.save_mode.get() if hasattr(self, "save_mode") else "none"
        protocol_logger.info("SAVE_OPTIONS mode=%s", mode)

    def update_all_plot_windows(self):
        """Aktualisiert alle offenen Plot-Fenster mit den aktuellen Filter-Einstellungen"""
        if not hasattr(self, 'open_plot_windows'):
            return

        for plot_data in self.open_plot_windows[:]:
            try:
                if 'window' in plot_data and plot_data['window'].winfo_exists():
                    self._update_single_plot_window(plot_data)
            except Exception as e:
                logger.exception("Fehler beim Aktualisieren des Plot-Fensters")
                self.open_plot_windows.remove(plot_data)

    def _update_single_plot_window(self, plot_data):
        """Aktualisiert ein einzelnes Plot-Fenster"""
        if 'signal_idx' not in plot_data or 'canvas' not in plot_data:
            return

        signal_idx = plot_data['signal_idx']
        if signal_idx < len(self.signals):
            signal = self.signals[signal_idx]
            filtered_signal = self.filter_manager.apply_filter(signal)

            if 'fig' in plot_data and 'canvas' in plot_data:
                plot_data['fig'].clear()
                ax = plot_data['fig'].add_subplot(111)
                ax.plot(filtered_signal)
                ax.set_title(f"Signal {signal_idx}")
                plot_data['canvas'].draw()

    def on_reset_selected(self, selected):
        """Delegiert an UiControlManager"""
        return self.ui_control.on_reset_selected(selected)

    def show_path_window(self, selected=None):
        """Delegiert an UiControlManager"""
        return self.ui_control.show_path_window(selected)

    def update_filter_plot_short(self):
        """Delegiert an UiControlManager"""
        return self.ui_control.update_filter_plot()

    def show_filter_characteristic_window(self):
        """Zeigt Fenster mit der aktuellen Filter-Charakteristik, Plot und Koeffizienten"""
        return self.ui_control.show_filter_characteristic_window()

    def on_filter_checkbox_changed(self):
        """Wird aufgerufen wenn Filter-Checkbox geändert wird"""
        if self.filter_active_var.get():
            # Filter aktiviert → Dialog öffnen
            def on_success():
                # Nach erfolgreicher Konfiguration: Plot mit Original + gefiltert
                self._update_main_plot_with_filter()

            def on_cancel():
                # Bei Abbruch: Checkbox wieder deaktivieren
                self.filter_active_var.set(False)

            self.ui_control.create_filter_setup_dialog(on_success=on_success)
        else:
            # Filter deaktiviert → Nur Original anzeigen
            self._update_main_plot_without_filter()

    def _update_main_plot_with_filter(self):
        """Zeigt 2 Subplots: Original + gefiltertes Signal"""
        idx = self.selected_signal
        if idx is None:
            messagebox.showwarning("Hinweis", "Bitte zuerst ein Signal auswählen")
            self.filter_active_var.set(False)
            return

        t, original, _, header, unit = self.analyse_manager._get_signal_for_operations(idx)
        filtered = self.filter_manager.apply_filter(original)

        win = tb.Toplevel(self.root)
        win.title(f"Signal: {header} (mit Filter)")
        win.geometry("1000x600")

        fig = plt.Figure(figsize=(12, 6))
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ax1 = fig.add_subplot(211)
        ax1.plot(t, original, color=Cfg.Colors.SIGNAL_ORIGINAL, label=f"{header} [{unit}]")
        ax1.set_title(f"{header} - Original")
        ax1.set_xlabel("Zeit [s]")
        ax1.set_ylabel(f"Amplitude [{unit}]")
        ax1.grid(True)
        ax1.legend()

        ax2 = fig.add_subplot(212, sharex=ax1)
        ax2.plot(t, filtered, color="orange", label=f"{header} gefiltert [{unit}]")
        ax2.set_title(f"{header} - Gefiltert ({self.filter_manager.filter_type})")
        ax2.set_xlabel("Zeit [s]")
        ax2.set_ylabel(f"Amplitude [{unit}]")
        ax2.grid(True)
        ax2.legend()

        fig.tight_layout()
        canvas.draw()

    def _update_main_plot_without_filter(self):
        """Filter deaktiviert - schließt ggf. Filter-Fenster"""
        self.status_label.config(text="Filter deaktiviert")

    def update_filter_plot(self):
        """Aktualisiert den Filter-Frequenzgang-Plot"""
        if not hasattr(self, 'filter_fig') or not hasattr(self, 'filter_canvas'):
            return

        self.filter_fig.clear()
        w, magnitude_db, phase_deg = self.filter_manager.get_frequency_response()

        filter_info = {
            'type': self.filter_manager.filter_type,
            'characteristic': self.filter_manager.characteristic,
            'order': self.filter_manager.order,
            'sample_rate': self.filter_manager.sample_rate,
            'cutoff': self.filter_manager.cutoff_frequency,
            'cutoff2': self.filter_manager.cutoff_frequency2
        }

        PlotManager.plot_filter_response(self.filter_fig, w, magnitude_db, phase_deg, filter_info)
        self.filter_canvas.draw()

    def _is_filter_ready(self) -> bool:
        """Prüft, ob Filter wirklich anwendbar ist (Typ, Grenzfrequenz(en), Samplerate, Nyquist)."""
        if not hasattr(self, "filter_manager") or not self.filter_manager:
            return False
        fm = self.filter_manager
        if fm.filter_type in (None, "", Cfg.Defaults.FILTER_TYP, "Filter wählen:"):
            return False
        # Samplerate
        try:
            fs_txt = self.entry5.get().strip()
            fs = float(fs_txt) if fs_txt and "Samplefrequenz" not in fs_txt else None
        except Exception:
            logger.debug("Fallback: Samplefrequenz konnte nicht geparst werden")
            fs = None
        if fs is None or fs <= 0:
            return False
        # Grenzfrequenzen prüfen
        ny = fs / 2.0
        def _parse_float(entry, placeholder):
            try:
                t = entry.get().strip()
                if not t or t == placeholder:
                    return None
                return float(t)
            except Exception:
                logger.debug("Fallback: Grenzfrequenz konnte nicht geparst werden")
                return None

        f1 = fm.cutoff_frequency
        f2 = fm.cutoff_frequency2

        if fm.filter_type in ("Tiefpass", "Hochpass"):
            if f1 is None or not (0 < f1 < ny):
                return False
        elif fm.filter_type == "Bandpass":
            # Fallback (±20%) erlauben: dann reicht f1
            if f2 is not None:
                if f1 is None or not (0 < f1 < ny) or not (0 < f2 < ny) or not (f1 < f2):
                    return False
            else:
                if f1 is None or not (0 < f1 < ny):
                    return False
        else:
            return False
        return True

    def create_filter_setup_dialog(self, on_success=None):
        """
        Öffnet einen Eingabe-Dialog für Filter-Parameter.
        Bei erfolgreichem 'Übernehmen': setzt FilterManager + GUI-Comboboxen,
        optionaler Callback 'on_success' wird aufgerufen (z.B. Plot-Update).
        """
        return self.ui_control.create_filter_setup_dialog(on_success)

    def create_live_plot_window(self, selected_signal):
        """Erstellt ein Plot-Fenster mit Live-Aktualisierung"""
        return self.plot_window_manager.create_live_plot_window(selected_signal)

    def update_single_plot(self, plot_window_data):
        """Aktualisiert einen einzelnen Plot (dynamische Achsen je Auswahl)."""
        return self.plot_window_manager.update_single_plot(plot_window_data)

    def on_filter_changed(self, event=None):
        """Handler für Änderungen in den Filter-Comboboxen"""
        return self.ui_control.on_window_function_changed(event)

    def on_window_function_changed(self, event=None):
        """Delegiert an EventHandler und aktualisiert Button-Status"""
        self.ui_control.on_window_function_changed(event)
        self.update_processing_button_state()

    def show_help(self):
        """Öffnet die externe Bedienungsanleitung in Word (bzw. Standardprogramm)."""
        help_path = self.get_resource_path("docs_bilder/Bedienungsanleitung_Messtool.docx")
        help_exists = os.path.exists(help_path)
        protocol_logger.info("HELP_OPEN path=%s exists=%s", help_path, help_exists)

        if not help_exists:
            messagebox.showinfo("Hinweis", f"Anleitung nicht gefunden:\n{help_path}")
            return
        try:
            if sys.platform.startswith("win"):
                # Öffnet in Word, wenn Word installiert ist und .docx verknüpft ist
                os.startfile(help_path)
            elif sys.platform == "darwin":
                subprocess.call(["open", help_path])      # macOS (öffnet in Word, wenn verknüpft)
            else:
                subprocess.call(["xdg-open", help_path])  # Linux (Standardprogramm für .docx)
        except Exception:
            logging.exception("Anleitung konnte nicht geöffnet werden")
            messagebox.showerror("Fehler", "Anleitung konnte nicht geöffnet werden.")
