"""
Filter Manager - Signalfilterung
================================
Klasse für digitale Signalfilter: Tiefpass, Hochpass,
Bandpass mit verschiedenen Charakteristiken (Butterworth,
Chebyshev, Bessel) und konfigurierbarer Ordnung.
"""

import numpy as np
from scipy import signal
import logging
from Messtool_Python_V15.setup import Cfg

logger = logging.getLogger(__name__)

class FilterManager:
    """Klasse für verschiedene Signalfilter mit Parameter-Container"""

    def __init__(self):
        self.filter_type = Cfg.Defaults.FILTER_TYP
        self.cutoff_frequency = None
        self.cutoff_frequency2 = None
        self.order = None
        self.sample_rate = None
        self.characteristic = Cfg.Defaults.FILTER_CHARAKTERISTIK
        self.b_coeffs = None
        self.a_coeffs = None
        self.sos_coeffs = None
        self._warned_nan_inf = False
        self._warned_cutoff = False
        self._warned_cutoff2 = False
        self._warned_bandpass_range = False

    def set_filter_parameters(self, filter_type, cutoff_frequency, sample_rate, cutoff_frequency2=None):
        """Setzt Filter-Parameter aus GUI"""
        self.filter_type = filter_type
        self.cutoff_frequency = cutoff_frequency
        self.cutoff_frequency2 = cutoff_frequency2
        self.sample_rate = sample_rate

    def set_filter_characteristics(self, characteristic, order):
        """Setzt Filter-Charakteristik und Ordnung"""
        if order < 1:
            raise ValueError(f"Filter-Ordnung muss >= 1 sein, ist aber {order}")
        self.characteristic = characteristic
        self.order = order

    def apply_filter(self, input_signal):
        """Wendet den gewählten Filter auf das Signal an"""
        if self.filter_type == Cfg.Defaults.FILTER_TYP or self.cutoff_frequency is None:
            return input_signal

        # NaN/Inf-Behandlung
        if not np.all(np.isfinite(input_signal)):
            if not self._warned_nan_inf:
                logger.warning("Signal enthält NaN/Inf-Werte; Filterung überspringen")
                self._warned_nan_inf = True
            return input_signal

        try:
            nyquist = self.sample_rate / 2
            normalized_cutoff = self.cutoff_frequency / nyquist

            if normalized_cutoff >= 1.0:
                if not self._warned_cutoff:
                    logger.warning("Grenzfrequenz %.3f Hz zu hoch für Nyquist %.3f Hz", self.cutoff_frequency, nyquist)
                    self._warned_cutoff = True
                return input_signal

            if self.filter_type == "Tiefpass":
                return self.apply_lowpass_filter(input_signal, normalized_cutoff)
            elif self.filter_type == "Hochpass":
                return self.apply_highpass_filter(input_signal, normalized_cutoff)
            elif self.filter_type == "Bandpass":
                if self.cutoff_frequency2 is not None:
                    normalized_cutoff2 = self.cutoff_frequency2 / nyquist
                    if normalized_cutoff2 >= 1.0:
                        if not self._warned_cutoff2:
                            logger.warning("Grenzfrequenz2 %.3f Hz zu hoch für Nyquist %.3f Hz", self.cutoff_frequency2, nyquist)
                            self._warned_cutoff2 = True
                        return input_signal
                    return self.apply_bandpass_filter(input_signal, normalized_cutoff, normalized_cutoff2)
                else:
                    return self.apply_bandpass_filter(input_signal, normalized_cutoff)
            else:
                return input_signal

        except Exception:
            logger.exception("Fehler beim Anwenden des Filters")
            return input_signal

    def apply_lowpass_filter(self, input_signal, normalized_cutoff):
        """Tiefpass-Filter (SOS-basiert für bessere numerische Stabilität)"""
        if self.characteristic == "bessel":
            sos = signal.bessel(self.order, normalized_cutoff, btype='low', analog=False, output='sos')
        elif self.characteristic == "Chebyshev I":
            sos = signal.cheby1(self.order, 1, normalized_cutoff, btype='low', analog=False, output='sos')
        elif self.characteristic == "elliptic":
            sos = signal.ellip(self.order, 1, 40, normalized_cutoff, btype='low', analog=False, output='sos')
        else:  # butterworth
            sos = signal.butter(self.order, normalized_cutoff, btype='low', analog=False, output='sos')
        filtered_signal = signal.sosfiltfilt(sos, input_signal)
        return filtered_signal

    def apply_highpass_filter(self, input_signal, normalized_cutoff):
        """Hochpass-Filter (SOS-basiert für bessere numerische Stabilität)"""
        if self.characteristic == "bessel":
            sos = signal.bessel(self.order, normalized_cutoff, btype='high', analog=False, output='sos')
        elif self.characteristic == "Chebyshev I":
            sos = signal.cheby1(self.order, 1, normalized_cutoff, btype='high', analog=False, output='sos')
        elif self.characteristic == "elliptic":
            sos = signal.ellip(self.order, 1, 40, normalized_cutoff, btype='high', analog=False, output='sos')
        else:  # butterworth
            sos = signal.butter(self.order, normalized_cutoff, btype='high', analog=False, output='sos')
        filtered_signal = signal.sosfiltfilt(sos, input_signal)
        return filtered_signal

    def apply_bandpass_filter(self, input_signal, normalized_cutoff_low, normalized_cutoff_high=None):
        """Bandpass-Filter (SOS-basiert, benötigt BEIDE Grenzfrequenzen)"""
        # STRENGE VALIDIERUNG: Beide Frequenzen MÜSSEN gesetzt sein
        if normalized_cutoff_high is None:
            raise ValueError(
                "Bandpass-Filter benötigt zwei Grenzfrequenzen! "
                "Bitte setzen Sie sowohl cutoff_frequency als auch cutoff_frequency2."
            )

        low = normalized_cutoff_low
        high = normalized_cutoff_high

        # Validierung: low < high
        if low >= high:
            if not self._warned_bandpass_range:
                logger.warning(
                    "untere Grenzfrequenz %.2f Hz muss kleiner als obere %.2f Hz sein",
                    low * self.sample_rate / 2,
                    high * self.sample_rate / 2,
                )
                self._warned_bandpass_range = True
            raise ValueError(
                f"Untere Grenzfrequenz ({low*self.sample_rate/2:.2f} Hz) muss kleiner sein "
                f"als obere Grenzfrequenz ({high*self.sample_rate/2:.2f} Hz)!"
            )

        effective_order = self.order

        if self.characteristic == "bessel":
            sos = signal.bessel(effective_order, [low, high], btype='band', analog=False, output='sos')
        elif self.characteristic == "Chebyshev I":
            sos = signal.cheby1(effective_order, 1, [low, high], btype='band', analog=False, output='sos')
        elif self.characteristic == "elliptic":
            sos = signal.ellip(effective_order, 1, 40, [low, high], btype='band', analog=False, output='sos')
        else:  # butterworth
            sos = signal.butter(effective_order, [low, high], btype='band', analog=False, output='sos')
        filtered_signal = signal.sosfiltfilt(sos, input_signal)
        return filtered_signal

    def get_filter_coefficients(self):
        """Berechnet und speichert die Filter-Koeffizienten"""
        if self.filter_type == Cfg.Defaults.FILTER_TYP or self.cutoff_frequency is None or self.sample_rate is None:
            self.b_coeffs = None
            self.a_coeffs = None
            self.sos_coeffs = None
            return None, None, None

        try:
            nyquist = self.sample_rate / 2
            normalized_cutoff = self.cutoff_frequency / nyquist

            if normalized_cutoff >= 1.0:
                self.b_coeffs = None
                self.a_coeffs = None
                self.sos_coeffs = None
                return None, None, None

            if self.filter_type == "Tiefpass":
                if self.characteristic == "bessel":
                    self.sos_coeffs = signal.bessel(self.order, normalized_cutoff, btype='low', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "Chebyshev I":
                    self.sos_coeffs = signal.cheby1(self.order, 1, normalized_cutoff, btype='low', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "elliptic":
                    self.sos_coeffs = signal.ellip(self.order, 1, 40, normalized_cutoff, btype='low', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                else:
                    self.sos_coeffs = signal.butter(self.order, normalized_cutoff, btype='low', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
            elif self.filter_type == "Hochpass":
                if self.characteristic == "bessel":
                    self.sos_coeffs = signal.bessel(self.order, normalized_cutoff, btype='high', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "Chebyshev I":
                    self.sos_coeffs = signal.cheby1(self.order, 1, normalized_cutoff, btype='high', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "elliptic":
                    self.sos_coeffs = signal.ellip(self.order, 1, 40, normalized_cutoff, btype='high', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                else:
                    self.sos_coeffs = signal.butter(self.order, normalized_cutoff, btype='high', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
            elif self.filter_type == "Bandpass":
                if self.cutoff_frequency2 is not None:
                    normalized_cutoff2 = self.cutoff_frequency2 / nyquist
                    if normalized_cutoff2 >= 1.0:
                        logger.warning("Grenzfrequenz2 %.3f Hz zu hoch für Nyquist %.3f Hz", self.cutoff_frequency2, nyquist)
                        self.b_coeffs = None
                        self.a_coeffs = None
                        self.sos_coeffs = None
                        return None, None, None
                    low = normalized_cutoff
                    high = normalized_cutoff2
                else:
                    low = max(0.01, normalized_cutoff * 0.8)
                    high = min(0.99, normalized_cutoff * 1.2)

                if low >= high:
                    logger.warning("Untere Grenzfrequenz %.3f Hz muss kleiner als obere %.3f Hz sein", low * nyquist, high * nyquist)
                    self.b_coeffs = None
                    self.a_coeffs = None
                    self.sos_coeffs = None
                    return None, None, None

                effective_order = self.order

                if self.characteristic == "bessel":
                    self.sos_coeffs = signal.bessel(effective_order, [low, high], btype='band', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "elliptic":
                    self.sos_coeffs = signal.ellip(effective_order, 1, 40, [low, high], btype='band', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                elif self.characteristic == "Chebyshev I":
                    self.sos_coeffs = signal.cheby1(effective_order, 1, [low, high], btype='band', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)
                else:
                    self.sos_coeffs = signal.butter(effective_order, [low, high], btype='band', analog=False, output='sos')
                    self.b_coeffs, self.a_coeffs = signal.sos2tf(self.sos_coeffs)

            return self.b_coeffs, self.a_coeffs, self.sos_coeffs

        except Exception:
            logger.exception("Fehler bei Filter-Koeffizienten-Berechnung")
            self.b_coeffs = None
            self.a_coeffs = None
            self.sos_coeffs = None
            return None, None, None

    def get_filter_info(self):
        """Gibt ein Dictionary mit allen Filter-Parametern zurück"""
        return {
            'type': self.filter_type,
            'characteristic': self.characteristic,
            'order': self.order,
            'sample_rate': self.sample_rate,
            'cutoff': self.cutoff_frequency,
            'cutoff2': self.cutoff_frequency2
        }

    def get_coefficients(self):
        """Gibt nur die b und a Koeffizienten zurück (Wrapper für get_filter_coefficients)"""
        b, a, _ = self.get_filter_coefficients()
        return b, a

    def get_frequency_response(self, num_points=1024):
        """Berechnet den Frequenzgang des Filters"""
        if self.b_coeffs is None or self.a_coeffs is None or self.sample_rate is None:
            return None, None, None

        try:
            w, h = signal.freqz(self.b_coeffs, self.a_coeffs, worN=num_points, fs=self.sample_rate)
            magnitude_db = 20 * np.log10(np.abs(h))
            phase_deg = np.angle(h, deg=True)
            return w, magnitude_db, phase_deg
        except Exception:
            logger.exception("Fehler bei Frequenzgang-Berechnung")
            return None, None, None

    @staticmethod
    def format_filter_info_text(filter_type, characteristic, order, cutoff_freq, cutoff_freq2, sample_rate, b, a, sos):
        """Generiert den Info-Text für Filter-Parameter und Koeffizienten."""
        ft = filter_type if filter_type else Cfg.Defaults.FILTER_TYP
        ch = characteristic if characteristic else Cfg.Defaults.FILTER_CHARAKTERISTIK
        od = order if order else 4
        cf = cutoff_freq if cutoff_freq else "Nicht gesetzt"
        cf2 = cutoff_freq2 if cutoff_freq2 else "Nicht gesetzt"
        sr = sample_rate if sample_rate else "Nicht gesetzt"

        info_text = f"""FILTER-PARAMETER:
    ========================
    Filtertyp: {ft}
    Charakteristik: {ch}
    Ordnung: {od}
    Grenzfrequenz 1: {cf} Hz
    Grenzfrequenz 2: {cf2} Hz
    Samplerate: {sr} Hz
    """
        if b is not None and a is not None:
            info_text += f"""
    TRANSFER FUNKTION (ba)
    ========================
    WICHTIG: Diese ba-Koeffizienten dienen nur zur mathematischen 
    Beschreibung und können bei höheren Ordnungen numerische 
    Rundungsfehler aufweisen!

    • b (Zähler): 
    {np.array2string(b, precision=6, separator=', ', max_line_width=50, formatter={'float_kind': lambda x: f'{x:.6e}'})}

    • a (Nenner): 
    {np.array2string(a, precision=6, separator=', ', max_line_width=50, formatter={'float_kind': lambda x: f'{x:.6e}'})}

    BA-MATRIX (Gleitkommadarstellung):
    b-Koeffizienten: {b.shape[0]} Werte
    a-Koeffizienten: {a.shape[0]} Werte

    HINWEIS: Die tatsächliche Filterung verwendet die numerisch
    stabilere SOS-Form (siehe unten)!
    """

        if sos is not None:
            info_text += f"""
    SECOND-ORDER SECTIONS (sos):
    =============================
    DIESE WERTE WERDEN FÜR DIE TATSÄCHLICHE FILTERUNG VERWENDET!

    SOS Matrix ({sos.shape[0]} Sektionen):
    {np.array2string(sos, precision=6, separator=', ', max_line_width=50)}

    ORDNUNGS-ZUSAMMENHANG BEI SOS:
    =============================
    Gewählte Sektionen/Ordnung: {od}
    Anzahl SOS-Sektionen: {sos.shape[0]}
    Effektive Gesamtordnung: {sos.shape[0] * 2}
    """

        if sample_rate and cutoff_freq and cutoff_freq != "Nicht gesetzt":
            nyquist = sample_rate / 2
            normalized_cutoff = cutoff_freq / nyquist
            info_text += f"""
    FREQUENZ-INFORMATIONEN:
    ========================
    Nyquist-Frequenz: {nyquist:.2f} Hz
    Normalisierte Grenzfrequenz: {normalized_cutoff:.4f}
    Grenzfrequenz (physikalisch): {cutoff_freq} Hz
    """

        if ft == "Bandpass" and cf2 != "Nicht gesetzt" and cf != "Nicht gesetzt":
            try:
                info_text += f"""
    BANDPASS-PARAMETER:
    ====================
    Untere Grenzfrequenz: {cf} Hz
    Obere Grenzfrequenz: {cf2} Hz
    Bandbreite: {float(cf2) - float(cf):.2f} Hz
    """
            except Exception:
                logger.debug("Bandpass-Parameter konnten nicht formatiert werden")

        return info_text

    def reset_filter(self):
        """Setzt alle Filter-Parameter auf Standardwerte zurück"""
        self.filter_type = Cfg.Defaults.FILTER_TYP
        self.cutoff_frequency = None
        self.cutoff_frequency2 = None
        self.order = None
        self.sample_rate = None
        self.characteristic = Cfg.Defaults.FILTER_CHARAKTERISTIK
        self.b_coeffs = None
        self.a_coeffs = None
        self.sos_coeffs = None
        logger.info("Filter wurde zurückgesetzt")