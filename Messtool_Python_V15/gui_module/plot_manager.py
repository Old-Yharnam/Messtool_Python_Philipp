"""
Plot Manager - Basis-Visualisierungsfunktionen
===============================================
Stellt statische Methoden für Basis-Plot-Operationen bereit:
Zeit- und Frequenzbereichsdarstellung, FFT-Plots, Filter-Charakteristiken,
interaktive Cursor und Multi-Signal-Overlays.
"""

import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.signal import cheby1, freqz
import mplcursors
import matplotlib
from matplotlib import gridspec
import seaborn as sns
import logging
from hilfsklassen.zentrales_logging import get_protocol_logger

from Messtool_Python_V15.setup import Cfg

logger = logging.getLogger(__name__)
protocol_logger = get_protocol_logger()

class PlotManager:
    """Klasse für Basis-Plot-Funktionen mit gemeinsamen Parametern"""

    @staticmethod
    def _apply_axis_margin(start, end, margin_percent=5):
        """
        Fügt prozentuale Margin zu Start/End hinzu für bessere Achsen-Sichtbarkeit

        Args:
            start: Start-Wert (Zeit oder Frequenz)
            end: End-Wert (Zeit oder Frequenz)
            margin_percent: Margin in % der Gesamtbreite (default 5%)

        Returns:
            tuple: (new_start, new_end) mit Margin

        Beispiel:
            start_zeit=5, end_zeit=10, margin_percent=5
            → start_zeit=4.75, end_zeit=10.25 (Margin=0.25s)
        """
        range_width = end - start
        if range_width <= 0:
            return start, end
        margin = (range_width / 100) * margin_percent
        return start - margin, end + margin

    @staticmethod
    def save_time_domain_plot(t, signal, header, unit, time, figure_number, save_path):
        plt.figure(figure_number)
        plt.plot(t, signal)
        plt.grid()
        plt.title(f"{header} [{unit}] - Starttime: {time}")
        plt.legend([header])
        plt.xlabel("Time [s]")
        plt.ylabel(f"{header} [{unit}]")
        plt.savefig(f"{save_path}/signal_{header}_time.png")
        plt.close()

    @staticmethod
    def add_cursor_and_zoom_logic(
        fig,
        axes,
        signal_data,
        axes_groups=None,
        sync_enabled=None,
        range_selected_callback=None,
        range_cleared_callback=None,
        selection_filter=None,
    ):
        """Fügt interaktive Cursor- und Zoom-Logik zu allen Axes hinzu"""
        vlines = {}
        hlines = {}
        annotations = {}
        selection_start = {}
        selection_lines = {}
        original_limits = {}
        hover_state = {"ax": None, "x": None, "y": None}

        for ax in axes:
            vlines[ax] = ax.axvline(x=0, color='red', linestyle='--', linewidth=1, visible=False)
            hlines[ax] = ax.axhline(y=0, color='red', linestyle='--', linewidth=1, visible=False)
            annotations[ax] = ax.annotate('', xy=(0, 0), xytext=(8, 8),
                                        textcoords='offset points',
                                        ha='left', va='bottom',
                                        fontsize=9,
                                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            selection_start[ax] = None
            selection_lines[ax] = (
                ax.axvline(x=0, color='blue', linestyle=':', linewidth=1, visible=False),
                ax.axvline(x=0, color='blue', linestyle=':', linewidth=1, visible=False)
            )
            original_limits[ax] = (ax.get_xlim(), ax.get_ylim())

        def _get_series_list(ax):
            data = signal_data.get(ax)
            if data is None:
                return []
            return data if isinstance(data, list) else [data]

        def _find_best_snap(ax, event):
            series_list = _get_series_list(ax)
            if not series_list:
                return None

            best = None
            mouse_xy = np.array([event.x, event.y], dtype=float)
            for series in series_list:
                if len(series) == 2:
                    xdata, ydata = series
                    label = None
                else:
                    xdata, ydata, label = series

                x_arr = np.array(xdata)
                idx = np.argmin(np.abs(x_arr - event.xdata))
                x_snap = x_arr[idx]
                y_snap = np.array(ydata)[idx]

                snap_xy = ax.transData.transform((x_snap, y_snap))
                dist = np.linalg.norm(snap_xy - mouse_xy)

                if best is None or dist < best["dist"]:
                    best = {"x": x_snap, "y": y_snap, "label": label, "dist": dist}

            return best

        def on_move(event):
            if event.inaxes is None or event.xdata is None:
                return
            ax = event.inaxes
            if ax not in signal_data:
                return
            best = _find_best_snap(ax, event)
            if best is None:
                return

            x_snap = best["x"]
            y_snap = best["y"]

            if hover_state["ax"] != ax:
                prev_ax = hover_state["ax"]
                if prev_ax is not None:
                    vlines[prev_ax].set_visible(False)
                    hlines[prev_ax].set_visible(False)
                    annotations[prev_ax].set_visible(False)
                hover_state["ax"] = ax

            if hover_state["x"] == x_snap and hover_state["y"] == y_snap:
                return

            hover_state["x"] = x_snap
            hover_state["y"] = y_snap

            vlines[ax].set_xdata([x_snap, x_snap])
            hlines[ax].set_ydata([y_snap, y_snap])
            vlines[ax].set_visible(True)
            hlines[ax].set_visible(True)

            label = f"{best['label']} | " if best["label"] else ""
            annotations[ax].set_text(f"{label}x={x_snap:.3f}, y={y_snap:.3f}")
            annotations[ax].xy = (x_snap, y_snap)
            annotations[ax].set_visible(True)
            fig.canvas.draw_idle()

        def on_click(event):
            if event.inaxes is None or event.xdata is None:
                return
            if event.button != 1:
                return

            ax = event.inaxes
            best = _find_best_snap(ax, event)
            if best is None:
                return

            start_x = selection_start.get(ax)
            start_line, end_line = selection_lines[ax]

            if start_x is None:
                selection_start[ax] = best["x"]
                start_line.set_xdata([best["x"], best["x"]])
                start_line.set_visible(True)
                end_line.set_visible(False)
                fig.canvas.draw_idle()
                return

            x0, x1 = sorted([start_x, best["x"]])
            selection_start[ax] = None
            start_line.set_xdata([x0, x0])
            end_line.set_xdata([x1, x1])
            start_line.set_visible(True)
            end_line.set_visible(True)

            if range_selected_callback:
                allow_selection = True
                if selection_filter is not None:
                    try:
                        allow_selection = selection_filter(ax)
                    except Exception:
                        allow_selection = False
                if allow_selection:
                    widget = getattr(fig.canvas, "get_tk_widget", None)
                    if widget:
                        fig.canvas.get_tk_widget().after(0, lambda: range_selected_callback(x0, x1, ax))
                    else:
                        range_selected_callback(x0, x1, ax)

            y_values = []
            for series in _get_series_list(ax):
                if len(series) == 2:
                    xdata, ydata = series
                else:
                    xdata, ydata, _ = series
                x_arr = np.array(xdata)
                y_arr = np.array(ydata)
                mask = (x_arr >= x0) & (x_arr <= x1)
                if np.any(mask):
                    y_values.append(y_arr[mask])

            if y_values:
                y_concat = np.concatenate(y_values)
                y_min = float(np.min(y_concat))
                y_max = float(np.max(y_concat))
                y_min, y_max = PlotManager._apply_axis_margin(y_min, y_max, margin_percent=5)
            else:
                y_min, y_max = ax.get_ylim()

            x0, x1 = PlotManager._apply_axis_margin(x0, x1, margin_percent=5)
            new_xlim = [x0, x1]
            new_ylim = [y_min, y_max]

            synced = False
            if axes_groups:
                for group_name, group_axes in axes_groups.items():
                    if ax in group_axes and len(group_axes) > 1:
                        sync_is_enabled = True
                        if sync_enabled and group_name in sync_enabled:
                            sync_is_enabled = sync_enabled[group_name].get()

                        if sync_is_enabled:
                            for a in group_axes:
                                a.set_xlim(new_xlim)
                                a.set_ylim(new_ylim)
                        else:
                            ax.set_xlim(new_xlim)
                            ax.set_ylim(new_ylim)
                        synced = True
                        break

            if not synced:
                ax.set_xlim(new_xlim)
                ax.set_ylim(new_ylim)

            fig.canvas.draw_idle()

        def reset_selection():
            for ax in axes:
                selection_start[ax] = None
                start_line, end_line = selection_lines[ax]
                start_line.set_visible(False)
                end_line.set_visible(False)
                if ax in original_limits:
                    xlim, ylim = original_limits[ax]
                    ax.set_xlim(xlim)
                    ax.set_ylim(ylim)
            fig.canvas.draw_idle()
            if range_cleared_callback:
                widget = getattr(fig.canvas, "get_tk_widget", None)
                if widget:
                    fig.canvas.get_tk_widget().after(0, range_cleared_callback)
                else:
                    range_cleared_callback()

        def on_leave(event):
            ax = event.inaxes
            if ax is None:
                return
            if ax in vlines:
                vlines[ax].set_visible(False)
                hlines[ax].set_visible(False)
                annotations[ax].set_visible(False)
                if hover_state["ax"] == ax:
                    hover_state["ax"] = None
                    hover_state["x"] = None
                    hover_state["y"] = None
            fig.canvas.draw_idle()

        def on_scroll(event):
            ax = event.inaxes
            if ax is None:
                return
            scale = 1.2 if event.button == 'down' else 0.8
            xdata = event.xdata
            ydata = event.ydata
            if xdata is None or ydata is None:
                return

            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            new_xlim = [xdata - (xdata - xlim[0]) * scale, xdata + (xlim[1] - xdata) * scale]
            new_ylim = [ydata - (ydata - ylim[0]) * scale, ydata + (ylim[1] - ydata) * scale]

            synced = False
            if axes_groups:
                for group_name, group_axes in axes_groups.items():
                    if ax in group_axes and len(group_axes) > 1:
                        sync_is_enabled = True
                        if sync_enabled and group_name in sync_enabled:
                            sync_is_enabled = sync_enabled[group_name].get()

                        if sync_is_enabled:
                            for a in group_axes:
                                a.set_xlim(new_xlim)
                                a.set_ylim(new_ylim)
                        else:
                            ax.set_xlim(new_xlim)
                            ax.set_ylim(new_ylim)
                        synced = True
                        break

            if not synced:
                ax.set_xlim(new_xlim)
                ax.set_ylim(new_ylim)

            fig.canvas.draw_idle()

        fig.canvas.mpl_connect('motion_notify_event', on_move)
        fig.canvas.mpl_connect('axes_leave_event', on_leave)
        fig.canvas.mpl_connect('scroll_event', on_scroll)
        fig.canvas.mpl_connect('button_press_event', on_click)
        fig._reset_zoom_selection = reset_selection

    @staticmethod
    def show_zeitbereich_dialog(parent, t_max, callback, title="Zeitbereich auswählen",
                                 selected_signal=None, is_filtered=False, filter_info=None,
                                 analyse_typen=None):
        """
        Zentraler Zeitbereich-Dialog mit Notebook für mehrere Analyse-Typen.

        Args:
            parent: Parent-Fenster
            t_max: Maximale Zeit (für Voreinstellung Ende-Zeit)
            callback: Funktion die mit dict {analyse_typ: [(start, ende), ...]} aufgerufen wird
            title: Dialog-Titel
            selected_signal: Name des ausgewählten Signals (optional)
            is_filtered: Ob gefiltert wird
            filter_info: Dict mit 'type', 'order', 'characteristic' (optional)
            analyse_typen: Liste von Analyse-Typen für Tabs, z.B. ["AVG", "RMS", "FFT"]
        """
        if analyse_typen is None:
            analyse_typen = ["Analyse"]

        dialog = tb.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("500x450")
        dialog.transient(parent)
        dialog.grab_set()

        header_frame = ttk.Frame(dialog)
        header_frame.pack(padx=10, pady=10, fill="x")

        if selected_signal:
            signal_length_text = f" ({t_max:.2f} s)" if t_max else ""
            ttk.Label(header_frame, text=f"Ausgewähltes Signal: {selected_signal}{signal_length_text}", 
                      font=("Arial", 10, "bold")).pack(anchor="w")

        if is_filtered and filter_info:
            filter_text = f"Gefiltert: {filter_info.get('type', '-')}, " \
                         f"Ordnung: {filter_info.get('order', '-')}, " \
                         f"Charakteristik: {filter_info.get('characteristic', '-')}"
            ttk.Label(header_frame, text=filter_text).pack(anchor="w")
        else:
            ttk.Label(header_frame, text="Ungefiltert").pack(anchor="w")

        notebook = ttk.Notebook(dialog)
        notebook.pack(padx=10, pady=10, fill="both", expand=True)

        tab_data = {}

        def create_tab(notebook, analyse_typ, t_max):
            """Erstellt einen Tab mit eigenem Scope für Variablen (löst Closure-Problem)."""
            tab_frame = ttk.Frame(notebook)
            notebook.add(tab_frame, text=analyse_typ)

            this_ganzes_signal_var = tk.BooleanVar(value=True)
            this_zeitbereich_felder = []

            checkbox_frame = ttk.Frame(tab_frame)
            checkbox_frame.pack(padx=10, pady=(10, 5))

            felder_frame = ttk.Frame(tab_frame)
            felder_frame.pack(padx=10, pady=5, fill="both", expand=True)

            plus_button = ttk.Button(tab_frame, text="+ Zeitbereich hinzufügen")
            plus_button.pack(pady=5)

            def toggle_felder():
                state = "disabled" if this_ganzes_signal_var.get() else "normal"
                for entry_start, entry_ende in this_zeitbereich_felder:
                    entry_start.config(state=state)
                    entry_ende.config(state=state)
                plus_button.config(state="disabled" if this_ganzes_signal_var.get() or len(this_zeitbereich_felder) >= 12 else "normal")

            def feld_hinzufuegen():
                if len(this_zeitbereich_felder) >= 12:
                    return
                zeile = len(this_zeitbereich_felder)

                row_frame = ttk.Frame(felder_frame)
                row_frame.pack(fill="x", pady=2)

                ttk.Label(row_frame, text=f"Zeitbereich {zeile + 1}:", width=15).pack(side=tk.LEFT)

                start_entry = ttk.Entry(row_frame, width=10)
                start_entry.insert(0, f"{zeile * 0.5:.1f}")
                start_entry.pack(side=tk.LEFT, padx=2)

                ttk.Label(row_frame, text="-").pack(side=tk.LEFT)

                ende_entry = ttk.Entry(row_frame, width=10)
                ende_val = min((zeile + 1) * 0.5, t_max) if t_max else (zeile + 1) * 0.5
                ende_entry.insert(0, f"{ende_val:.1f}")
                ende_entry.pack(side=tk.LEFT, padx=2)

                ttk.Label(row_frame, text="[s]").pack(side=tk.LEFT)

                this_zeitbereich_felder.append((start_entry, ende_entry))

                if len(this_zeitbereich_felder) >= 12:
                    plus_button.config(state="disabled")

            feld_hinzufuegen()

            plus_button.config(command=feld_hinzufuegen)

            ganzes_signal_checkbox = ttk.Checkbutton(
                checkbox_frame, 
                text="Ganzes Signal verwenden", 
                variable=this_ganzes_signal_var,
                command=toggle_felder
            )
            ganzes_signal_checkbox.pack()

            toggle_felder()

            return {
                'ganzes_signal_var': this_ganzes_signal_var,
                'zeitbereich_felder': this_zeitbereich_felder
            }

        for analyse_typ in analyse_typen:
            tab_data[analyse_typ] = create_tab(notebook, analyse_typ, t_max)

        def berechnen():
            result = {}
            for analyse_typ, data in tab_data.items():
                zeitbereiche = []
                if data['ganzes_signal_var'].get():
                    zeitbereiche.append((None, None))
                else:
                    for start_entry, ende_entry in data['zeitbereich_felder']:
                        try:
                            start = float(start_entry.get().strip())
                            ende = float(ende_entry.get().strip())
                            zeitbereiche.append((start, ende))
                        except ValueError:
                            continue
                result[analyse_typ] = zeitbereiche

            protocol_logger.info(
                "PLOT_TIME_RANGE title=%s | signal=%s | analyses=%s | ranges=%s",
                title,
                selected_signal,
                analyse_typen,
                result,
            )

            dialog.destroy()
            callback(result)

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="OK", command=berechnen, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

    @staticmethod
    def save_frequency_domain_plot(f, sig_abs, sig_arg, header, unit, figure_number, save_path):
        plt.figure(figure_number)

        plt.subplot(2,1,1)
        plt.plot(f, sig_abs)
        plt.grid()
        plt.title(f"{header} [{unit}]")
        plt.xlabel("Frequenz [Hz]")
        plt.ylabel("Amplitude") 
        plt.legend([header + "[" + unit + "]"])

        plt.subplot(2,1,2)
        plt.plot(f, np.angle(np.exp(1j * sig_arg), deg=True))
        plt.grid()
        plt.xlabel("Frequency [Hz]")
        plt.ylabel("Phase [Grad]")

        plt.tight_layout()
        plt.savefig(f"{save_path}/signal_{header}_freq.png")
        plt.close()

    @staticmethod
    def save_overview_plot(t, signals, headers, units, time, save_path):
        num_signals = len(signals)
        plt.figure(109, figsize=(12, 16))
        for i, (sig, header, unit) in enumerate(zip(signals, headers, units)):
            plt.subplot(num_signals, 1, i + 1)
            plt.plot(t, sig)
            plt.grid()
            if i == 0:
                plt.title(f"{header} [{unit}] - Starttime: {time}")
            plt.legend([header + "[" + unit + "]"])
            plt.ylabel(f"[{unit}]")
        plt.xlabel("Time [s]")
        plt.tight_layout()
        plt.savefig(f"{save_path}/overview.png")
        plt.close()

    @staticmethod
    def _setup_subplot_grid(fig, n_signals, plot_types, is_filtered=False):
        """Erstellt Subplot-Grid: Jedes Signal bekommt eigenen Subplot, gruppiert nach Plot-Typ."""
        n_types = len(plot_types)
        total_subplots = n_signals * n_types

        gs = gridspec.GridSpec(total_subplots, 1)
        axes_dict = {ptype: [] for ptype in plot_types}

        subplot_idx = 0
        for ptype in plot_types:
            for sig_idx in range(n_signals):
                ax = fig.add_subplot(gs[subplot_idx])
                axes_dict[ptype].append(ax)
                subplot_idx += 1

        return axes_dict

    @staticmethod
    def _configure_ax(ax, ylabel, xlabel=None, title=None, show_legend=True):
        """Konfiguriert einen Subplot einheitlich."""
        ax.set_ylabel(ylabel)
        if xlabel:
            ax.set_xlabel(xlabel)
        if title:
            ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.7)
        if show_legend:
            ax.legend(loc="upper right")

    @staticmethod
    def _hide_xticklabels(axes_list):
        """Versteckt X-Achsen-Labels für alle Axes in der Liste."""
        for ax in axes_list:
            plt.setp(ax.get_xticklabels(), visible=False)

    @staticmethod
    def plot_overview(fig, t, signals, headers, units):
        """Erstellt Übersichtsplot aller Signale."""
        exclude_columns = ['SECTION', 'LOGDATA', 'Nb', 'Type', 'Date', 'Time']
        filtered_data = []
        for i, header in enumerate(headers):
            if header not in exclude_columns and i < len(signals):
                filtered_data.append((signals[i], header, units[i] if i < len(units) else ''))

        if not filtered_data:
            return

        filtered_signals, filtered_headers, filtered_units = zip(*filtered_data)
        num_signals = len(filtered_signals)

        for i, (sig, header, unit) in enumerate(zip(filtered_signals, filtered_headers, filtered_units)):
            ax = fig.add_subplot(num_signals, 1, i+1)
            ax.plot(t, sig, label=f"{header} [{unit}]", linewidth=1.2)
            ax.set_ylabel(f"[{unit}]", fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right', fontsize=9)
            ax.tick_params(labelsize=8)
            if i == num_signals - 1:
                ax.set_xlabel("Zeit [s]", fontsize=10)

        fig.suptitle(f"Übersicht aller Signale ({num_signals} Kanäle) [Einheiten gemischt]", fontsize=14, fontweight='bold')
        fig.tight_layout()
        fig.subplots_adjust(top=0.95, hspace=0.3)

    @staticmethod
    def plot_filter_response(fig, w, magnitude_db, phase_deg, filter_info):
        """Zeichnet Filter-Frequenzgang (Magnitude + Phase)."""
        if w is not None and magnitude_db is not None and phase_deg is not None:
            ax1 = fig.add_subplot(2, 1, 1)
            ax1.plot(w, magnitude_db, 'b-', linewidth=2)
            ax1.set_ylabel('Magnitude [dB]')
            ax1.set_title(f"{filter_info['characteristic'].capitalize()} {filter_info['type']} - {filter_info['order']}. Ordnung")
            ax1.grid(True, alpha=0.3)
            ax1.set_xscale('log')
            ax1.set_xlim(1, filter_info['sample_rate'] / 2 if filter_info['sample_rate'] else 1000)

            ax2 = fig.add_subplot(2, 1, 2)
            ax2.plot(w, phase_deg, 'r-', linewidth=2)
            ax2.set_ylabel('Phase [Grad]')
            ax2.set_xlabel('Frequenz [Hz]')
            ax2.grid(True, alpha=0.3)
            ax2.set_xscale('linear')
            ax2.set_xlim(0, filter_info['sample_rate'] / 2 if filter_info['sample_rate'] else 1000)

            if filter_info['cutoff']:
                ax1.axvline(x=filter_info['cutoff'], color='red', linestyle='--', alpha=0.7,
                            label=f"Grenzfrequenz: {filter_info['cutoff']} Hz")
                ax2.axvline(x=filter_info['cutoff'], color='red', linestyle='--', alpha=0.7)
                ax1.legend()

                if filter_info['type'] == "Bandpass" and filter_info.get('cutoff2'):
                    ax1.axvline(x=filter_info['cutoff2'], color='orange', linestyle='--', alpha=0.7,
                                label=f"Grenzfrequenz 2: {filter_info['cutoff2']} Hz")
                    ax2.axvline(x=filter_info['cutoff2'], color='orange', linestyle='--', alpha=0.7)
                    ax1.legend()
        else:
            ax = fig.add_subplot(1, 1, 1)
            ax.text(0.5, 0.5, 'Kein gültiger Filter\noder\nParameter nicht gesetzt',
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.set_xticks([])
            ax.set_yticks([])

        fig.tight_layout()

    @staticmethod
    def plot_selected_signals(parent_window, selected_headers, signals, units, t, dt, 
                            header_to_signal_idx, show_avg, show_rms, show_diff, 
                            show_integral, use_filtered, filter_manager):
        """Erstellt Overlay-Plot für mehrere Signale."""

        if not selected_headers:
            logger.info("Keine Signale ausgewählt")
            return

        overlay_window = tb.Toplevel(parent_window)
        overlay_window.title("Überlagerte Signale")
        overlay_window.geometry("1200x700")

        plot_frame = ttk.Frame(overlay_window)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        fig = plt.Figure(figsize=(14, 8))

        use_bottom = show_diff or show_integral
        if use_bottom:
            ax_top = fig.add_subplot(211)
            ax_bottom = fig.add_subplot(212, sharex=ax_top)
        else:
            ax_top = fig.add_subplot(111)
            ax_bottom = None

        colors = plt.cm.get_cmap('Set1', len(selected_headers))

        filter_label_suffix = ""
        if use_filtered and filter_manager is not None:
            filter_label_suffix = f" (Gefiltert: {filter_manager.filter_type})"

        for i, hdr in enumerate(selected_headers):
            sig_idx = header_to_signal_idx.get(hdr, None)
            if sig_idx is None or sig_idx >= len(signals):
                continue

            sig = signals[sig_idx]
            unit = units[sig_idx] if sig_idx < len(units) else ""

            used = sig
            if use_filtered and filter_manager is not None:
                try:
                    used = filter_manager.apply_filter(sig)
                    ax_top.plot(t, sig, color=colors(i), alpha=0.30,
                                label=f"{hdr} [{unit}] (Original)")
                    ax_top.plot(t, used, color=colors(i), linewidth=1.8,
                                label=f"{hdr} [{unit}]{filter_label_suffix}")
                except Exception:
                    ax_top.plot(t, sig, color=colors(i), linewidth=1.5,
                                label=f"{hdr} [{unit}]")
            else:
                ax_top.plot(t, sig, color=colors(i), linewidth=1.5,
                            label=f"{hdr} [{unit}]")

            if show_avg:
                try:
                    avg_val = float(np.nanmean(used))
                    ax_top.axhline(avg_val, color=colors(i), linestyle="--",
                                alpha=0.5, linewidth=1.2,
                                label=f"{hdr} AVG={avg_val:.6g} {unit}")
                except Exception:
                    pass

            if show_rms:
                try:
                    rms_val = float(np.sqrt(np.nanmean(used**2)))
                    ax_top.axhline(+rms_val, color=colors(i), linestyle=":",
                                alpha=0.6, linewidth=1.2,
                                label=f"{hdr} +RMS={rms_val:.6g} {unit}")
                except Exception:
                    pass

        ax_top.set_title("Überlagerte Signale [Einheiten: gemischt]")
        ax_top.set_xlabel("Zeit [s]")
        ax_top.set_ylabel("Amplitude")
        ax_top.grid(True)
        ax_top.legend(loc="upper right", fontsize=9)

        if use_bottom and ax_bottom is not None:
            for i, hdr in enumerate(selected_headers):
                sig_idx = header_to_signal_idx.get(hdr, None)
                if sig_idx is None or sig_idx >= len(signals):
                    continue
                sig = signals[sig_idx]
                unit = units[sig_idx] if sig_idx < len(units) else ""
                used = sig
                if use_filtered and filter_manager is not None:
                    try:
                        used = filter_manager.apply_filter(sig)
                    except Exception:
                        used = sig

                if show_diff:
                    try:
                        diff = np.gradient(used, dt)
                        unit_diff = f"{unit}/s" if unit else "1/s"
                        ax_bottom.plot(t, diff, color=colors(i), alpha=0.85,
                                    label=f"d({hdr})/dt [{unit_diff}]")
                    except Exception:
                        pass

                if show_integral:
                    try:
                        integ = np.cumsum(used) * dt
                        unit_int = f"{unit}·s" if unit else "unit·s"
                        ax_bottom.plot(t, integ, color=colors(i), linestyle="--",
                                    alpha=0.90, label=f"∫{hdr} dt [{unit_int}]")
                    except Exception:
                        pass

            ax_bottom.set_title("Differential / Integral (ausgewählt) [Einheiten: gemischt]")
            ax_bottom.set_xlabel("Zeit [s]")
            ax_bottom.set_ylabel("Wert")
            ax_bottom.grid(True)
            ax_bottom.legend(loc="lower right", fontsize=8)

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        toolbar_frame = ttk.Frame(plot_frame)
        toolbar_frame.pack(side=tk.TOP, fill=tk.X)
        NavigationToolbar2Tk(canvas, toolbar_frame)

        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        canvas.draw()

    @staticmethod
    def plot_signal_analysis(fig, t, original_signal, filtered_signal, signal_name, unit, dt,
                            show_original=True, show_filtered=False, filter_type=None,
                            show_avg=False, show_rms=False, show_diff=False, show_integral=False,
                            show_amp=False, show_phase=False, f_axis=None, amp=None, phase=None,
                            filter_order=None, filter_characteristic=None):
        """Zeichnet Signal-Analyse-Plot mit Zeit, FFT, AVG, RMS, Diff, Integral."""

        rows = 1 + int(show_amp) + int(show_phase)
        gs = fig.add_gridspec(nrows=max(rows, 1), ncols=1, height_ratios=[2] + [1]*(max(rows, 1)-1), hspace=0.35)

        ax1 = fig.add_subplot(gs[0, 0])
        drew_any = False

        if show_original and original_signal is not None:
            ax1.plot(t, original_signal, label="Original", alpha=0.8, color='blue')
            drew_any = True

        if show_filtered and filtered_signal is not None and filter_type != Cfg.Defaults.FILTER_TYP:
            ax1.plot(t, filtered_signal, label=f"Gefiltert ({filter_type})", color='red', linewidth=2)
            drew_any = True

        chosen = filtered_signal if (show_filtered and filter_type != Cfg.Defaults.FILTER_TYP and filtered_signal is not None) else original_signal

        if show_avg and chosen is not None:
            avg_val = float(np.nanmean(chosen))
            ax1.axhline(avg_val, color="orange", linestyle="--", linewidth=2, label=f"AVG = {avg_val:.6g} {unit}")
            drew_any = True

        if show_rms and chosen is not None:
            rms_val = float(np.sqrt(np.nanmean(chosen**2)))
            ax1.axhline(+rms_val, color="purple", linestyle="--", linewidth=1.6, label=f"+RMS = {rms_val:.6g} {unit}")
            drew_any = True

        if (show_diff or show_integral) and chosen is not None and dt is not None:
            ax1b = ax1.twinx()
            if show_diff:
                diff = np.gradient(chosen, dt)
                unit_diff = f"{unit}/s" if unit else "1/s"
                ax1b.plot(t, diff, color="crimson", alpha=0.8, label=f"d/dt [{unit_diff}]")
                ax1b.set_ylabel(unit_diff)
            if show_integral:
                integ = np.cumsum(chosen) * dt
                unit_int = f"{unit}·s" if unit else "unit·s"
                ax1b.plot(t, integ, color="darkgreen", alpha=0.8, label=f"Integral [{unit_int}]")
                ax1b.set_ylabel(unit_int)
            ax1b.legend(loc='lower right', fontsize=8)

        if not drew_any:
            ax1.text(0.5, 0.5, "Keine Zeitkurve ausgewählt", ha="center", va="center", transform=ax1.transAxes)

        ax1.set_title(f"{signal_name} [{unit}]")
        ax1.set_xlabel("Time [s]")
        ax1.set_ylabel(f"[{unit}]")
        ax1.grid(True)
        if drew_any:
            ax1.legend(loc='upper right', fontsize=9)

        row_cursor = 1
        if show_amp and f_axis is not None and amp is not None:
            ax2 = fig.add_subplot(gs[row_cursor, 0])
            row_cursor += 1
            filter_title = ""
            if show_filtered and filter_type != Cfg.Defaults.FILTER_TYP:
                if filter_order is not None and filter_characteristic is not None:
                    filter_title = f" (Gefiltert: {filter_type}, {filter_order}, {filter_characteristic})"
                else:
                    filter_title = f" (Gefiltert: {filter_type})"
            ax2.plot(f_axis, amp)
            ax2.set_title(f"Frequenz Spektrum{filter_title} [{unit}]")
            ax2.set_xlabel("Frequenz [Hz]")
            ax2.set_ylabel("Amplitude")
            ax2.grid(True)

        if show_phase and f_axis is not None and phase is not None:
            ax3 = fig.add_subplot(gs[row_cursor, 0])
            ax3.plot(f_axis, phase)
            filter_title = ""
            if show_filtered and filter_type != Cfg.Defaults.FILTER_TYP:
                if filter_order is not None and filter_characteristic is not None:
                    filter_title = f" (Gefiltert: {filter_type}, {filter_order}, {filter_characteristic})"
                else:
                    filter_title = f" (Gefiltert: {filter_type})"
            ax3.plot(f_axis, phase)
            ax3.set_title(f"Phase Spektrum{filter_title} [Grad]")
            ax3.set_xlabel("Frequenz [Hz]")
            ax3.set_ylabel("Phase [Grad]")
            ax3.grid(True)

        fig.set_constrained_layout(False)
