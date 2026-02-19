"""
GUI Manager - Zentrale Verwaltung aller GUI-Elemente
====================================================
Kombiniert State Management, Event-Handling und Dialog-Verwaltung:
- GUI-Zustandsverwaltung (Reset, Enable/Disable)
- Event-Verarbeitung (Button-Clicks, Combobox-Auswahl)
- Dialog-Fenster (Filter-Charakteristik, etc.)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import logging
from datetime import datetime
from hilfsklassen.zentrales_logging import get_protocol_logger
from hilfsklassen.zentrales_logging import log_session_end

logger = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

from gui_module.plot_manager import PlotManager
from hilfsklassen.filter_manager import FilterManager
from hilfsklassen.datei_handler import FileHandler
from Messtool_Python_V15.setup import Cfg


class UiControlManager:
    """
    Zentrale Verwaltung aller GUI-Operationen:
    - State Management (reset_all, reset_inputs, enable_entries_after_load)
    - Event-Handling (on_reset_selected, on_sheet_selected, show_path_window)
    - Dialog-Verwaltung (show_filter_characteristic_window, etc.)

    Diese Klasse ersetzt die bisherigen drei Manager für bessere Lesbarkeit
    und weniger Dateien/Imports.
    """

    def __init__(self, gui_manager):
        self.gui = gui_manager

    def apply_visual_defaults(self):
        """Setzt zentrale visuelle Defaults für das Hauptfenster."""
        self.gui.root.option_add("*Font", f"{Cfg.Fonts.FAMILY} {Cfg.Fonts.SMALL}")
        style = ttk.Style(self.gui.root)
        style.configure(".", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("TLabel", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("TButton", padding=(10, 5))
        style.configure("TEntry", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(4, 2))
        style.configure("TCombobox", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(4, 2))
        style.configure("TCheckbutton", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL), padding=(2, 1))
        style.configure("TLabelframe.Label", font=(Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL, "bold"))
        style.configure("EntryNormal.TEntry", foreground="black")
        style.configure("EntryPlaceholder.TEntry", foreground="gray45")
        style.map("EntryNormal.TEntry", foreground=[("readonly", "black"), ("disabled", "black")])
        style.map("EntryPlaceholder.TEntry", foreground=[("readonly", "gray45"), ("disabled", "gray45")])
        style.map("TEntry", foreground=[("readonly", "black"), ("disabled", "gray45")])
        style.map("TCombobox", foreground=[("readonly", "black"), ("disabled", "gray45")])

    def configure_root_lifecycle(self):
        """Registriert zentrale Root-Callbacks (Close + Exception-Handling)."""
        def on_main_window_close():
            session_id = getattr(self.gui, "session_id", None)
            end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_session_end(session_id=session_id, end_time=end_time, reason="window_close")
            self.gui.root.destroy()

        def report_callback_exception(exc_type, exc_value, exc_traceback):
            logger.exception(
                "Unhandled Tkinter callback exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )

        self.gui.root.report_callback_exception = report_callback_exception
        self.gui.root.protocol("WM_DELETE_WINDOW", on_main_window_close)

    def setup_placeholder(self, entry, placeholder_text):
        """Richtet Placeholder-Verhalten für Entry-Felder ein."""
        try:
            entry.unbind('<FocusIn>')
            entry.unbind('<FocusOut>')
        except Exception:
            pass

        def on_focus_in(event):
            current_text = entry.get()
            is_placeholder = getattr(entry, "_is_placeholder", False)
            if current_text == placeholder_text or is_placeholder:
                entry.delete(0, tk.END)
                entry.configure(style="EntryNormal.TEntry")
                entry._is_placeholder = False

        def on_focus_out(event):
            current_text = entry.get().strip()
            if current_text == '' or current_text == placeholder_text:
                entry.delete(0, tk.END)
                entry.insert(0, placeholder_text)
                entry.configure(style="EntryPlaceholder.TEntry")
                entry._is_placeholder = True

        entry.delete(0, tk.END)
        entry.insert(0, placeholder_text)
        entry.configure(style="EntryPlaceholder.TEntry")
        entry._is_placeholder = True

        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    # ========== STATE MANAGEMENT ==========

    def reset_all(self):
        """Setzt die gesamte GUI und alle Daten zurück"""
        protocol_logger.info("RESET action=all")
        self.gui.reset_active = True

        # Schließe alle offenen Plot-Fenster
        for plot_data in self.gui.open_plot_windows:
            if plot_data.get('window') is not None and plot_data['window'].winfo_exists():
                plot_data['window'].destroy()
        self.gui.open_plot_windows.clear()

        # Schließe das Signal-Auswahl-Fenster falls offen
        if self.gui.plot_window_manager.active_signal_window is not None:
            try:
                self.gui.plot_window_manager.active_signal_window.destroy()
            except Exception:
                pass
            self.gui.plot_window_manager.active_signal_window = None

        # Alle Daten zurücksetzen
        self.gui.t = None
        self.gui.nS = None
        self.gui.dt = None
        self.gui.CF = None
        self.gui.signals = []
        self.gui.value = None
        self.gui.df = None
        self.gui.headers = []
        self.gui.units = []
        self.gui.Gesamtpfad = None
        self.gui.temp_df = None
        self.gui.temp_headers = []
        self.gui.temp_units = []

        # GUI-Elemente zurücksetzen
        placeholders = Cfg.Ph.EINGABE
        entries = [self.gui.entry1, self.gui.entry2, self.gui.entry3, self.gui.entry4, self.gui.entry5]

        for entry, placeholder in zip(entries, placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True
            entry.config(state="disabled")

        self.gui.entry6.config(state='normal')
        self.gui.entry6.set(Cfg.Defaults.FENSTERTYP)
        self.gui.entry6.config(state='disabled')

        self.gui.flood_gauge.stop()
        self.gui.flood_gauge.pack_forget()

        output_placeholders = Cfg.Ph.AUSGABE
        output_entries = [self.gui.entry7, self.gui.entry8, self.gui.entry9, self.gui.entry10, self.gui.entry11]

        for entry, placeholder in zip(output_entries, output_placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True
            entry.config(state="readonly")

        self.gui.sheet_combobox.set(Cfg.Texts.CB_CSV_DEFAULT)
        self.gui.sheet_combobox['values'] = [Cfg.Texts.CB_CSV_DEFAULT]
        self.gui.sheet_combobox.config(state="disabled")

        if hasattr(self.gui, 'save_mode'):
            self.gui.save_mode.set("none")
        for rb in ('rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self.gui, rb):
                getattr(self.gui, rb).state(["disabled"])

        if hasattr(self.gui, 'overview_window_button'):
            self.gui.overview_window_button.config(state="disabled")

        self.gui.import_button.config(state="normal")
        self.gui.status_label.config(text=Cfg.Texts.STATUS_NEUE_DATEI)
        self.gui.progress_label.config(text="")

        self.gui.load_data_active = False
        self.gui.reset_gui_active = False
        pass

    def reset_inputs(self):
        """Setzt nur die Eingabefelder zurück, bewahrt aber die Daten"""
        protocol_logger.info("RESET action=inputs")
        if self.gui.temp_df is not None and isinstance(self.gui.temp_df, pd.DataFrame):
            self.gui.df = self.gui.temp_df.copy()
            logger.info("DataFrame für erneute Verarbeitung wiederhergestellt")

        self.gui.reset_active = False

        placeholders = Cfg.Ph.EINGABE
        entries = [self.gui.entry1, self.gui.entry2, self.gui.entry3, self.gui.entry4, self.gui.entry5]

        for entry, placeholder in zip(entries, placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True

        self.gui.entry6.config(state='normal')
        self.gui.entry6.set(Cfg.Defaults.FENSTERTYP)

        output_placeholders = Cfg.Ph.AUSGABE
        output_entries = [self.gui.entry7, self.gui.entry8, self.gui.entry9, self.gui.entry10, self.gui.entry11]

        for entry, placeholder in zip(output_entries, output_placeholders):
            entry.config(state="normal")
            entry.delete(0, tk.END)
            entry.insert(0, placeholder)
            entry.configure(style="EntryPlaceholder.TEntry")
            entry._is_placeholder = True
            entry.config(state="readonly")

        if self.gui.Gesamtpfad:
            file_extension = self.gui.Gesamtpfad.suffix.lower()
            if file_extension in ['.xlsx', '.xls']:
                self.gui.sheet_combobox.config(state="readonly")
            else:
                self.gui.sheet_combobox.config(state="disabled")
        else:
            self.gui.sheet_combobox.config(state="disabled")

        self.gui.status_label.config(text=Cfg.Texts.STATUS_NEUE_EINGABEN)
        self.gui.Verarbeitung_button.config(state="normal")
        for rb in ('rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self.gui, rb):
                getattr(self.gui, rb).state(["!disabled"])

    def enable_entries_after_load(self):
        """Aktiviert alle Eingabefelder nach dem Laden einer Datei"""
        placeholders = Cfg.Ph.EINGABE
        entries = [self.gui.entry1, self.gui.entry2, self.gui.entry3, self.gui.entry4, self.gui.entry5]

        for entry, placeholder in zip(entries, placeholders):
            entry.config(state='normal')
            self.setup_placeholder(entry, placeholder)

        self.gui.entry6.config(state='normal')

    def update_processing_button_state(self):
        """Aktualisiert den State des Verarbeitungs-Buttons und der Radiobuttons"""
        if self.gui.check_processing_ready():
            state = "normal"
        else:
            state = "disabled"
        self.gui.Verarbeitung_button.configure(state=state)
        for rb in ('rb_plots', 'rb_spectrum', 'rb_none'):
            if hasattr(self.gui, rb):
                if state == "normal":
                    getattr(self.gui, rb).state(["!disabled"])
                else:
                    getattr(self.gui, rb).state(["disabled"])

    # ========== EVENT HANDLING ==========

    def on_reset_selected(self, selected):
        """Handler für Reset-Auswahl per Button"""
        protocol_logger.info("UI_SELECT reset=%s", selected)
        if selected == "Komplett zurücksetzen":
            self.reset_all()
        elif selected == "Nur Eingabefelder zurücksetzen":
            self.reset_inputs()
            self.gui.flood_gauge.stop()
            self.gui.flood_gauge.pack_forget()

    def on_sheet_selected(self, event):
        """Handler für Sheet-Auswahl in Excel-Dateien"""
        if not (self.gui.Gesamtpfad and self.gui.sheet_combobox.get()):
            return

        try:
            file_handler = FileHandler()
            file_handler.file_path = str(self.gui.Gesamtpfad)
            result = file_handler.read_dws_excel(
                self.gui.sheet_combobox.get(), self.gui.status_label, self.gui.progress_label)
            self.gui._apply_loaded_dataset(result, disable_sheet=True)
        except Exception as e:
            logger.exception("Fehler beim Laden des Sheets: %s", e)
            self.gui.status_label.config(text=f"Fehler: {str(e)}")

    def on_window_function_changed(self, event=None):
        """Handler für Änderungen der Fensterfunktion"""
        selected = self.gui.entry6.get()
        if selected == Cfg.Ph.FENSTERTYP:
            return
        logger.info("Fensterfunktion geändert auf: %s", selected)
        protocol_logger.info("WINDOW_FUNCTION selected=%s", selected)

    def show_path_window(self, selected=None):
        """Zeigt ein Fenster mit dem gewählten Pfad an"""
        if selected == "Datei Herkunftspfad":
            path = str(self.gui.Gesamtpfad) if self.gui.Gesamtpfad else "Keine Datei geladen"
            title = "Datei Herkunftspfad"
        elif selected == "Spektrum Speicherpfad":
            path = str(self.gui.spectrum_save_path) if self.gui.spectrum_save_path else "Kein Speicherpfad festgelegt"
            title = "Spektrum Speicherpfad"
        else:
            return

        messagebox.showinfo(title, path)
        protocol_logger.info("PATH_VIEW type=%s", selected)

    # ========== DIALOG-VERWALTUNG ==========

    def show_filter_characteristic_window(self):
        """
        Zeigt Fenster mit der aktuellen Filter-Charakteristik:
        - Filter-Parameter oben
        - Frequenzgang-Plot links
        - Filter-Koeffizienten rechts
        """
        if not hasattr(self.gui, 'filter_manager') or not self.gui.filter_manager:
            logger.info("Kein FilterManager verfügbar")
            return

        protocol_logger.info("FILTER_CHARACTERISTIC_OPEN")

        if self.gui.characteristic_window and self.gui.characteristic_window.winfo_exists():
            self.gui.characteristic_window.destroy()
        filter_info = self.gui.filter_manager.get_filter_info()
        layout = self.gui.layout_manager.create_filter_characteristic_layout(filter_info)
        info_text_widget = layout["info_text_widget"]

        # Koeffizienten berechnen
        b, a, sos = self.gui.filter_manager.get_filter_coefficients()

        self.update_filter_plot()

        # Vollständigen Info-Text mit format_filter_info_text generieren
        if b is None or a is None:
            # Prüfe ob die Parameter ungültig sind
            sr = filter_info.get('sample_rate')
            cf = filter_info.get('cutoff')
            if sr and cf and cf >= sr / 2:
                info_text = f"""FEHLER: Ungültige Filter-Parameter!

