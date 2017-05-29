
from os import path, makedirs
from logging import getLogger, Formatter, NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL, StreamHandler, basicConfig
from logging.handlers import RotatingFileHandler

from nanohttp import settings, LazyAttribute


_loggers = {}
_handlers = {}
_formatters = {}
root_logger_is_configured = False


def get_level(name):
    return {
        'notset': NOTSET,       # 0
        'debug': DEBUG,         # 10
        'info': INFO,           # 20
        'warning': WARNING,     # 30
        'error': ERROR,         # 40
        'critical': CRITICAL    # 50
    }[name]


def ensure_formatter(name):
    if name not in _formatters:
        formatter_config = settings.logging.formatters.default.copy()
        formatter_config.update(settings.logging.formatters.get(name, {}))
        _formatters[name] = Formatter(formatter_config.format, formatter_config.date_format)
    return _formatters[name]


def ensure_handler(name):
    if name not in _handlers:

        handler_config = settings.logging.handlers.default.copy()
        handler_config.update(settings.logging.handlers.get(name, {}))

        if handler_config.type == 'console':
            handler = StreamHandler()
        elif handler_config.type == 'file':
            directory = path.dirname(handler_config.filename)
            if not path.exists(directory):
                makedirs(directory)
            handler = RotatingFileHandler(
                handler_config.filename,
                encoding='utf-8',
                maxBytes=handler_config.get('max_bytes', 52428800)
            )
        else:
            raise ValueError('Invalid handler type: %s' % handler_config.type)

        if handler_config.level != 'notset':
            handler.setLevel(get_level(handler_config.level))

        # Attaching newly created formatter to the handler
        handler.setFormatter(ensure_formatter(handler_config.formatter))
        _handlers[name] = handler

    return _handlers[name]


def ensure_root_logger():
    global root_logger_is_configured

    if root_logger_is_configured:
        return

    basicConfig(handlers=settings.logging.loggers.default.handlers, level=settings.logging.loggers.default.level)
    root_logger_is_configured = True


def ensure_logger(name):
    global root_logger_is_configured
    ensure_root_logger()

    if name in _loggers:
        # Rebasing with default config
        logger_config = settings.logging.loggers.default.copy()
        logger_config.update(settings.logging.loggers.get(name, {}))
        level = get_level(logger_config.level)

        # Creating logger
        logger = getLogger(name)
        logger.setLevel(level)
        logger.propagate = logger_config.propagate

        # Creating Handlers
        for handler_name in logger_config.handlers:
            logger.addHandler(ensure_handler(handler_name))

        # Adding the first log entry
        logger.info('Logger %s just initialized' % name)
        _loggers[name] = logger

    return _loggers[name]


class LoggerProxy(object):
    def __init__(self, name):
        self.name = name

    @LazyAttribute
    def logger(self):
        return ensure_logger(self.name)

    def info(self, *args, **kw):
        self.logger.info(*args, **kw)

    def debug(self, *args, **kw):
        self.logger.debug(*args, **kw)

    def error(self, *args, **kw):
        self.logger.error(*args, **kw)

    def warning(self, *args, **kw):
        self.logger.warning(*args, **kw)

    def critical(self, *args, **kw):
        self.logger.critical(*args, **kw)

    def exception(self, *args, **kw):
        self.logger.exception(*args, **kw)


def get_logger(logger_name='main'):
    logger = _loggers.get(logger_name)
    if not logger:
        logger = _loggers[logger_name] = LoggerProxy(logger_name)
    return logger
