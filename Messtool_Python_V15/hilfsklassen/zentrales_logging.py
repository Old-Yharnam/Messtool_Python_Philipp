import os
import logging
import sys
from logging.handlers import RotatingFileHandler
import warnings

DEV_MODE = 0  # Set to 1 to show errors in console while keeping full log files
PROTOCOL_LOGGER_NAME = "user_protocol"
_session_end_logged = set()

class StreamToLogger:

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message):
        if not message:
            return
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)

    def flush(self):
        if self._buffer:
            self.logger.log(self.level, self._buffer)
            self._buffer = ""

    def isatty(self):
        return False

def _has_file_handler(logger, file_path):
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == file_path:
            return True
    return False

def _has_named_handler(logger, name):
    return any(getattr(handler, "name", None) == name for handler in logger.handlers)

def get_protocol_logger():
    return logging.getLogger(PROTOCOL_LOGGER_NAME)

def log_session_start(session_id, start_time, python_version, cwd, pid):
    app_logger = logging.getLogger(__name__)
    app_logger.info(
        "SESSION_START id=%s | %s | python=%s | cwd=%s | pid=%s",
        session_id,
        start_time,
        python_version,
        cwd,
        pid,
    )
    protocol_logger = get_protocol_logger()
    protocol_logger.info("SESSION_START id=%s | %s", session_id, start_time)

def log_session_end(session_id, end_time, reason="unknown"):
    if not session_id or session_id in _session_end_logged:
        return False
    _session_end_logged.add(session_id)
    app_logger = logging.getLogger(__name__)
    app_logger.info("SESSION_END id=%s | %s | reason=%s", session_id, end_time, reason)
    protocol_logger = get_protocol_logger()
    protocol_logger.info("SESSION_END id=%s | %s | reason=%s", session_id, end_time, reason)
    return True

def setup_logging(log_level=logging.INFO):

    if getattr(sys, 'frozen', False):
        project_root = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(base_dir, ".."))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "messtool.log")
    protocol_file = os.path.join(log_dir, "user_protocol.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    if not _has_file_handler(root_logger, log_file):
        root_logger.addHandler(file_handler)

    protocol_logger = get_protocol_logger()
    protocol_logger.setLevel(logging.INFO)
    protocol_logger.propagate = False
    protocol_formatter = logging.Formatter("%(asctime)s | %(message)s")
    protocol_handler = RotatingFileHandler(
        protocol_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    protocol_handler.setFormatter(protocol_formatter)
    protocol_handler.setLevel(logging.INFO)
    if not _has_file_handler(protocol_logger, protocol_file):
        protocol_logger.addHandler(protocol_handler)

    if DEV_MODE and not _has_named_handler(root_logger, "dev_console_error"):
        console_handler = logging.StreamHandler(stream=sys.stderr)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        console_handler.name = "dev_console_error"
        root_logger.addHandler(console_handler)

    logging.captureWarnings(True)
    warnings.simplefilter("once")
    sys.stdout = StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger("stderr"), logging.ERROR)