Die Grenzfrequenz ({cf} Hz) muss kleiner als die
Nyquist-Frequenz ({sr/2} Hz) sein!

Nyquist-Frequenz = Abtastrate / 2 = {sr} / 2 = {sr/2} Hz

Bitte korrigieren Sie die Grenzfrequenz oder erhöhen
Sie die Abtastrate.
"""
            else:
                info_text = """Filter-Koeffizienten konnten nicht berechnet werden.

Mögliche Ursachen:
- Grenzfrequenz nicht gesetzt
- Abtastrate nicht gesetzt
- Ungültige Frequenzkombination
"""
        else:
            info_text = FilterManager.format_filter_info_text(
                filter_info.get('type'),
                filter_info.get('characteristic'),
                filter_info.get('order'),
                filter_info.get('cutoff'),
                filter_info.get('cutoff2'),
                filter_info.get('sample_rate'),
                b, a, sos
            )

        lines = info_text.splitlines()
        for line in lines:
            info_text_widget.insert("", tk.END, values=(line,))

    def update_filter_plot(self):
        """Aktualisiert den Filter-Frequenzgang-Plot"""
        if not hasattr(self.gui, 'filter_fig') or not hasattr(self.gui, 'filter_canvas'):
            return

        self.gui.filter_fig.clear()

        w, magnitude_db, phase_deg = self.gui.filter_manager.get_frequency_response()

        filter_info = {
            'type': self.gui.filter_manager.filter_type,
            'characteristic': self.gui.filter_manager.characteristic,
            'order': self.gui.filter_manager.order,
            'sample_rate': self.gui.filter_manager.sample_rate,
            'cutoff': self.gui.filter_manager.cutoff_frequency,
            'cutoff2': self.gui.filter_manager.cutoff_frequency2
        }

        PlotManager.plot_filter_response(self.gui.filter_fig, w, magnitude_db, phase_deg, filter_info)
        self.gui.filter_canvas.draw()

    def create_filter_setup_dialog(self, on_success=None):
        """
        Erstellt einen Dialog zur interaktiven Filter-Setup
        (Falls diese Methode in filter_dialog_manager vorhanden war)
        """
        # Platzhalter für zukünftige Filter-Setup Dialog Implementierung
        pass

    # ========== ALLGEMEINE DIALOG-VERWALTUNG ==========

    def close_all_dialogs(self):
        """Schließt alle offenen Dialoge"""
        if hasattr(self.gui, 'characteristic_window') and self.gui.characteristic_window:
            try:
                if self.gui.characteristic_window.winfo_exists():
                    self.gui.characteristic_window.destroy()
            except tk.TclError:
                pass

    def get_open_dialog(self, dialog_name):
        """Gibt ein offenes Dialog-Fenster zurück, falls es existiert"""
        if dialog_name == 'characteristic' and hasattr(self.gui, 'characteristic_window'):
            if self.gui.characteristic_window and self.gui.characteristic_window.winfo_exists():
                return self.gui.characteristic_window
        return None

    # ========== PLATZHALTER FÜR ZUKÜNFTIGE DIALOGE ==========

    def show_settings_dialog(self):
        """Platzhalter für zukünftige Settings-Dialoge"""
        pass

    def show_export_dialog(self):
        """Platzhalter für Export-Dialog"""
        pass
