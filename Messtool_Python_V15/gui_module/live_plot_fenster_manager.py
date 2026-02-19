"""
Live Plot Fenster Manager - Live-Plot-Verwaltung
================================================
Verwaltet die Erstellung und Aktualisierung von Live-Plot-Fenstern
mit interaktiven Optionen für Signal, FFT, AVG, RMS, Differential und Integral.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import logging
from hilfsklassen.zentrales_logging import get_protocol_logger

logger = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

from Messtool_Python_V15.setup import Cfg
from gui_module.plot_manager import PlotManager
from hilfsklassen.daten_verarbeiter import DataProcessor
from hilfsklassen.datei_handler import FileHandler


class LivePlotFensterManager:
    """Verwaltet Live-Plot-Fenster"""

    def __init__(self, gui_manager, plot_window_manager):
        self.gui = gui_manager
        self.plot_window_manager = plot_window_manager

    def create_live_plot_window(self, selected_signal):
        """Erstellt ein Plot-Fenster mit Live-Aktualisierung"""
        if not selected_signal or selected_signal == "Signal auswählen:" or not self.gui.signals or not self.gui.headers or self.gui.t is None:
            logger.info("Keine Daten zum Plotten verfügbar")
            return None

        protocol_logger.info("LIVE_PLOT_OPEN signal=%s", selected_signal)

        layout = self.gui.layout_manager.create_live_plot_layout(selected_signal)
        plot_window = layout['window']
        fig = layout['fig']
        canvas = layout['canvas']
        toolbar_frame = layout['toolbar_frame']
        options_frame = layout['options_frame']

        show_original_var = tk.BooleanVar(value=True)
        show_filtered_var = self.gui.use_filtered_var
        show_fft_master_var = tk.BooleanVar(value=False)
        show_amp_var = tk.BooleanVar(value=False)
        show_phase_var = tk.BooleanVar(value=False)

        analysis_frame = layout['analysis_frame']
        show_avg_var = tk.BooleanVar(value=False)
        show_rms_var = tk.BooleanVar(value=False)
        show_diff_var = tk.BooleanVar(value=False)
        show_integral_var = tk.BooleanVar(value=False)

        plot_window_data = {
            'window': plot_window,
            'signal_name': selected_signal,
            'fig': fig,
            'canvas': canvas,
            'show_original_var': show_original_var,
            'show_filtered_var': show_filtered_var,
            'show_fft_master_var': show_fft_master_var,
            'show_amp_var': show_amp_var,
            'show_phase_var': show_phase_var,
            'show_avg_var': show_avg_var,
            'show_rms_var': show_rms_var,
            'show_diff_var': show_diff_var,
            'show_integral_var': show_integral_var,
            'avg_zeitbereiche': [],
            'rms_zeitbereiche': [],
            'fft_zeitbereiche': []
        }

        def _on_filtered_toggled(*_):
            enabled = self.gui.use_filtered_var.get()
            if enabled:
                if not self.gui._is_filter_ready():
                    self.gui.use_filtered_var.set(False)
                    messagebox.showwarning("Filter nicht konfiguriert", "Bitte Filter wählen/einstellen")
                    return
            self.update_single_plot(plot_window_data)

        def _on_fft_master_toggled(*_):
            on = show_fft_master_var.get()
            show_amp_var.set(on)
            show_phase_var.set(on)
            if on:
                t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

                selected_signal = plot_window_data.get('header', '')
                is_filtered = plot_window_data.get('show_filtered_var', tk.BooleanVar()).get()
                filter_info = None
                if is_filtered and hasattr(self.gui, 'filter_manager'):
                    filter_info = self.gui.filter_manager.get_filter_info()

                def on_fft_zeitbereich(result):
                    zeitbereiche = result.get("FFT", [(None, None)])
                    plot_window_data['fft_zeitbereiche'] = zeitbereiche
                    protocol_logger.info(
                        "LIVE_PLOT_TIME_RANGE signal=%s | type=FFT | ranges=%s",
                        selected_signal,
                        zeitbereiche,
                    )
                    self.update_single_plot(plot_window_data)

                PlotManager.show_zeitbereich_dialog(
                    parent=plot_window,
                    t_max=t_max,
                    callback=on_fft_zeitbereich,
                    title="FFT - Zeitbereich auswählen",
                    selected_signal=selected_signal,
                    is_filtered=is_filtered,
                    filter_info=filter_info,
                    analyse_typen=["FFT"]
                )
            else:
                plot_window_data['fft_zeitbereiche'] = []
                self.update_single_plot(plot_window_data)

        ttk.Checkbutton(options_frame, text="Original", variable=show_original_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(options_frame, text="Gefiltert", variable=show_filtered_var).pack(side=tk.LEFT, padx=6)

        ttk.Separator(options_frame, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Checkbutton(options_frame, text="FFT anzeigen", variable=show_fft_master_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(options_frame, text="Amplitude (FFT)", variable=show_amp_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(options_frame, text="Phase (FFT)", variable=show_phase_var).pack(side=tk.LEFT, padx=6)

        ttk.Checkbutton(analysis_frame, text="AVG", variable=show_avg_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(analysis_frame, text="RMS", variable=show_rms_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(analysis_frame, text="Differential", variable=show_diff_var).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(analysis_frame, text="Integral", variable=show_integral_var).pack(side=tk.LEFT, padx=6)

        def _bind_var(var, name, cb):
            def _wrapped(*_):
                try:
                    protocol_logger.info("LIVE_PLOT_TOGGLE %s=%s", name, var.get())
                except Exception:
                    pass
                cb()

            try:
                var.trace_add("write", _wrapped)
            except Exception:
                var.trace("w", lambda *_: _wrapped())

        _bind_var(show_original_var, "original", lambda *_: self.update_single_plot(plot_window_data))
        _bind_var(show_amp_var, "fft_amplitude", lambda *_: self.update_single_plot(plot_window_data))
        _bind_var(show_phase_var, "fft_phase", lambda *_: self.update_single_plot(plot_window_data))
        _bind_var(show_diff_var, "differential", lambda *_: self.update_single_plot(plot_window_data))
        _bind_var(show_integral_var, "integral", lambda *_: self.update_single_plot(plot_window_data))

        _bind_var(show_filtered_var, "filtered", _on_filtered_toggled)

        def _on_avg_toggled(*_):
            if show_avg_var.get():
                t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

                selected_signal = plot_window_data.get('header', '')
                is_filtered = plot_window_data.get('show_filtered_var', tk.BooleanVar()).get()
                filter_info = None
                if is_filtered and hasattr(self.gui, 'filter_manager'):
                    filter_info = self.gui.filter_manager.get_filter_info()

                def on_avg_zeitbereich(result):
                    zeitbereiche = result.get("AVG", [(None, None)])
                    plot_window_data['avg_zeitbereiche'] = zeitbereiche
                    protocol_logger.info(
                        "LIVE_PLOT_TIME_RANGE signal=%s | type=AVG | ranges=%s",
                        selected_signal,
                        zeitbereiche,
                    )
                    self.update_single_plot(plot_window_data)

                PlotManager.show_zeitbereich_dialog(
                    parent=plot_window,
                    t_max=t_max,
                    callback=on_avg_zeitbereich,
                    title="AVG - Zeitbereich auswählen",
                    selected_signal=selected_signal,
                    is_filtered=is_filtered,
                    filter_info=filter_info,
                    analyse_typen=["AVG"]
                )
            else:
                plot_window_data['avg_zeitbereiche'] = []
                self.update_single_plot(plot_window_data)

        def _on_rms_toggled(*_):
            if show_rms_var.get():
                t_max = self.gui.t[-1] if self.gui.t is not None and len(self.gui.t) > 0 else 10

                selected_signal = plot_window_data.get('header', '')
                is_filtered = plot_window_data.get('show_filtered_var', tk.BooleanVar()).get()
                filter_info = None
                if is_filtered and hasattr(self.gui, 'filter_manager'):
                    filter_info = self.gui.filter_manager.get_filter_info()

                def on_rms_zeitbereich(result):
                    zeitbereiche = result.get("RMS", [(None, None)])
                    plot_window_data['rms_zeitbereiche'] = zeitbereiche
                    protocol_logger.info(
                        "LIVE_PLOT_TIME_RANGE signal=%s | type=RMS | ranges=%s",
                        selected_signal,
                        zeitbereiche,
                    )
                    self.update_single_plot(plot_window_data)

                PlotManager.show_zeitbereich_dialog(
                    parent=plot_window,
                    t_max=t_max,
                    callback=on_rms_zeitbereich,
                    title="RMS - Zeitbereich auswählen",
                    selected_signal=selected_signal,
                    is_filtered=is_filtered,
                    filter_info=filter_info,
                    analyse_typen=["RMS"]
                )
            else:
                plot_window_data['rms_zeitbereiche'] = []
                self.update_single_plot(plot_window_data)

        _bind_var(show_avg_var, "avg", _on_avg_toggled)
        _bind_var(show_rms_var, "rms", _on_rms_toggled)
        _bind_var(show_fft_master_var, "fft_master", _on_fft_master_toggled)

        self.update_single_plot(plot_window_data)

        def export_current_signal():
            """Exportiert das aktuelle Signal nach Excel/CSV via FileHandler"""

            show_avg = plot_window_data.get('show_avg_var').get() if plot_window_data.get('show_avg_var') else False
            show_rms = plot_window_data.get('show_rms_var').get() if plot_window_data.get('show_rms_var') else False
            show_diff = plot_window_data.get('show_diff_var').get() if plot_window_data.get('show_diff_var') else False
            show_integral = plot_window_data.get('show_integral_var').get() if plot_window_data.get('show_integral_var') else False

            if self.gui.t is None or not self.gui.signals or not self.gui.headers:
                self.gui.status_label.config(text="Keine Daten zum Export.")
                return
            if self.gui.dt is None:
                self.gui.status_label.config(text="Kein gültiges dt vorhanden.")
                return
            try:
                idx = self.gui.headers.index(selected_signal)
            except ValueError:
                self.gui.status_label.config(text=f"Signal '{selected_signal}' nicht gefunden.")
                return

            t = np.asarray(self.gui.t)
            original = np.asarray(self.gui.signals[idx])
            unit = self.gui.units[idx] if idx < len(self.gui.units) else ""

            try:
                if (self.gui.use_filtered_var.get() and self.gui._is_filter_ready() and 
                    self.gui.filter_manager and self.gui.filter_manager.filter_type != Cfg.Defaults.FILTER_TYP):
                    used = np.asarray(self.gui.filter_manager.apply_filter(original))
                    filter_info = {
                        'filter_type': self.gui.filter_manager.filter_type,
                        'characteristic': self.gui.filter_manager.characteristic,
                        'order': self.gui.filter_manager.order,
                        'cutoff1': self.gui.filter_manager.cutoff_frequency,
                        'cutoff2': self.gui.filter_manager.cutoff_frequency2,
                        'sample_rate': self.gui.filter_manager.sample_rate
                    }
                else:
                    used = original
                    filter_info = {
                        'filter_type': Cfg.Defaults.FILTER_TYP,
                        'characteristic': self.gui.filter_manager.characteristic if self.gui.filter_manager else Cfg.Defaults.FILTER_CHARAKTERISTIK,
                        'order': self.gui.filter_manager.order if self.gui.filter_manager else None,
                        'cutoff1': getattr(self.gui.filter_manager, "cutoff_frequency", None),
                        'cutoff2': getattr(self.gui.filter_manager, "cutoff_frequency2", None),
                        'sample_rate': getattr(self.gui.filter_manager, "sample_rate", None)
                    }

            except Exception as e:
                logger.exception("Filterfehler beim Export: %s", e)
                used = original
                filter_info = {'filter_type': Cfg.Defaults.FILTER_TYP, 'characteristic': Cfg.Defaults.FILTER_CHARAKTERISTIK,
                            'order': None, 'cutoff1': None, 'cutoff2': None, 'sample_rate': None}

            N = min(len(t), len(original), len(used))
            if N < 2:
                self.gui.status_label.config(text="Zu wenige Punkte für Export.")
                return
            t = t[:N]
            original = original[:N]
            used = used[:N]

            f_axis, amp, phase = DataProcessor.compute_fft(used, self.gui.dt)
            window_type = (self.gui.entry6.get().strip() if hasattr(self.gui, "entry6") else Cfg.Defaults.FENSTERTYP) or Cfg.Defaults.FENSTERTYP

            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=f"{selected_signal}_export.xlsx"
            )
            if not save_path:
                self.gui.status_label.config(text="Export abgebrochen.")
                return

            protocol_logger.info(
                "EXPORT_LIVE path=%s | signal=%s | avg=%s | rms=%s | diff=%s | integral=%s | filtered=%s",
                save_path,
                selected_signal,
                show_avg,
                show_rms,
                show_diff,
                show_integral,
                self.gui.use_filtered_var.get() and self.gui._is_filter_ready(),
            )

            success, message = FileHandler.export_signal_data(
                save_path=save_path,
                t=t, original=original, used=used,
                signal_name=selected_signal, unit=unit, dt=self.gui.dt,
                f_axis=f_axis, amp=amp, phase=phase,
                filter_info=filter_info, window_type=window_type,
                show_avg=show_avg, show_rms=show_rms,
                show_diff=show_diff, show_integral=show_integral
            )
            self.gui.status_label.config(text=message)

        export_button = ttk.Button(toolbar_frame, text="Exportieren", command=export_current_signal)
        export_button.pack(side=tk.RIGHT, padx=8, pady=4)
        plot_window_data['export_button'] = export_button

        def on_window_close():
            if plot_window_data in self.gui.open_plot_windows:
                self.gui.open_plot_windows.remove(plot_window_data)
            plot_window.destroy()

        plot_window.protocol("WM_DELETE_WINDOW", on_window_close)

        return plot_window_data

    def update_single_plot(self, plot_window_data):
        """Aktualisiert einen einzelnen Plot (dynamische Achsen je Auswahl)."""
        if not plot_window_data:
            logger.debug("DEBUG: plot_window_data ist None/leer")
            return
        try:
            if not plot_window_data['window'].winfo_exists():
                logger.info("DEBUG: Fenster existiert nicht mehr")
                return
        except Exception as e:
            logger.exception("DEBUG: Exception bei Fenster-Prüfung: %s", e)
            return

        selected = plot_window_data['signal_name']
        fig = plot_window_data['fig']
        canvas = plot_window_data['canvas']
        fig.clear()

        logger.info("DEBUG update_single_plot: selected='%s'", selected)

        if selected == "Overview":
            PlotManager.plot_overview(fig, self.gui.t, self.gui.signals, self.gui.headers, self.gui.units)
            canvas.draw()
            return

        getv = lambda key, default=True: (plot_window_data.get(key).get() if plot_window_data.get(key) is not None else default)
        show_original = getv('show_original_var', True)
        show_filtered = getv('show_filtered_var', False) and self.gui._is_filter_ready()
        show_fft_master = getv('show_fft_master_var', True)
        show_amp = getv('show_amp_var', True) and show_fft_master
        show_phase = getv('show_phase_var', True) and show_fft_master
        fft_zeitbereiche = plot_window_data.get('fft_zeitbereiche', [])
        show_avg = getv('show_avg_var', False)
        show_rms = getv('show_rms_var', False)
        show_diff = getv('show_diff_var', False)
        show_integral = getv('show_integral_var', False)

        avg_zeitbereiche = plot_window_data.get('avg_zeitbereiche', [])
        rms_zeitbereiche = plot_window_data.get('rms_zeitbereiche', [])

        try:
            idx = self.gui.headers.index(selected)
        except (ValueError, IndexError) as e:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Signal '{selected}' nicht gefunden.", ha="center", va="center", transform=ax.transAxes)
            canvas.draw()
            return

        original_signal = self.gui.signals[idx]
        filtered_signal = original_signal
        filter_type = Cfg.Defaults.FILTER_TYP

        if show_filtered and self.gui.filter_manager and self.gui.filter_manager.filter_type != Cfg.Defaults.FILTER_TYP:
            filtered_signal = self.gui.filter_manager.apply_filter(original_signal)
            filter_type = self.gui.filter_manager.filter_type

        fft_daten = []
        fft_farben = ['green', 'orange', 'red', 'blue', 'purple', 'brown']
        if show_amp or show_phase:
            if fft_zeitbereiche:
                for i, (start, ende) in enumerate(fft_zeitbereiche):
                    if start is not None:
                        maske = (self.gui.t >= start) & (self.gui.t <= ende)
                        segment = original_signal[maske]
                    else:
                        segment = original_signal
                    if show_filtered and self.gui.filter_manager and filter_type != Cfg.Defaults.FILTER_TYP:
                        segment = self.gui.filter_manager.apply_filter(segment)
                        label = f"FFT {start}-{ende}s (gefiltert)" if start else "FFT (gefiltert)"
                    else:
                        label = f"FFT {start}-{ende}s" if start else "FFT (ganzes Signal)"
                    f_axis, amp, phase = DataProcessor.compute_fft(segment, self.gui.dt)
                    farbe = fft_farben[i % len(fft_farben)]
                    fft_daten.append((f_axis, amp, phase, label, farbe))
            else:
                segment = original_signal
                if show_filtered and self.gui.filter_manager and filter_type != Cfg.Defaults.FILTER_TYP:
                    segment = self.gui.filter_manager.apply_filter(segment)
                f_axis, amp, phase = DataProcessor.compute_fft(segment, self.gui.dt)
                fft_daten.append((f_axis, amp, phase, "FFT", "green"))

        # Berechne Anzahl Subplots
        num_subplots = 1
        if show_amp:
            num_subplots += 1
        if show_phase:
            num_subplots += 1
        if show_diff:
            num_subplots += 1
        if show_integral:
            num_subplots += 1
        if show_avg and avg_zeitbereiche:
            num_subplots += 2
        if show_rms and rms_zeitbereiche:
            num_subplots += 2

        current_subplot = 1
        unit = self.gui.units[idx] if idx < len(self.gui.units) else ""
        t = self.gui.t
        signal = original_signal

        # Haupt-Signal Plot
        ax1 = fig.add_subplot(num_subplots, 1, current_subplot)
        current_subplot += 1
        if show_original:
            ax1.plot(t, original_signal, color=Cfg.Colors.SIGNAL_ORIGINAL, label=f"Original [{unit}]", alpha=0.7)
        if show_filtered and filter_type != Cfg.Defaults.FILTER_TYP:
            ax1.plot(t, filtered_signal, color="crimson", label=f"Gefiltert ({filter_type}) [{unit}]")
        ax1.set_title(f"{selected} [{unit}]")
        ax1.set_xlabel("Zeit [s]")
        ax1.set_ylabel(f"Amplitude [{unit}]")
        ax1.grid(True)
        ax1.legend()

        # FFT Amplitude (Overlay)
        if show_amp and fft_daten:
            ax_amp = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for f_axis, amp, phase, label, farbe in fft_daten:
                ax_amp.plot(f_axis, amp, color=farbe, label=label)
            ax_amp.set_title(f"FFT Amplitude [{unit}]")
            ax_amp.set_xlabel("Frequenz [Hz]")
            ax_amp.set_ylabel("Amplitude")
            ax_amp.grid(True)
            ax_amp.legend()

        # FFT Phase (Overlay)
        if show_phase and fft_daten:
            ax_phase = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for f_axis, amp, phase, label, farbe in fft_daten:
                ax_phase.plot(f_axis, phase, color=farbe, label=label)
            ax_phase.set_title(f"FFT Phase [rad]")
            ax_phase.set_xlabel("Frequenz [Hz]")
            ax_phase.set_ylabel("Phase [rad]")
            ax_phase.grid(True)
            ax_phase.legend()

        # Differential Subplot
        if show_diff:
            ax_diff = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            diff_signal = np.gradient(signal, t)
            ax_diff.plot(t, diff_signal, color="darkorange")
            ax_diff.set_title(f"Differential (Ableitung) [{unit}/s]")
            ax_diff.set_xlabel("Zeit [s]")
            ax_diff.set_ylabel(f"d/dt [{unit}/s]")
            ax_diff.grid(True)

        # Integral Subplot
        if show_integral:
            ax_int = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            dt_arr = np.diff(t)
            integral_signal = np.concatenate([[0], np.cumsum((signal[:-1] + signal[1:]) * dt_arr / 2)])
            ax_int.plot(t, integral_signal, color="teal")
            ax_int.set_title(f"Integral [{unit}*s]")
            ax_int.set_xlabel("Zeit [s]")
            ax_int.set_ylabel(f"Integral [{unit}*s]")
            ax_int.grid(True)

        # AVG Subplots (Overlay)
        if show_avg and avg_zeitbereiche:
            avg_farben = ['red', 'blue', 'green', 'orange', 'purple', 'brown']

            ax_avg = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for i, (start, ende) in enumerate(avg_zeitbereiche):
                farbe = avg_farben[i % len(avg_farben)]
                if start is None:
                    used_avg = signal
                    t_used = t
                    avg_val = float(np.nanmean(signal))
                    label = f"Ganzes Signal, AVG={avg_val:.4g}"
                else:
                    maske = (t >= start) & (t <= ende)
                    used_avg = signal[maske]
                    t_used = t[maske]
                    avg_val = float(np.nanmean(used_avg))
                    label = f"{start}-{ende}s, AVG={avg_val:.4g}"
                ax_avg.plot(t_used, used_avg, color=farbe, alpha=0.7, label=label)
                ax_avg.axhline(avg_val, color=farbe, linestyle="--", linewidth=2)
            ax_avg.set_title(f"{selected} - AVG Analyse [{unit}]")
            ax_avg.set_xlabel("Zeit [s]")
            ax_avg.set_ylabel(f"Amplitude [{unit}]")
            ax_avg.grid(True)
            ax_avg.legend()

            ax_hist = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for i, (start, ende) in enumerate(avg_zeitbereiche):
                farbe = avg_farben[i % len(avg_farben)]
                if start is None:
                    used_avg = signal
                    avg_val = float(np.nanmean(signal))
                    label = f"Ganzes Signal"
                else:
                    maske = (t >= start) & (t <= ende)
                    used_avg = signal[maske]
                    avg_val = float(np.nanmean(used_avg))
                    label = f"{start}-{ende}s"
                ax_hist.hist(used_avg[~np.isnan(used_avg)], bins=50, color=farbe, alpha=0.5, label=label)
                ax_hist.axvline(avg_val, color=farbe, linestyle="--", linewidth=2)
            ax_hist.set_title(f"Histogramm - AVG Vergleich [{unit}]")
            ax_hist.set_xlabel(f"Wert [{unit}]")
            ax_hist.set_ylabel("Häufigkeit")
            ax_hist.grid(True)
            ax_hist.legend()

        # RMS Subplots (Overlay)
        if show_rms and rms_zeitbereiche:
            rms_farben = ['orange', 'blue', 'green', 'red', 'purple', 'brown']

            ax_rms = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for i, (start, ende) in enumerate(rms_zeitbereiche):
                farbe = rms_farben[i % len(rms_farben)]
                if start is None:
                    used_rms = signal
                    t_used = t
                    rms_val = float(np.sqrt(np.nanmean(signal**2)))
                    label = f"Ganzes Signal, RMS={rms_val:.4g}"
                else:
                    maske = (t >= start) & (t <= ende)
                    used_rms = signal[maske]
                    t_used = t[maske]
                    rms_val = float(np.sqrt(np.nanmean(used_rms**2)))
                    label = f"{start}-{ende}s, RMS={rms_val:.4g}"
                ax_rms.plot(t_used, used_rms, color=farbe, alpha=0.7, label=label)
                ax_rms.axhline(rms_val, color=farbe, linestyle="--", linewidth=2)
                ax_rms.axhline(-rms_val, color=farbe, linestyle="--", linewidth=2)
            ax_rms.set_title(f"{selected} - RMS Analyse [{unit}]")
            ax_rms.set_xlabel("Zeit [s]")
            ax_rms.set_ylabel(f"Amplitude [{unit}]")
            ax_rms.grid(True)
            ax_rms.legend()

            ax_sq = fig.add_subplot(num_subplots, 1, current_subplot)
            current_subplot += 1
            for i, (start, ende) in enumerate(rms_zeitbereiche):
                farbe = rms_farben[i % len(rms_farben)]
                if start is None:
                    used_rms = signal
                    t_used = t
                    rms_val = float(np.sqrt(np.nanmean(signal**2)))
                    label = f"Ganzes Signal"
                else:
                    maske = (t >= start) & (t <= ende)
                    used_rms = signal[maske]
                    t_used = t[maske]
                    rms_val = float(np.sqrt(np.nanmean(used_rms**2)))
                    label = f"{start}-{ende}s"
                ax_sq.plot(t_used, used_rms**2, color=farbe, alpha=0.7, label=label)
                ax_sq.axhline(rms_val**2, color=farbe, linestyle="--", linewidth=2)
            ax_sq.set_title(f"Signal² - RMS Vergleich [{unit}^2]")
            ax_sq.set_xlabel("Zeit [s]")
            ax_sq.set_ylabel(f"Amplitude² [{unit}²]")
            ax_sq.grid(True)
            ax_sq.legend()

        fig.tight_layout()
        canvas.draw()
