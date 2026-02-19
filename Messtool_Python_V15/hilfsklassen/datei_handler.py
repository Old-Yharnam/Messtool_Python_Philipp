"""
Datei Handler - Dateioperationen
================================
Klasse für alle Datei-Operationen: Lesen von Excel, CSV
und DWS-Dateien, Encoding-Erkennung, Validierung und
Export von verarbeiteten Daten.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import os
import charset_normalizer
from Messtool_Python_V15.setup import Cfg
import logging
import re

logger = logging.getLogger(__name__)

class FileHandler:
    """Klasse für alle Datei-Operationen mit Property-basierter Validierung"""

    def __init__(self):
        self._file_path = None
        self._encoding = None
        self._delimiter = None 
        self._is_valid = False

    @staticmethod
    def split_header_unit(name: str) -> tuple[str, str]:
        m = re.search(r"\[(.*?)]", name)
        if not m:
            return name, ""
        unit = m.group(1).strip()
        if unit.lower().startswith("unit:"):
            unit = unit.split(":", 1)[1].strip()
        header = re.sub(r"\s*\[.*?]\s*", "", name).strip()
        return header, unit

    @property
    def file_path(self):
        return self._file_path

    @file_path.setter
    def file_path(self, path):
        if path is None:
            self._file_path = None
            self._is_valid = False
            return

        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")
        if not path_obj.is_file():
            raise ValueError(f"Pfad ist keine Datei: {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Datei nicht lesbar: {path}")

        self._file_path = path_obj
        self._is_valid = True
        self._encoding = None
        self._delimiter = None

    @property
    def encoding(self):
        if self._encoding is None and self._file_path is not None:
            self._encoding = self._detect_encoding()

        return self._encoding

    @encoding.setter
    def encoding(self, value):
        valid_encodings = ['utf-8', 'windows-1250', 'windows-1252', 'iso-8859-1', 'cp1252']
        logger.debug("Das ist das encoding: %s", value)
        if value is not None and value not in valid_encodings:
            raise ValueError(f"Ungültiges Encoding: {value}. Gültige Werte: {valid_encodings}")
        self._encoding = value

    @property
    def delimiter(self):
        if self._delimiter is None and self._file_path is not None and self.encoding is not None:
            self._delimiter = self._detect_csv_delimiter()
        return self._delimiter

    @delimiter.setter
    def delimiter(self, value):
        valid_delimiters = [';', ',', '\t', '|']
        if value is not None and value not in valid_delimiters:
            raise ValueError(f"Ungültiges Trennzeichen: {value}. Gültige Werte: {valid_delimiters}")
        self._delimiter = value

    @property
    def is_valid(self):
        return self._is_valid and self._file_path is not None and self._file_path.exists()

    @property
    def file_extension(self):
        return self._file_path.suffix.lower() if self._file_path else None

    @property
    def is_excel(self):
        return self.file_extension in ['.xlsx', '.xls'] if self.file_extension else False

    @property
    def is_csv(self):
        return self.file_extension == '.csv' if self.file_extension else False

    def _detect_encoding(self):
        """Private Methode zur Encoding-Erkennung"""
        if not self.is_valid:
            raise ValueError("Kein gültiger Dateipfad gesetzt")

        with open(self._file_path, 'rb') as f:
            result = charset_normalizer.detect(f.read())
        return result['encoding']

    def _detect_csv_delimiter(self):
        """Private Methode zur Delimiter-Erkennung"""
        if not self.is_valid:
            raise ValueError("Kein gültiger Dateipfad gesetzt")
        if self._encoding is None:
            raise ValueError("Encoding muss zuerst erkannt werden")

        delimiters = [';', ',', '\t', '|']

        try:
            with open(self._file_path, 'r', encoding=self.encoding) as f:
                first_line = f.readline()
            logger.debug("Das ist self.encoding: %s", self.encoding)
        except UnicodeDecodeError:
            logger.exception("Encoding-Fehler mit %s, verwende Fallback", self.encoding)
            return ',' 

        delimiter_counts = {}
        for delimiter in delimiters:
            count = first_line.count(delimiter)
            if count > 0:
                delimiter_counts[delimiter] = count

        if delimiter_counts:
            best_delimiter = max(delimiter_counts, key=delimiter_counts.get)
            logger.info("Erkanntes Trennzeichen: '%s' (Anzahl: %s)", best_delimiter, delimiter_counts[best_delimiter])
            return best_delimiter
        else:
            logger.info("Kein Trennzeichen erkannt, verwende Komma als Standard")
            return ','

    def read_dws_excel(self, sheet_name, status_label, progress_label):
        try:
            if not self.is_valid:
                status_label.config(text="Fehler: Ungültiger Dateipfad")
                return None, None, None

            if not self.is_excel:
                status_label.config(text="Fehler: Keine Excel-Datei")
                return None, None, None

            logger.info("Excel wird mit geladen: %s", self.file_path)

            if not self.file_path.exists():
                status_label.config(text="Fehler: Datei nicht gefunden")
                return None, None, None

            with open(self.file_path, 'rb') as f:
                raw_data = f.read()

            df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=[0, 1], parse_dates=False)

            df.index += 1
            temp_df = df.copy()

            temp_headers = [col[0] for col in df.columns]
            temp_units = [col[1] for col in df.columns]

            parsed = [self.split_header_unit(str(h)) for h in temp_headers]
            temp_headers = [h for h, _ in parsed]
            temp_units = [
                u if u not in (None, "") else parsed[i][1]
                for i, u in enumerate(temp_units)
            ]

            if df.empty:
                logger.warning("Warnung: DataFrame ist leer")
                status_label.config(text="Fehler: Excel-Datei ist leer")
                return None, None, None

        except Exception as e:
            logger.exception("Fehler beim Einlesen der Excel-Datei: %s", e)
            status_label.config(text="Fehler beim Einlesen der Datei")
            return None, None, None

        time_column = ("Time", "s")

        if time_column not in df.columns:
            logger.debug("Verfügbare Spalten: %s", df.columns.tolist())
            status_label.config(text="Fehler: Zeitstempel-Spalte nicht gefunden")
            return None, None, None

        logger.debug("Erste Zeitstempel-Werte:")
        logger.debug(df[time_column].head())

        try:
            df[time_column] = pd.to_datetime(
                df[time_column].astype(str),
                format="%d.%m.%Y %H:%M:%S.%f",
                dayfirst=True,
                errors="coerce"
            )

            if df[time_column].empty:
                status_label.config(text="Fehler: Keine Zeitstempel vorhanden")
                return None, None, None

            invalid_timestamps = df[time_column].isna().sum()
            if invalid_timestamps > 0:
                logger.warning("Warnung: %s Zeitstempel konnten nicht konvertiert werden", invalid_timestamps)
                status_label.config(text="Fehler: Ungültige Zeitstempel gefunden")
                return None, None, None

        except Exception as e:
            logger.exception("Fehler bei Zeitstempel-Konvertierung: %s", e)
            logger.error("Problematischer Wert: %s", df[time_column].iloc[0])
            status_label.config(text="Fehler: Ungültiges Zeitformat")
            return None, None, None

        logger.info("Excel-Datei erfolgreich geladen. Shape: %s", df.shape)
        logger.info("Zeitstempel-Spalte: %s", time_column)
        logger.debug("Hauptüberschriften (Level 0): %s", df.columns.levels[0].tolist())
        logger.debug("Einheiten (Level 1): %s", df.columns.levels[1].tolist())
        logger.debug("Erste Zeilen der Daten:\n%s", df.head())

        end_row = df.shape[0]
        columns = df.columns.levels[0].tolist()

        start_row = 1
        if columns:
            start_col = 0
            end_col = len(columns) - 1
            logger.info("DWS Standard-Bereich: Zeilen %d-%d, Spalten %d-%d", start_row, end_row, start_col, end_col)
        else:
            status_label.config(text="Fehler: keine gültigen Daten vorhanden")
            return None, None, None

        status_label.config(text="Datei erfolgreich geladen - Eingaben vornehmen")

        return df, temp_headers, temp_units

    def read_top(self, status_label, progress_label):
        try:
            if not self.is_valid:
                status_label.config(text="Fehler: Ungültiger Dateipfad")
                return None, None, None

            if not self.is_csv:
                status_label.config(text="Fehler: Keine CSV-Datei")
                return None, None, None

            logger.info("TOP CSV-Datei geladen: %s", self.file_path)

            if not self.file_path.exists():
                status_label.config(text="Fehler: Datei nicht gefunden")
                return None, None, None

            logger.info("Verwende Encoding: %s", self.encoding)
            logger.info("Verwende Delimiter: %s", self.delimiter)

            with open(self.file_path, 'r', encoding=self.encoding) as f:
                lines = f.readlines()
                logger.info("CSV-Datei mit open() geladen: %d Zeilen", len(lines))

            unit_map = {}
            delimiter = self.delimiter or ";"
            for line in lines:
                line_stripped = line.lstrip()
                if not line_stripped.startswith("LOGITEM"):
                    continue
                parts = [p.strip() for p in line_stripped.split(delimiter)]
                if len(parts) < 2:
                    continue
                signal_name = parts[1]
                text = " ".join(parts[2:])
                m = re.search(r"\[unit\s*:\s*([^\]]+)\]", text, flags=re.IGNORECASE)
                if m:
                    unit_map[signal_name] = m.group(1).strip()

            data_start_line = None

            for i, line in enumerate(lines):
                if "Nb" in line.split(delimiter):
                    data_start_line = i
                    logger.info("Nb gefunden in Zeile %d, Daten starten ab Zeile %d", i, data_start_line)
                    break 

            if data_start_line is None:
                logger.info("Keine Nb-Markierung gefunden, versuche Standard-Ansatz")
                data_start_line = 0

            df = pd.read_csv(self.file_path, skiprows=data_start_line, header=0,parse_dates=False, encoding=self.encoding, sep=self.delimiter)
            df = df.dropna(how='all', axis=1)
            df = df.dropna(how='all', axis=0)
            df.index = range(1, len(df) + 1)

            temp_df = df.copy()
            parsed = [self.split_header_unit(str(col)) for col in df.columns]
            temp_headers = [h for h, _ in parsed]
            temp_units = []
            for header, unit in parsed:
                unit_from_map = unit_map.get(header)
                temp_units.append(unit_from_map if unit_from_map else unit)

            if df.empty:
                logger.warning("Warnung: DataFrame ist leer")
                status_label.config(text="Fehler: CSV-Datei ist leer")
                return None, None, None

            logger.info("DataFrame Shape nach Bereinigung: %s", df.shape)
            logger.debug("Verfügbare Spalten: %s", df.columns.tolist())

        except Exception as e:
            logger.exception(f"Fehler beim Einlesen der TOP CSV-Datei: {e}")
            status_label.config(text="Fehler beim Einlesen der Datei")
            return None, None, None

        time_columns = []
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['time', 'zeit', 'timestamp', 'datetime', 'date']):
                time_columns.append(col)

        if len(df.columns) == 0:
            status_label.config(text="Fehler: Keine Spalten gefunden")
            return None, None, None
        elif time_columns:
            time_column = time_columns[0]
            logger.info("Zeitspalte automatisch erkannt: %s", time_column)
        else:
            time_column = df.columns[0]
            logger.info("Keine Zeitspalte gefunden - verwende erste Spalte als Fallback: %s", time_column)

        logger.debug("Erste Zeitstempel-Werte:")
        logger.debug(df[time_column].head())
        logger.info("Zeitspalte '%s' wird als Index-Referenz beibehalten", time_column)
        logger.debug("Zeitwerte (unkonvertiert): %s", df[time_column].head(3).tolist())
        logger.info("Fokus liegt auf numerischen Messdaten - Zeitkonvertierung übersprungen")

        progress_label.config(text="")

        logger.info("TOP CSV-Datei erfolgreich geladen. Shape: %s", df.shape)
        logger.info("Referenz-Zeitspalte: %s", time_column)
        logger.info("\nAnzahl verfügbare Spalten: %d", len(df.columns))
        logger.info("Spalten (erste 10): %s", df.columns.tolist()[:10])

        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        logger.info("Numerische Spalten: %d (erste 8: %s)", len(numeric_columns), numeric_columns[:8])
        logger.debug("Erste Datenzeilen (nur numerische Spalten):")

        if numeric_columns:
            logger.debug("%s", df[numeric_columns[:6]].head(3))
        else:
            logger.info("Keine numerischen Spalten erkannt")

        end_row = len(df)
        columns = df.columns.tolist()

        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        exclude_columns = ['SECTION', 'LOGDATA', 'Nb', 'Type', 'Date', 'Time']
        numeric_columns = [col for col in numeric_columns if col not in exclude_columns]

        filtered_pairs = [(h, u) for h, u in zip(temp_headers, temp_units) if h not in exclude_columns]
        temp_headers = [h for h, _ in filtered_pairs]
        temp_units = [u for _, u in filtered_pairs]

        start_row = 2

        if numeric_columns:
            logger.info("Setze Standard-Bereich auf numerische Spalten: %d verfügbar", len(numeric_columns))
            first_numeric_idx = df.columns.get_loc(numeric_columns[0])
            last_numeric_idx = df.columns.get_loc(numeric_columns[-1])
            start_col = first_numeric_idx
            end_col = min(last_numeric_idx, first_numeric_idx + 10)
            logger.info("Standard-Spaltenbereich: %d bis %d (numerische Daten)", start_col, end_col)
        elif columns:
            start_col = 0
            end_col = min(len(columns) - 1, 10)
            logger.info("Fallback-Spaltenbereich: %d bis %d", start_col, end_col)
        else:
            status_label.config(text="Fehler: keine gültigen Daten vorhanden")
            return None, None, None
        status_label.config(text="Datei erfolgreich geladen - Bitte Eingaben vornehmen")

        return df, temp_headers, temp_units

def export_signal_data(self, save_path,
                       t,
                       original,
                       used,
                       signal_name,
                       unit,
                       dt,
                       f_axis,
                       amp,
                       phase,
                       filter_info,
                       window_type,
                       show_avg=False,
                       show_rms=False,
                       show_diff=False,
                       show_integral=False):
    """
    Exportiert Signal-Daten nach Excel oder CSV.

    Args:
        save_path: Zieldateipfad (.xlsx)
        t: Zeitarray
        original: Original-Signal
        used: Benutztes Signal (gefiltert oder original)
        signal_name: Name des Signals
        unit: Einheit
        dt: Abtastzeit
        f_axis: Frequenzachse (FFT)
        amp: Amplitude (FFT)
        phase: Phase (FFT)
        filter_info: Dict mit filter_type, characteristic, order, cutoff1, cutoff2, sample_rate
        window_type: Fensterfunktion
        show_avg, show_rms, show_diff, show_integral: Flags für optionale Berechnungen

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        N = len(t)
        if N < 2:
            return False, "Zu wenige Punkte für Export."

        # Hilfsfunktion: Array auf N Zeilen auffüllen
        def pad_to_N(a, L):
            a = np.asarray(a)
            if len(a) == L:
                return a
            out = np.empty(L, dtype=float)
            out[:] = np.nan
            out[:min(len(a), L)] = a[:min(len(a), L)]
            return out

        freq_pad = pad_to_N(f_axis, N)
        amp_pad = pad_to_N(amp, N)
        phase_pad = pad_to_N(phase, N)

        # Optionale Kennwerte/Serien
        info_rows_extra = []
        extra_series = {}

        if show_avg:
            avg_val = float(np.nanmean(used))
            info_rows_extra.append(["AVG (auf aktuell benutztem Signal)", f"{avg_val:.6g} {unit}"])

        if show_rms:
            rms_val = float(np.sqrt(np.nanmean(used**2)))
            info_rows_extra.append(["RMS (auf aktuell benutztem Signal)", f"{rms_val:.6g} {unit}"])

        if show_diff:
            diff = np.gradient(used, dt)
            unit_diff = f"{unit}/s" if unit else "1/s"
            extra_series[f"d({signal_name})/dt [{unit_diff}]"] = pad_to_N(diff, N)

        if show_integral:
            integ = np.cumsum(used) * dt
            unit_int = f"{unit}·s" if unit else "unit·s"
            extra_series[f"∫{signal_name} dt [{unit_int}]"] = pad_to_N(integ, N)

        # Metadaten-Block
        df_step = 1.0 / (N * dt)
        fmt = lambda x: "" if x is None else str(x)
        filter_type = filter_info.get('filter_type', 'Kein Filter')

        info_rows = [
            ["Export Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["Signal Name", signal_name],
            ["Unit", unit],
            ["Samples (N)", str(N)],
            ["dt [s]", f"{dt:.6g}"],
            ["df [Hz]", f"{df_step:.6g}"],
            ["Window Type", window_type or Cfg.Defaults.FENSTERTYP],
            ["Filter Type", filter_type],
            ["Filter Characteristic", filter_info.get('characteristic', '')],
            ["Filter Order", fmt(filter_info.get('order'))],
            ["Cutoff Frequency 1 [Hz]", fmt(filter_info.get('cutoff1'))],
            ["Cutoff Frequency 2 [Hz]", fmt(filter_info.get('cutoff2'))],
            ["Sample Rate [Hz]", fmt(filter_info.get('sample_rate'))],
            ["Note", "Daten ab Zeile 20: Time, (filtered), (original), Frequency, Amplitude, Phase"
                    + (", d()/dt" if show_diff else "")
                    + (", ∫()dt" if show_integral else "")]
        ]
        info_rows.extend(info_rows_extra)

        info_df = pd.DataFrame(info_rows, columns=["Key", "Value"])

        # Daten-Block
        data_dict = {
            "Time [s]": t,
            f"{signal_name} [{unit}] ({filter_type})": used,
            f"{signal_name} [{unit}] (original)": original,
            "Frequency [Hz]": freq_pad,
            "Amplitude": amp_pad,
            "Phase [deg]": phase_pad
        }
        for col_name, series in extra_series.items():
            data_dict[col_name] = series

        data_df = pd.DataFrame(data_dict).replace([np.inf, -np.inf], np.nan)

        # Excel schreiben
        engines = ["openpyxl", "xlsxwriter"]
        written = False
        last_err = None

        for eng in engines:
            try:
                with pd.ExcelWriter(save_path, engine=eng) as writer:
                    info_df.to_excel(writer, sheet_name="Signal", index=False, startrow=0, startcol=0)
                    data_df.to_excel(writer, sheet_name="Signal", index=False, startrow=19, startcol=0)
                written = True
                break
            except ModuleNotFoundError as e:
                last_err = e
            except Exception as e:
                last_err = e

        # Fallback: CSV
        if not written:
            base = os.path.splitext(save_path)[0]
            csv_path = base + "_Signal.csv"
            try:
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["Key", "Value"])
                    w.writerows(info_rows)
                    w.writerow([])
                    w.writerow([])
                    w.writerow(list(data_df.columns))
                    for _, row in data_df.iterrows():
                        w.writerow(list(row.values))
                return True, f"Excel-Engines nicht verfügbar ({last_err}). CSV erstellt: {csv_path}"
            except Exception as e:
                return False, f"Fehler beim Export: {e}"

        return True, f"Export abgeschlossen: {save_path}"

    except Exception as e:
        return False, f"Fehler beim Export: {e}"