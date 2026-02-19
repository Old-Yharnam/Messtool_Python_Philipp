"""
Daten Verarbeiter - Signalverarbeitung
======================================
Klasse für die Verarbeitung von Messdaten:
FFT-Berechnung, Zeitbereichsanalyse, Signal-Export
und Berechnung von Kennwerten (RMS, AVG, etc.).
"""

import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
from gui_module.plot_manager import PlotManager
from Messtool_Python_V15.setup import Cfg
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataProcessor:
    """Klasse für Datenverarbeitung mit samplerate_fs und value Parametern"""

    @staticmethod
    def compute_fft(y, dt_val):
        """
        Universelle FFT-Berechnung.
        Args:
            y: Signal-Array
            dt_val: Zeitschritt (1/Samplerate)
        Returns:
            f_axis: Frequenzachse in Hz
            amplitude: Amplitudenspektrum
            phase: Phasenspektrum in Grad
        """
        y = np.asarray(y)
        N = len(y)
        if N < 2:
            return np.array([]), np.array([]), np.array([])
        f = np.fft.fftfreq(N, dt_val)[:N // 2]
        fft_res = np.fft.fft(y) / N
        amp = np.abs(fft_res[:N // 2]) * 2
        phase = np.angle(fft_res[:N // 2], deg=True)
        return f, amp, phase

    @staticmethod
    def process_data(samplerate_fs, hann_fenster, value, headers, units, entry6, entry7, entry8, entry9, entry10, entry11, status_label, save_spectrum=True, save_plots=True):
        dt = 1/samplerate_fs
        nS = value.shape[0]
        logger.info("Extrahierte Samples: %d", nS)
        logger.debug("Value Shape: %s", value.shape)                  
        df = 1/(nS*dt)

        t = np.arange(0, nS) * dt
        lbd = np.arange(0, nS//2)
        f = lbd * df

        start_time = t[0]
        end_time = t[-1]

        entry7.config(state="normal")
        entry8.config(state="normal")
        entry9.config(state="normal")
        entry10.config(state="normal")
        entry11.config(state="normal")

        # Ausgabefelder mit beschreibenden Labels
        entry7.delete(0, tk.END)
        entry7.insert(0, f"Startzeit: {start_time:.6f}")
        entry7.configure(style="EntryNormal.TEntry")
        entry7._is_placeholder = False
        entry8.delete(0, tk.END)
        entry8.insert(0, f"Endzeit: {end_time:.6f}")
        entry8.configure(style="EntryNormal.TEntry")
        entry8._is_placeholder = False
        entry9.delete(0, tk.END)
        entry9.insert(0, f"Samples: {nS}")
        entry9.configure(style="EntryNormal.TEntry")
        entry9._is_placeholder = False
        entry10.delete(0, tk.END)
        entry10.insert(0, f"dt: {dt:.6f}")
        entry10.configure(style="EntryNormal.TEntry")
        entry10._is_placeholder = False
        entry11.delete(0, tk.END)
        entry11.insert(0, f"df: {df:.6f}")
        entry11.configure(style="EntryNormal.TEntry")
        entry11._is_placeholder = False

        entry7.config(state="readonly")
        entry8.config(state="readonly")
        entry9.config(state="readonly")
        entry10.config(state="readonly")
        entry11.config(state="readonly")

        logger.debug("Number of Samples: %s", nS)
        logger.debug("Frequency Step: %s", df)
        logger.debug("Time step is: %s", dt)

        logger.info("Berechne Frequenzachse: nS = %d, df = %s", nS, df)
        logger.debug("Frequenzachse: %s", f)

        if entry6.get() == "Hanning":
            save_window = np.hanning(nS)
            save_CF = 2
        else: 
            save_window = np.ones(nS)
            save_CF = 1

        numeric_columns = [i for i in range(value.shape[1]) if np.issubdtype(value[:, i].dtype, np.number)]

        overview_signals = [value[:, i] for i in numeric_columns]
        overview_signals = [np.asarray(signal) for signal in overview_signals]

        signals = [value[:, i] for i in numeric_columns]
        signals = [np.asarray(signal) for signal in signals]

        save_signals = [save_window * value[:, i] * save_CF for i in numeric_columns]
        save_signals = [np.asarray(signal) for signal in save_signals]

        for i, signal in enumerate(signals):
            logger.debug("Signal %d: shape=%s, dtype=%s, type=%s", i, signal.shape, signal.dtype, type(signal))
            logger.debug("Signal %d data: %s", i, signal)
            logger.debug("Signal %d ist %s", i, "numerisch" if np.issubdtype(signal.dtype, np.number) else " nicht numerisch")
            logger.debug("Signal %d NaNs: %s", i, np.isnan(signal).sum())

        i2 = signals[2] - signals[3] if len(signals) > 3 else np.zeros(nS)

        exclude_columns = ['SECTION', 'LOGDATA', 'Nb', 'Type', 'Date', 'Time']
        filtered_headers = [header for header in headers if header not in exclude_columns]

        def _local_fft_display(signal):
            """Berechnet FFT mit Normalisierung auf Signallänge"""
            fft_result = np.fft.fft(signal / nS)
            fft_result = 2 * fft_result[:nS // 2]
            fft_result[0] = 0.5 * fft_result[0]
            return fft_result

        def _local_fft_save(signal):
            """Berechnet FFT für PNG-Speicherung mit gewählter Fensterfunktion"""
            fft_result = np.fft.fft(signal / nS)
            fft_result = 2 * fft_result[:nS // 2]
            fft_result[0] = 0.5 * fft_result[0]
            return fft_result

        fft_results = [_local_fft_display(signal) for signal in signals]
        save_fft_results = [_local_fft_save(signal) for signal in save_signals]

        i2 = signals[2] - signals[3] if len(signals) > 3 else np.zeros(nS)
        save_i2 = save_signals[2] - save_signals[3] if len(save_signals) > 3 else np.zeros(nS)

        if len(signals) > 3:
            fft_results.append(_local_fft_display(i2))
            save_fft_results.append(_local_fft_save(save_i2))

        logger.info("Anzahl der headers: %s", len(headers))
        logger.info("Anzahl der fft_results: %s",  len(fft_results))

        spectrum_data = {"Frequenz": f}
        logger.info("Frequenzachse Länge: %s", len(f))
        logger.info("Anzahl FFT Results: %s", len(fft_results))

        for i, header in enumerate(headers):
            if i < len(save_fft_results):
                fft_length = len(save_fft_results[i])
                freq_length = len(f)
                logger.debug("Header %s: FFT-Länge=%d, Frequenz-Länge=%d", header, fft_length, freq_length)

                if fft_length == freq_length:
                    spectrum_data[f"{header}_komplex"] = save_fft_results[i]
                    spectrum_data[f"{header}_betrag"] = np.abs(save_fft_results[i])
                    spectrum_data[f"{header}_phase"] = np.angle(save_fft_results[i], deg=True)
                else:
                    logger.warning("Warnung: Längenmismatch für %s - überspringe", header)
            else:
                logger.warning("Warnung: Kein save_fft_result für header %s", header)

        if len(save_signals) > 3 and len(save_fft_results) > len(headers):
            diff_fft = save_fft_results[-1]
            if len(diff_fft) == len(f):
                spectrum_data["I2_komplex"] = diff_fft
                spectrum_data["I2_betrag"] = np.abs(diff_fft)
                spectrum_data["I2_phase"] = np.angle(diff_fft, deg=True)

        data_lengths = {key: len(value) for key, value in spectrum_data.items()}
        logger.debug("Finale Daten-Längen: %s", data_lengths)

        unique_lengths = set(data_lengths.values())
        if len(unique_lengths) == 1:
            spectrum_df = pd.DataFrame(spectrum_data)
            logger.info("DataFrame erfolgreich erstellt")
        else:
            logger.info("Fehler: Inkonsistente Array-Längen: %s", unique_lengths)
            return signals, headers, units, t, dt

        if save_spectrum or save_plots:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile="Spektrum_Auswertung.xlsx")

            if save_path:
                try:
                    if save_spectrum:
                        spectrum_df.to_excel(save_path, sheet_name="Tabelle1", index=False)
                        logger.info("Spektrum gespeichert in: %s", save_path)

                except Exception as e:
                    logger.exception("Fehler beim Speichern")
                    return signals, headers, units, t, dt, None

                if save_plots:
                    plot_dir = os.path.join(os.path.dirname(save_path), "plots")
                    if not os.path.exists(plot_dir):
                        os.makedirs(plot_dir)

                    for i, (save_signal, header) in enumerate(zip(save_signals, headers)):
                        if i < len(save_fft_results):
                            PlotManager.save_time_domain_plot(t, save_signal, header, units[i], str(pd.Timestamp.now()), i*2+1, plot_dir)
                            fft_abs = np.abs(save_fft_results[i])
                            fft_phase = np.angle(save_fft_results[i])
                            PlotManager.save_frequency_domain_plot(f, fft_abs, fft_phase,
                                                    header, units[i], i*2+2, plot_dir)

                    PlotManager.save_overview_plot(t, save_signals, headers, units,
                                     str(pd.Timestamp.now()),
                                     plot_dir)

                logger.info("Spektrum und Plots gespeichert")
                status_label.config(text="Spektrum und Plots gespeichert")
                return signals, headers, units, t, dt, save_path

            else:
                logger.info("Speichern abgebrochen")
                status_label.config(text="Speichern abgebrochen")
                return signals, headers, units, t, dt, None
        else:
            status_label.config(text="Datenverarbeitung abgeschlossen (ohne Speichern)")
            return signals, headers, units, t, dt, None

    @staticmethod
    def export_signals_to_excel(save_path, selected_headers, signals, units, t, dt,
                                header_to_signal_idx, add_avg, add_rms, add_diff,
                                add_int, use_filtered, filter_manager, window_type=Cfg.Defaults.FENSTERTYP):
        """
        Exportiert alle ausgewählten Signale in EIN Excel-Workbook.
        - Pro Signal ein Sheet
        - AVG/RMS (falls angehakt) -> Info-Block
        - Differential/Integral (falls angehakt) -> zusätzliche Zeitreihen-Spalten
        """

        def safe_sheet(name: str) -> str:
            invalid = ['\\', '/', '*', '?', ':', '[', ']']
            for ch in invalid: name = name.replace(ch, '_')
            return name[:31] if len(name) > 31 else name

        def pad(a, L):
            a = np.asarray(a)
            if len(a) == L: return a
            out = np.empty(L, dtype=float); out[:] = np.nan
            out[:min(len(a), L)] = a[:min(len(a), L)]
            return out

        summary_rows = [["Signal", "Unit", "AVG", "RMS"]]

        engines = ["openpyxl", "xlsxwriter"]
        written = False
        last_err = None

        try:
            for eng in engines:
                try:
                    with pd.ExcelWriter(save_path, engine=eng) as writer:

                        for hdr in selected_headers:
                            sig_idx = header_to_signal_idx.get(hdr, None)
                            if sig_idx is None or sig_idx >= len(signals):
                                continue

                            unit = units[sig_idx] if sig_idx < len(units) else ""
                            t_arr = np.asarray(t)
                            original = np.asarray(signals[sig_idx])
                            N = len(original)
                            if N < 2: 
                                continue

                            if use_filtered and filter_manager is not None:
                                try:
                                    used = np.asarray(filter_manager.apply_filter(original))
                                    filter_type = filter_manager.filter_type
                                    characteristic = filter_manager.characteristic
                                    order = filter_manager.order
                                    cutoff1 = filter_manager.cutoff_frequency
                                    cutoff2 = filter_manager.cutoff_frequency2
                                    sample_rate = filter_manager.sample_rate
                                except Exception as e:
                                    logger.exception("Filterfehler (%s):%s",hdr, e)
                                    used = original.copy()
                                    filter_type = Cfg.Defaults.FILTER_TYP
                                    characteristic = filter_manager.characteristic if filter_manager else Cfg.Defaults.FILTER_CHARAKTERISTIK
                                    order = filter_manager.order if filter_manager else None
                                    cutoff1 = getattr(filter_manager, "cutoff_frequency", None)
                                    cutoff2 = getattr(filter_manager, "cutoff_frequency2", None)
                                    sample_rate = getattr(filter_manager, "sample_rate", None)
                            else:
                                used = original.copy()
                                filter_type = Cfg.Defaults.FILTER_TYP
                                characteristic = filter_manager.characteristic if filter_manager else Cfg.Defaults.FILTER_CHARAKTERISTIK
                                order = filter_manager.order if filter_manager else None
                                cutoff1 = getattr(filter_manager, "cutoff_frequency", None) if filter_manager else None
                                cutoff2 = getattr(filter_manager, "cutoff_frequency2", None) if filter_manager else None
                                sample_rate = getattr(filter_manager, "sample_rate", None) if filter_manager else None

                            # Kürzen auf gleiche Länge
                            N = min(len(t_arr), len(original), len(used))
                            t_arr = t_arr[:N]; original = original[:N]; used = used[:N]

                            # FFT - jetzt universelle Methode nutzen
                            f_axis, amp, phase = DataProcessor.compute_fft(used, dt)
                            L = N
                            freq_pad  = pad(f_axis, L)
                            amp_pad   = pad(amp, L)
                            phase_pad = pad(phase, L)

                            # Zusatz: AVG/RMS (Info) + Differential/Integral (Spalten)
                            info_extra = []
                            extra_cols = {}

                            if add_avg:
                                try:
                                    avg_val = float(np.nanmean(used))
                                    info_extra.append(["AVG (benutztes Signal)", f"{avg_val:.6g} {unit}"])
                                    summary_avg = avg_val
                                except Exception:
                                    summary_avg = ""
                            else:
                                summary_avg = ""

                            if add_rms:
                                try:
                                    rms_val = float(np.sqrt(np.nanmean(used**2)))
                                    info_extra.append(["RMS (benutztes Signal)", f"{rms_val:.6g} {unit}"])
                                    summary_rms = rms_val
                                except Exception:
                                    summary_rms = ""
                            else:
                                summary_rms = ""

                            if add_diff:
                                try:
                                    diff = np.gradient(used, dt)
                                    unit_diff = f"{unit}/s" if unit else "1/s"
                                    extra_cols[f"d({hdr})/dt [{unit_diff}]"] = pad(diff, L)
                                except Exception as e:
                                    logger.exception("Diff-Fehler (%s) : %s", hdr, e)

                            if add_int:
                                try:
                                    integ = np.cumsum(used) * dt
                                    unit_int = f"{unit}·s" if unit else "unit·s"
                                    extra_cols[f"∫{hdr} dt [{unit_int}]"] = pad(integ, L)
                                except Exception as e:
                                    logger.exception("Integral-Fehler (%s) : %s", hdr, e)

                            # Info-Block
                            df_step = 1.0 / (N * dt)
                            def fmt(x): return "" if x is None else str(x)
                            info_rows = [
                                ["Export Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                                ["Signal Name", hdr],
                                ["Unit", unit],
                                ["Samples (N)", str(N)],
                                ["dt [s]", f"{dt:.6g}"],
                                ["df [Hz]", f"{df_step:.6g}"],
                                ["Window Type", window_type],
                                ["Filter Type", filter_type],
                                ["Filter Characteristic", characteristic],
                                ["Filter Order", fmt(order)],
                                ["Cutoff Frequency 1 [Hz]", fmt(cutoff1)],
                                ["Cutoff Frequency 2 [Hz]", fmt(cutoff2)],
                                ["Sample Rate [Hz]", fmt(sample_rate)],
                                ["Note", "Daten ab Zeile 20: Time, (benutztes Signal), (original), "
                                        "Frequency, Amplitude, Phase"
                                        + (", d()/dt" if add_diff else "")
                                        + (", ∫()dt" if add_int else "")]
                            ]
                            info_rows.extend(info_extra)
                            info_df = pd.DataFrame(info_rows, columns=["Key","Value"])

                            # Datenblock
                            data_dict = {
                                "Time [s]": t_arr,
                                f"{hdr} [{unit}] ({filter_type})": used,
                                f"{hdr} [{unit}] (original)": original,
                                "Frequency [Hz]": freq_pad,
                                "Amplitude": amp_pad,
                                "Phase [deg]": phase_pad
                            }
                            data_dict.update(extra_cols)
                            data_df = pd.DataFrame(data_dict).replace([np.inf, -np.inf], np.nan)

                            # Schreiben (pro Signal eigenes Sheet)
                            sheet = safe_sheet(hdr)
                            info_df.to_excel(writer, sheet_name=sheet, index=False, startrow=0, startcol=0)
                            data_df.to_excel(writer, sheet_name=sheet, index=False, startrow=19, startcol=0)

                            # Summary-Zeile
                            summary_rows.append([hdr, unit,
                                                "" if summary_avg=="" else f"{summary_avg:.6g}",
                                                "" if summary_rms=="" else f"{summary_rms:.6g}"])

                        # Optionales Summary-Sheet
                        try:
                            if len(summary_rows) > 1:
                                pd.DataFrame(summary_rows[1:], columns=summary_rows[0])\
                                .to_excel(writer, sheet_name="Summary", index=False)
                        except Exception:
                            pass

                    written = True
                    break
                except ModuleNotFoundError as e:
                    last_err = e
                except Exception as e:
                    last_err = e

            if written:
                return True, f"Export nach {save_path} erfolgreich."
            else:
                return False, f"Excel-Engines nicht verfügbar ({last_err})."

        except Exception as e:
            return False, f"Export-Fehler: {e}"