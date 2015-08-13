import logging
import atexit


class Logger:
    cache = {
        'log_level': None,
        'message': ''
    }

    def __init__(self, logger, level=logging.INFO):
        """
        Initialize the logging class and set the default logging level

        :type logger: logging.Logger
        :param logger: The log object to write to

        :type level: int
        :param level: The log level to use by default
        """
        self.level = level
        self.logger = logger
        self.logger.setLevel(level)
        atexit.register(self.clean_cache)

    def write(self, log_line, multi_line=True, log_level=None):
        """
        Write a log message using the default settings

        :type log_line: string
        :param log_line: The message to write

        :type multi_line: int
        :param multi_line: The log level to use by default

        :type log_level: int
        :param log_level: The log level to use for this specific message
        """
        if log_level is None:
            log_level = self.level

        log_line = log_line.replace('\n', ' ')
        if multi_line:
            if self.cache['log_level'] is None:
                self.cache['log_level'] = log_level
            self.cache['message'] += log_line
        elif log_line != '\n':
            if self.cache['message']:
                self.logger.log(self.cache['log_level'], self.cache['message'])
            self.logger.log(log_level, log_line)
            self.cache['log_level'] = None
            self.cache['message'] = ''

    def clean_cache(self):
        if self.cache['message']:
            self.logger.log(self.cache['log_level'], '\n' + self.cache['message'])
            self.cache['log_level'] = None
            self.cache['message'] = ''

    def debug(self, log_line, multi_line=False):
        self.write(log_line, multi_line, logging.DEBUG)

    def info(self, log_line, multi_line=False):
        self.write(log_line, multi_line, logging.INFO)

    def warn(self, log_line, multi_line=False):
        self.write(log_line, multi_line, logging.WARNING)

    def error(self, log_line, multi_line=False):
        self.write(log_line, multi_line, logging.ERROR)

    def critical(self, log_line, multi_line=False):
        self.write(log_line, multi_line, logging.CRITICAL)
