"""
Setup - Zentrale Konfiguration
===============================
Alle Placeholders, Default-Werte, Farben, Schriftarten,
Texte und Layout-Konstanten an einer Stelle.

Verwendung:
    from setup import Cfg
    font = (Cfg.Fonts.FAMILY, Cfg.Fonts.SMALL)
    color = Cfg.Colors.WINE
"""


class Fonts:
    FAMILY = "Segoe UI"
    SMALL = 10
    MEDIUM = 11
    LARGE = 12
    TABS = 13
    STATUS = 15
    HEADER = 16


class Colors:
    WINE = "#a0616c"
    PRIMARY = "#0d6efd"
    SUCCESS = "#198754"
    WARNING = "#fd7e14"
    SECONDARY = "#6c757d"
    DANGER = "#dc3545"
    SIGNAL_ORIGINAL = "#2c7fb8"

    CARD_MAP = {
        "danger": DANGER,
        "primary": PRIMARY,
        "success": SUCCESS,
        "warning": WARNING,
        "secondary": SECONDARY,
        "wine": WINE,
    }

    SIDEBAR_HEADER_BG = "#3a3a3a"
    SIDEBAR_INNER_BG = "#2b2b2b"
    SIDEBAR_TEXT_BG = "#4a4a4a"

    TAB_INPUT = PRIMARY
    TAB_OUTPUT = SUCCESS
    TAB_INACTIVE = "#e9ecef"
    TAB_TEXT_ACTIVE = "white"
    TAB_TEXT_INACTIVE = "#333333"

    GROUP_SELECTED_BG = "#d9edf7"
    GROUP_LABEL = "blue"

    UNIT_PALETTE = [
        "#e6f3ff", "#e6ffe6", "#fff3e6", "#ffe6e6", "#f3e6ff",
        "#e6ffff", "#fff9e6", "#ffe6f3", "#e6ffe9", "#f0e6ff",
    ]


class Placeholders:
    START_REIHE = "Start Reihe z.B. 1"
    END_REIHE = "End Reihe z.B. 10000"
    START_SPALTE = "Start Spalte z.B. 1 / A"
    END_SPALTE = "End Spalte z.B. 100 / CC"
    SAMPLERATE = "Samplefrequenz z.B. 20"
    FENSTERTYP = "Fenstertyp wählen:"

    EINGABE = [START_REIHE, END_REIHE, START_SPALTE, END_SPALTE, SAMPLERATE]

    STARTZEIT = "Startzeit"
    ENDZEIT = "Endzeit"
    SAMPLES = "Samples (n)"
    DT = "Zeitabstände (dt)"
    DF = "Frequenzabstände (df)"

    AUSGABE = [STARTZEIT, ENDZEIT, SAMPLES, DT, DF]


class Defaults:
    START_REIHE = 1
    END_REIHE = 10000
    START_SPALTE = 1
    END_SPALTE = 100
    SAMPLERATE = 20
    FENSTERTYP = "Rechteck"
    START_ROW_PREFILL = 2

    VALUES_CONFIG = [
        (1, "Start Reihe --> 1"),
        (10000, "End Reihe --> 10000"),
        (1, "Start Spalte --> 1"),
        (100, "End Spalte --> 100"),
        (20, "Samplefrequenz FS --> 20"),
        ("Rechteck", "Fenster --> Rechteck"),
    ]

    GRENZFREQUENZ_1 = 2
    GRENZFREQUENZ_2 = 6
    FILTER_CHARAKTERISTIK = "butterworth"
    FILTER_ORDNUNG = "1.Ordnung"
    FILTER_TYP = "Kein Filter"

    FILTER_TYPEN = ["Kein Filter", "Tiefpass", "Hochpass", "Bandpass"]
    FILTER_CHARAKTERISTIKEN = ["butterworth", "bessel", "Chebyshev I", "Elliptic"]
    FILTER_ORDNUNGEN = ["1.Ordnung", "2.Ordnung", "3.Ordnung", "4.Ordnung"]

    FENSTER_TYPEN = ["Fenstertyp wählen:", "Rechteck", "Hanning"]

    MAX_GROUPS = 3
    MAX_SIGNALS = 3


