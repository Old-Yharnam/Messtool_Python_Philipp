"""
Analyse Manager - Signalanalyse-Funktionen
==========================================
Kapselt mathematische Analysefunktionen für Messsignale:
Mittelwert (AVG), Effektivwert (RMS), Differential, Integral,
Varianz und Autokorrelation mit zugehörigen Ergebnisfenstern.
"""

from __future__ import annotations

import numpy as np
import tkinter as tk
from tkinter import messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import seaborn as sns
from matplotlib import gridspec
import mplcursors
import logging

logger = logging.getLogger(__name__)

from setup import Cfg
from hilfsklassen.daten_verarbeiter import DataProcessor
from gui_module.plot_manager import PlotManager

sns.set_theme(style="whitegrid")

class AnalysisManager:
    """
    Kapselt die Analyse-Funktionen:
    - AVG, RMS, Differential, Integral, Varianz/Autokorrelation
    - inkl. der Helfer für Signal-Auswahl und Ergebnisfenster
    """

    def __init__(self, gui_manager):
        self.gui = gui_manager

    def _get_selected_signal_index(self):
        if not self.gui.headers or not self.gui.signals or self.gui.t is None:
            messagebox.showwarning(Cfg.Texts.HINT, Cfg.Texts.NO_DATA)
            return None
        selected = getattr(self.gui, "selected_signal", None)
        if not selected or selected == Cfg.Texts.SELECT_SIGNAL:
            messagebox.showinfo(Cfg.Texts.HINT, Cfg.Texts.SELECT_SIGNAL_FIRST)
            return None
        try:
            idx = self.gui.headers.index(selected)
            return idx
        except ValueError:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.SIGNAL_NOT_FOUND.format(selected))
            return None

    def _get_signal_for_operations(self, idx):
        t = self.gui.t
        header = self.gui.headers[idx] if idx < len(self.gui.headers) else f"Signal {idx}"
        unit = self.gui.units[idx] if idx < len(self.gui.units) else ""
        original = self.gui.signals[idx]

        # Falls ein Filter gewählt ist UND aktiviert, darauf arbeiten
        if (getattr(self.gui, "use_filtered_var", None) and 
            self.gui.use_filtered_var.get() and
            getattr(self.gui, "filter_manager", None) and 
            self.gui.filter_manager.filter_type != Cfg.Defaults.FILTER_TYP):
            try:
                used = self.gui.filter_manager.apply_filter(original)
            except Exception as e:
                logger.exception("Filterfehler: %s", e)
                used = original
        else:
            used = original
        return t, original, used, header, unit

    def _open_result_window(self, title, plot_func):
        layout = self.gui.layout_manager.create_analysis_result_window(title)
        frame = layout["frame"]

        try:
            plot_func(frame)
        except Exception as e:
            fig = plt.Figure(figsize=Cfg.Layouts.ANALYSIS_FIG_SIZE)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, Cfg.Texts.PLOT_ERROR.format(e),
                    ha="center", va="center", transform=ax.transAxes)
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            canvas.draw()

    def differential_anwendung(self):
        if self.gui.dt is None:
            messagebox.showerror(Cfg.Texts.ERROR, Cfg.Texts.NO_DT)
            return

        signals = getattr(self.gui, 'selected_signals', [])
        if not signals:
            idx = self._get_selected_signal_index()
            if idx is None:
                return
            signals = [self.gui.headers[idx]]

        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Differential",
                selected_headers=signals,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window(Cfg.Texts.DIFFERENTIAL_ANALYSE_TITLE, _plot)

    def differential_multi_anwendung(self, signal_indices):
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.differential_anwendung()
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Differential",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window("Differential Analyse (Multi)", _plot)

    def avg_anwendung(self, start_zeit=None, ende_zeit=None, signal_idx=None):
        if signal_idx is not None:
            idx = signal_idx
        else:
            idx = self._get_selected_signal_index()
            if idx is None:
                return
        if self.gui.dt is None:
            messagebox.showerror("Fehler", "Keine gültige Abtastzeit (dt) vorhanden.")
            return

        header = self.gui.headers[idx]
        header_to_signal_idx = {header: idx}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="AVG",
                selected_headers=[header],
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start_zeit,
                ende_zeit=ende_zeit
            )

        self._open_result_window(Cfg.Texts.AVG_ANALYSE_TITLE, _plot)

    def avg_multi_anwendung(self, signal_indices, start_zeit=None, ende_zeit=None):
        if len(signal_indices) == 1:
            self.avg_anwendung(start_zeit, ende_zeit, signal_idx=signal_indices[0])
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="AVG",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start_zeit,
                ende_zeit=ende_zeit
            )

        self._open_result_window(Cfg.Texts.AVG_ANALYSE_MULTI_TITLE, _plot)

    def rms_anwendung(self, start_zeit=None, ende_zeit=None, signal_idx=None):
        if signal_idx is not None:
            idx = signal_idx
        else:
            idx = self._get_selected_signal_index()
            if idx is None:
                return

        header = self.gui.headers[idx]
        header_to_signal_idx = {header: idx}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="RMS",
                selected_headers=[header],
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start_zeit,
                ende_zeit=ende_zeit
            )

        self._open_result_window(Cfg.Texts.RMS_ANALYSE_TITLE, _plot)

    def rms_multi_anwendung(self, signal_indices, start_zeit=None, ende_zeit=None):
        if len(signal_indices) == 1:
            self.rms_anwendung(start_zeit, ende_zeit, signal_idx=signal_indices[0])
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="RMS",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start_zeit,
                ende_zeit=ende_zeit
            )

        self._open_result_window(Cfg.Texts.RMS_ANALYSE_MULTI_TITLE, _plot)

    def fft_anwendung(self, start=None, ende=None, signal_idx=None):
        if signal_idx is not None:
            idx = signal_idx
        else:
            idx = self._get_selected_signal_index()
            if idx is None:
                return

        header = self.gui.headers[idx]
        header_to_signal_idx = {header: idx}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="FFT",
                selected_headers=[header],
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start,
                ende_zeit=ende
            )

        self._open_result_window(Cfg.Texts.FFT_ANALYSE_TITLE, _plot)

    def fft_multi_anwendung(self, signal_indices, start=None, ende=None):
        if len(signal_indices) == 1:
            self.fft_anwendung(start, ende, signal_idx=signal_indices[0])
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="FFT",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager,
                start_zeit=start,
                ende_zeit=ende
            )

        self._open_result_window(Cfg.Texts.FFT_ANALYSE_MULTI_TITLE, _plot)

    def integral_anwendung(self):
        if self.gui.dt is None:
            messagebox.showerror("Fehler", "Keine gültige Abtastzeit (dt) vorhanden.")
            return

        signals = getattr(self.gui, 'selected_signals', [])
        if not signals:
            idx = self._get_selected_signal_index()
            if idx is None:
                return
            signals = [self.gui.headers[idx]]

        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Integral",
                selected_headers=signals,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window(Cfg.Texts.INTEGRAL_ANALYSE_TITLE, _plot)

    def integral_multi_anwendung(self, signal_indices):
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.integral_anwendung()
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Integral",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window(Cfg.Texts.INTEGRAL_ANALYSE_MULTI_TITLE, _plot)

    def varianz_anwendung(self):
        if self.gui.dt is None:
            messagebox.showerror("Fehler", "Keine gültige Abtastzeit (dt) vorhanden.")
            return

        signals = getattr(self.gui, 'selected_signals', [])
        if not signals:
            idx = self._get_selected_signal_index()
            if idx is None:
                return
            signals = [self.gui.headers[idx]]

        header_to_signal_idx = {h: self.gui.headers.index(h) for h in signals}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Statistik",
                selected_headers=signals,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window(Cfg.Texts.VARIANZ_ANALYSE_TITLE, _plot)

    def varianz_multi_anwendung(self, signal_indices):
        if len(signal_indices) == 1:
            self.gui.selected_signals = [self.gui.headers[signal_indices[0]]]
            self.varianz_anwendung()
            return

        selected_headers = [self.gui.headers[idx] for idx in signal_indices]
        header_to_signal_idx = {h: self.gui.headers.index(h) for h in selected_headers}
        use_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                        self.gui.use_filtered_var.get())
        filter_manager = getattr(self.gui, "filter_manager", None)

        def _plot(frame):
            PlotManager.create_analysis_tab(
                frame=frame,
                analyse_typ="Statistik",
                selected_headers=selected_headers,
                signals=self.gui.signals,
                units=self.gui.units,
                t=self.gui.t,
                dt=self.gui.dt,
                header_to_signal_idx=header_to_signal_idx,
                use_filtered=use_filtered,
                filter_manager=filter_manager
            )

        self._open_result_window(Cfg.Texts.VARIANZ_ANALYSE_MULTI_TITLE, _plot)

    def zeige_zeitbereich_dialog(self, berechnungs_typ, signal_idx=None):
        """Öffnet Zeitbereich-Dialog und führt Analyse aus."""
        t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

        selected_signal = None
        if signal_idx is not None and signal_idx < len(self.gui.headers):
            selected_signal = self.gui.headers[signal_idx]
        elif hasattr(self.gui, 'selected_signal'):
            selected_signal = self.gui.selected_signal

        is_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                       self.gui.use_filtered_var.get())
        filter_info = None
        if is_filtered and hasattr(self.gui, 'filter_manager'):
            filter_info = self.gui.filter_manager.get_filter_info()

        def on_berechnen(result):
            zeitbereiche = result.get(berechnungs_typ, [(None, None)])
            for start_zeit, ende_zeit in zeitbereiche:
                if berechnungs_typ == "AVG":
                    self.avg_anwendung(start_zeit, ende_zeit, signal_idx)
                elif berechnungs_typ == "RMS":
                    self.rms_anwendung(start_zeit, ende_zeit, signal_idx)
                elif berechnungs_typ == "FFT":
                    self.fft_anwendung(start_zeit, ende_zeit)

        PlotManager.show_zeitbereich_dialog(
            parent=self.gui.root,
            t_max=t_max,
            callback=on_berechnen,
            title=Cfg.Texts.ZEITBEREICH_DIALOG_TITLE.format(berechnungs_typ),
            selected_signal=selected_signal,
            is_filtered=is_filtered,
            filter_info=filter_info,
            analyse_typen=[berechnungs_typ]
        )

    def zeige_zeitbereich_dialog_multi(self, analysis_type, selected_signals):
        """Öffnet Zeitbereich-Dialog für Multi-Signal-Ansicht."""
        t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

        signal_indices = []
        for signal_name in selected_signals:
            try:
                signal_indices.append(self.gui.headers.index(signal_name))
            except ValueError:
                continue

        selected_signal = ", ".join(selected_signals[:3])
        if len(selected_signals) > 3:
            selected_signal += f" (+{len(selected_signals) - 3} weitere)"

        is_filtered = (getattr(self.gui, "use_filtered_var", None) and 
                       self.gui.use_filtered_var.get())
        filter_info = None
        if is_filtered and hasattr(self.gui, 'filter_manager'):
            filter_info = self.gui.filter_manager.get_filter_info()

        def on_berechnen(result):
            zeitbereiche = result.get(analysis_type, [(None, None)])
            for start_zeit, ende_zeit in zeitbereiche:
                if analysis_type == "AVG":
                    self.avg_multi_anwendung(signal_indices, start_zeit, ende_zeit)
                elif analysis_type == "RMS":
                    self.rms_multi_anwendung(signal_indices, start_zeit, ende_zeit)
                elif analysis_type == "FFT":
                    self.fft_multi_anwendung(signal_indices, start_zeit, ende_zeit)

            if analysis_type == "Differential":
                self.differential_multi_anwendung(signal_indices)
            elif analysis_type == "Integral":
                self.integral_multi_anwendung(signal_indices)
            elif analysis_type == "Statistik":
                self.varianz_multi_anwendung(signal_indices)

        PlotManager.show_zeitbereich_dialog(
            parent=self.gui.root,
            t_max=t_max,
            callback=on_berechnen,
            title=Cfg.Texts.ZEITBEREICH_DIALOG_TITLE.format(analysis_type),
            selected_signal=selected_signal,
            is_filtered=is_filtered,
            filter_info=filter_info,
            analyse_typen=[analysis_type]
        )