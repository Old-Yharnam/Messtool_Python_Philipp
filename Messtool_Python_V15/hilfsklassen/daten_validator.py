"""
Daten Validator - Eingabevalidierung
====================================
Klasse für Validierung der Benutzereingaben:
Zeilen-/Spaltenbereich, Samplerate, DataFrame-Extraktion
und Konvertierung von Spaltennamen.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Klasse für Validierung und Verarbeitung mit DataFrame und Entry-Parametern"""

    def __init__(self):
        self._start_row = None
        self._end_row = None
        self._start_col = None
        self._end_col = None
        self._samplerate_fs = None
        self.df = None
        self.temp_df = None
        self.headers = []
        self.units = []
        self.temp_headers = []
        self.temp_units = []
        self.reset_active = False

    @property
    def start_row(self):
        return self._start_row

    @start_row.setter
    def start_row(self, value):
        if value < 0:
            raise ValueError("Start-Zeile darf nicht negativ sein")
        if self._end_row is not None and value > self._end_row:
            raise ValueError("Start-Zeile muss kleiner als End-Zeile sein")
        self._start_row = value

    @property
    def end_row(self):
        return self._end_row

    @end_row.setter
    def end_row(self, value):
        if value < 0:
            raise ValueError("End-Zeile darf nicht negativ sein")
        if self._start_row is not None and value < self._start_row:
            raise ValueError("End-Zeile muss größer als Start-Zeile sein")
        self._end_row = value

    @property
    def start_col(self):
        return self._start_col

    @start_col.setter
    def start_col(self, value):
        if value < 0:
            raise ValueError("Start-Spalte darf nicht negativ sein")
        if self._end_col is not None and value > self._end_col:
            raise ValueError("Start-Spalte muss kleiner als End-Spalte sein")
        self._start_col = value

    @property
    def end_col(self):
        return self._end_col

    @end_col.setter
    def end_col(self, value):
        if value < 0:
            raise ValueError("End-Spalte darf nicht negativ sein")
        if self._start_col is not None and value < self._start_col:
            raise ValueError("End-Spalte muss größer als Start-Spalte sein")
        self._end_col = value

    @property
    def samplerate_fs(self):
        return self._samplerate_fs

    @samplerate_fs.setter
    def samplerate_fs(self, value):
        if value <= 0:
            raise ValueError("Samplerate muss positiv sein")
        self._samplerate_fs = value

    @property
    def is_valid_range(self):
        """Prüft automatisch, ob alle Bereiche gültig sind"""
        return (self._start_row is not None and 
                self._end_row is not None and 
                self._start_row < self._end_row and
                self._start_col is not None and
                self._end_col is not None and
                self._start_col < self._end_col)

    @property
    def total_samples(self):
        """Berechnet Anzahl zu verarbeitender Samples"""
        if self.is_valid_range:
            return (self._end_row - self._start_row + 1) * (self._end_col - self._start_col + 1)
        return 0

    @property
    def processing_time_estimate(self):
        """Schätzt Verarbeitungszeit basierend auf Datenmenge"""
        samples = self.total_samples
        if samples > 0:
            return f"~{samples // 1000}s geschätzte Verarbeitungszeit"
        return "Keine Schätzung möglich"

    @property
    def dataframe_type(self):
        """Erkennt automatisch den DataFrame-Typ"""
        if self.df is None:
            return "Kein DataFrame"
        elif hasattr(self.df.columns, 'levels') and len(self.df.columns.levels) == 2:
            return "DWS/Excel (MultiIndex)"
        else:
            return "TOP/CSV (Simple Index)"

    @property
    def can_process(self):
        """Prüft, ob Verarbeitung möglich ist"""
        return (self.df is not None and 
                not self.df.empty and 
                self.is_valid_range and 
                self._samplerate_fs is not None)

    @property
    def data_loaded(self):
        """Prüft automatisch, ob Daten verfügbar sind"""
        return (self.df is not None and 
                not self.df.empty and 
                self.headers)

    def excel_column_to_number(self, col):
        if not col:  # Prüfen, ob leer oder None
            raise ValueError("Spaltenname darf nicht leer sein")
        col = col.upper()  # Großbuchstaben
        result = 0
        for k in col:
            result = result * 26 + (ord(k) - ord('A') + 1)
        return result

    def set_entries_from_gui(self, entry1, entry2, entry3, entry4, entry5):
        """Setzt Properties aus GUI-Eingaben"""
        try:
            placeholders = [
                1,
                10000, 
                1,
                100,
                20
            ]

            entries = [entry1, entry2, entry3, entry4, entry5]
            values = []

            # Hier prüfen, ob entry4 Buchstaben enthält
            end_col_text = entry4.get().strip()  # Text aus GUI holen

            if end_col_text:  # Nur wenn nicht leer
                if end_col_text.isalpha():  # Wenn Buchstaben
                    col_number = self.excel_column_to_number(end_col_text)
                    logger.info("Excel-Spalte %s entspricht Nummer %d", end_col_text, col_number)
                    self.end_col = col_number
                else:  # Wenn Zahl
                    self.end_col = int(end_col_text)
                    logger.info("End-Spalte als Zahl gesetzt: %d", self.end_col)
            else:
                raise ValueError("End-Spalte darf nicht leer sein")

            start_col_text = entry3.get().strip()  # Text aus GUI holen

            if start_col_text:  # Nur wenn nicht leer
                if start_col_text.isalpha():  # Wenn Buchstaben
                    col_number = self.excel_column_to_number(start_col_text)
                    logger.info("Excel-Spalte %s entspricht Nummer %d", start_col_text, col_number)
                    self.start_col = col_number
                else:  # Wenn Zahl
                    self.start_col = int(start_col_text)
                    logger.info("Start-Spalte als Zahl gesetzt: %d", self.start_col)
            else:
                raise ValueError("End-Spalte darf nicht leer sein")

            for entry, placeholder in zip(entries, placeholders):
                value = entry.get().strip()
                if not value or value == placeholder:
                    raise ValueError(f"Bitte alle Felder ausfüllen (fehlt: {placeholder})")
                values.append(value)

            self.start_row = int(values[0])
            self.end_row = int(values[1])
            self.samplerate_fs = float(values[4])

            return True
        except ValueError as e:
            logger.exception("Fehler bei Eingabevalidierung: %s", e)
            return False

    def validate_and_process_dws(self, status_label):
        """DWS/Excel Verarbeitung als Instanzmethode"""
        logger.info("=== DWS/Excel Verarbeitung gestartet ===")
        logger.info("DataFrame Type: %s", self.dataframe_type)

        if not self.data_loaded:
            logger.info("DataFrame Status: Ungültig - Kein DataFrame-Objekt")
            status_label.config(text="Keine gültigen Daten geladen")
            return None, None, None, None, None

        if not (hasattr(self.df.columns, 'levels') and len(self.df.columns.levels) == 2):
            logger.info("Fehler: Kein MultiIndex-DataFrame - nicht für DWS/Excel geeignet")
            status_label.config(text="Fehler: Falsches Datenformat für DWS/Excel")
            return None, None, None, None, None

        if not self.can_process:
            status_label.config(text="Validierung fehlgeschlagen - prüfen Sie Ihre Eingaben")
            return None, None, None, None, None

        try:
            df_to_use = self.temp_df if (self.reset_active and self.temp_df is not None) else self.df

            max_rows = df_to_use.index.max()
            if self._end_row > max_rows:
                self.end_row = max_rows
                logger.info("End_Zeile auf maximale Zeilenzahl %d angepasst", max_rows)
            elif self._end_row == max_rows - 1:
                self.end_row = max_rows
                logger.info("End_Zeile korrigiert auf %d für vollständige Datennutzung", max_rows)

            max_columns = len(df_to_use.columns.levels[0])
            if self._end_col >= max_columns:
                self.end_col = max_columns - 1
                logger.info("End_Spalte auf maximale Spaltenanzahl %d angepasst", (max_columns - 1))

        except Exception as e:
            error_msg = f"Fehler bei Bereichsvalidierung: {str(e)}"
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

        try:
            logger.info("Extrahiere DWS-Daten: Zeilen %d-%d Spalten %d-%d", self._start_row, self._end_row, self._start_col, self._end_col)
            logger.info("Geschätzte Verarbeitungszeit: %s", self.processing_time_estimate)

            df_to_use = self.temp_df if (self.reset_active and self.temp_df is not None) else self.df
            selected_columns = df_to_use.columns[self._start_col:self._end_col + 1]
            data_slice = df_to_use.loc[self._start_row:self._end_row][selected_columns]

            data_converted = data_slice.replace({True: 1, False: 0})
            data_converted = data_converted.astype(str).replace(",", ".", regex=True)

            numeric_data = data_converted.apply(pd.to_numeric, errors='coerce')
            value = numeric_data.to_numpy()

            if self.reset_active and self.temp_df is not None:
                headers = [self.temp_headers[i] for i in range(self._start_col, min(self._end_col + 1, len(self.temp_headers)))]
                units = [self.temp_units[i] for i in range(self._start_col, min(self._end_col + 1, len(self.temp_units)))]
            else:
                headers = [col[0] for col in selected_columns]
                units = [col[1] for col in selected_columns]
                if self.temp_units:
                    for i in range(len(units)):
                        if not units[i]:
                            idx = self._start_col + i
                            if idx < len(self.temp_units):
                                units[i] = self.temp_units[idx]

            if len(headers) != len(units) or len(headers) != value.shape[1]:
                raise ValueError("Inkonsistente Dimensionen der extrahierten Daten")

            logger.info("DWS-Daten erfolgreich extrahiert: %s Spalten", len(headers))
            status_label.config(text="DWS-Datei erfolgreich verarbeitet")

            return self._samplerate_fs, 1, value, headers, units

        except (ValueError, IndexError) as e:
            error_msg = f"Fehler bei DWS-Datenextraktion: {str(e)}"
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

    def validate_and_process_top(self, status_label):
        """TOP/CSV Verarbeitung als Instanzmethode"""
        logger.info("=== TOP-CSV Verarbeitung gestartet ===")
        logger.info("DataFrame Type: %s", self.dataframe_type)

        if not self.data_loaded:
            logger.info("DataFrame Status: Ungültig - Kein DataFrame-Objekt")
            status_label.config(text="Keine gültigen Daten geladen")
            return None, None, None, None, None

        if not self.can_process:
            status_label.config(text="Validierung fehlgeschlagen - prüfen Sie Ihre Eingaben")
            return None, None, None, None, None

        try:
            df_to_use = self.temp_df if (self.reset_active and self.temp_df is not None) else self.df

            max_rows = df_to_use.index.max()
            if self._end_row > max_rows:
                self.end_row = max_rows
                logger.info("End_Zeile auf maximale Zeilenzahl %d angepasst", max_rows)
            elif self._end_row == max_rows - 1:
                self.end_row = max_rows
                logger.info("End_Zeile korrigiert auf %d für vollständige TOP-Datennutzung", max_rows)

            max_columns = len(df_to_use.columns)
            if self._end_col >= max_columns:
                self.end_col = max_columns - 1
                logger.info("End_Spalte auf maximale Spaltenanzahl %d angepasst", (max_columns-1))

        except Exception as e:
            error_msg = f"Fehler bei Bereichsvalidierung: {str(e)}"
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

        try:
            logger.info("Extrahiere TOP-Daten: Zeilen %d-%d Spalten %d-%d", self._start_row, self._end_row, self._start_col, self._end_col)
            logger.info("Geschätzte Verarbeitungszeit: %s", self.processing_time_estimate)

            df_to_use = self.temp_df if (self.reset_active and self.temp_df is not None) else self.df
            selected_columns = df_to_use.columns[self._start_col:self._end_col + 1]
            data_slice = df_to_use.loc[self._start_row:self._end_row][selected_columns]

            data_converted = data_slice.replace({True: 1, False: 0})
            data_converted = data_converted.astype(str).replace(",", ".", regex=True)

            numeric_data = data_converted.apply(pd.to_numeric, errors='coerce')
            value = numeric_data.to_numpy()

            headers = [str(col) for col in selected_columns]
            if self.temp_headers and self.temp_units:
                unit_by_header = dict(zip(self.temp_headers, self.temp_units))
                units = [unit_by_header.get(str(col), "") for col in selected_columns]
            else:
                units = [''] * len(selected_columns)

            if len(headers) != len(units) or len(headers) != value.shape[1]:
                raise ValueError("Inkonsistente Dimensionen der extrahierten Daten")

            logger.info("TOP-Daten erfolgreich extrahiert: %d Spalten", len(headers))
            status_label.config(text="TOP-Datei erfolgreich verarbeitet")

            return self._samplerate_fs, 1, value, headers, units

        except (ValueError, IndexError) as e:
            error_msg = f"Fehler bei TOP-Datenextraktion: {str(e)}"
            logger.exception(error_msg)
            status_label.config(text=error_msg)
            return None, None, None, None, None

    def validate_and_process(self, entry1, entry2, entry3, entry4, entry5, status_label):
        """Hauptverarbeitungsmethode als Instanzmethode"""

        logger.info("Standartwerte der Datenverarbeitung gesetzt")
        if not self.set_entries_from_gui(entry1, entry2, entry3, entry4, entry5):
            status_label.config(text="Bitte geben Sie gültige Zahlen ein")
            return None, None, None, None, None

        if self.df is None or not isinstance(self.df, pd.DataFrame):
            if self.temp_df is not None and isinstance(self.temp_df, pd.DataFrame):
                self.df = self.temp_df.copy()
                logger.info("DataFrame aus temp_df wiederhergestellt")
            else:
                logger.info("Fehler: Kein gültiger DataFrame verfügbar")
                return None, None, None, None, None

        if self.dataframe_type == "DWS/Excel (MultiIndex)":
            logger.info("MultiIndex erkannt - verwende DWS/Excel Verarbeitung")
            return self.validate_and_process_dws(status_label)
        else:
            logger.info("Einfacher Index erkannt - verwende TOP Verarbeitung")
            return self.validate_and_process_top(status_label)
