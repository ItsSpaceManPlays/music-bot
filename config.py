from logging.config import dictConfig
import logging
import colorlog
import os

os.makedirs("logs", exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)-10s - %(asctime)s - %(module)-15s : %(message)s"
        },
        "standard": {
            "format": "%(asctime_log_color)s%(asctime)s %(reset)s%(log_color)s%(levelname)-10s %(name)-15s %(message_log_color)s%(message)s",
            "()": "colorlog.ColoredFormatter",
            "log_colors": {
                "DEBUG": "blue",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "purple",
            },
            "secondary_log_colors": {
                "asctime": {
                    "DEBUG": "bold_black",
                    "INFO": "bold_black",
                    "WARNING": "bold_black",
                    "ERROR": "bold_black",
                    "CRITICAL": "bold_black",
                },
                "message": {
                    "DEBUG": "black",
                    "INFO": "black",
                    "WARNING": "black",
                    "ERROR": "black",
                    "CRITICAL": "black",
                }
            },
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "colorlog.StreamHandler",
            "formatter": "standard"
        },
        "console2": {
            "level": "WARNING",
            "class": "colorlog.StreamHandler",
            "formatter": "standard"
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/info.log",
            "mode": "w",
            "formatter": "verbose"
        }
    },
    "loggers": {
        "bot": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False
        },
        "discord": {
            "handlers": ["console2", "file"],
            "level": "INFO",
            "propagate": False
        }
    }
}

dictConfig(LOGGING_CONFIG)