class Texts:
    # AnalyseManager spezifisch
    HINT = "Hinweis"
    ERROR = "Fehler"
    NO_DATA = "Keine verarbeiteten Daten vorhanden."
    SELECT_SIGNAL = "Signal auswählen:"
    SELECT_SIGNAL_FIRST = "Bitte zuerst ein Signal in der Liste auswählen."
    SIGNAL_NOT_FOUND = "Signal '{0}' wurde nicht gefunden."
    NO_DT = "Keine gültige Abtastzeit (dt) vorhanden."
    PLOT_ERROR = "Fehler bei der Darstellung:\n{0}"
    DIFFERENTIAL_ANALYSE_TITLE = "Differential Analyse"
    AVG_ANALYSE_TITLE = "AVG Analyse"
    AVG_ANALYSE_MULTI_TITLE = "AVG Analyse (Multi)"
    RMS_ANALYSE_TITLE = "RMS Analyse"
    RMS_ANALYSE_MULTI_TITLE = "RMS Analyse (Multi)"
    FFT_ANALYSE_TITLE = "FFT Analyse"
    FFT_ANALYSE_MULTI_TITLE = "FFT Analyse (Multi)"
    INTEGRAL_ANALYSE_TITLE = "Integral Analyse"
    INTEGRAL_ANALYSE_MULTI_TITLE = "Integral Analyse (Multi)"
    VARIANZ_ANALYSE_TITLE = "Varianz/Autokorrelation Analyse"
    VARIANZ_ANALYSE_MULTI_TITLE = "Varianz/Autokorrelation Analyse (Multi)"
    ZEITBEREICH_DIALOG_TITLE = "{0} - Zeitbereich auswählen"
    WINDOW_TITLE = "Messdatenverarbeitung"
    DASHBOARD = "Dashboard"

    BTN_IMPORT = "Messdaten importieren"
    BTN_VERARBEITUNG = "Datenverarbeitung starten"
    BTN_SIGNALE = "Signale anzeigen"
    BTN_HILFE = "\U0001F4D6 Bedienungsanleitung"
    BTN_HERKUNFTSPFAD = "\U0001F4E5 Herkunftspfad"
    BTN_SPEICHERPFAD = "\U0001F4E4 Speicherpfad"
    BTN_RESET_KOMPLETT = "\U0001F5D1 Komplett"
    BTN_RESET_EINGABE = "\U0001F9F9 nur Eingabe"
    BTN_GRUPPE_ERSTELLEN = "Gruppe erstellen"
    BTN_GRUPPE_LOESCHEN = "Gruppe löschen"
    BTN_FILTER = "Filtereinstellungen"

    LBL_PFAD = "\U0001F4C1 Pfad"
    LBL_RESET = "\u21BA Zurücksetzen"

    STATUS_BEREIT = "Bereit"
    STATUS_LADEN = "Daten werden geladen..."
    STATUS_VERARBEITUNG = "Verarbeitung läuft..."
    STATUS_NEUE_DATEI = "Bitte neue Datei importieren"
    STATUS_NEUE_EINGABEN = "Bitte neue Eingaben vornehmen"
    STATUS_KEIN_SIGNAL = "Keine Signale ausgewählt"

    TAB_EINGABE = "📥 Eingabedaten"
    TAB_AUSGABE = "📤 Ausgabedaten"

    RB_PLOTS = "\U0001F4CA Plots speichern"
    RB_SPEKTRUM = "\u3030 Spektrum speichern"
    RB_NICHTS = "\u274C Nichts speichern"

    CARD_IMPORT_TITLE = "Datenimport"
    CARD_IMPORT_ICON = "\U0001F4C2"
    CARD_VERARBEITUNG_TITLE = "Verarbeitung"
    CARD_VERARBEITUNG_ICON = "\u2699"
    CARD_SIGNAL_TITLE = "Signalverarbeitung"
    CARD_SIGNAL_ICON = "\u223F"
    CARD_ALLGEMEIN_TITLE = "Allgemeines"
    CARD_ALLGEMEIN_ICON = "\u2139"

    CB_CSV_DEFAULT = "CSV auswählen"

    PATH_HERKUNFT_ID = "Datei Herkunftspfad"
    PATH_SPEKTRUM_ID = "Spektrum Speicherpfad"
    RESET_KOMPLETT_ID = "Komplett zurücksetzen"


class Layout:
    ANALYSIS_FIG_SIZE = (14, 8)
    SIDEBAR_WIDTH = 520
    PAD_X_MEDIUM = 10
    PAD_Y_MEDIUM = 8
    PAD_X_CARD = 6
    PAD_Y_CARD = 4
    LOGO_WIDTH = 400
    LOGO_ASPECT = 80 / 500


class Data:
    EXCLUDE_COLUMNS = ['SECTION', 'LOGDATA', 'Nb', 'Type', 'Date', 'Time']


class Cfg:
    Fonts = Fonts
    Colors = Colors
    Ph = Placeholders
    Defaults = Defaults
    Texts = Texts
    Layout = Layout
    Data = Data