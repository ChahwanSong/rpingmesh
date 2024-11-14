import logging
import os
from logging.handlers import RotatingFileHandler

# Create the logs directory if it doesn't exist
log_dir = "../logs"
logging_level = logging.INFO
console_level = logging.ERROR

if not os.path.exists(log_dir):
    os.makedirs(log_dir)


# Initialize a logger object and return
def initialize_consumer_logger(prefix, ipv4):
    # Set up the logger
    logger = logging.getLogger(f"{prefix}_consumer_{ipv4}")
    logger.setLevel(logging_level)  # Set the log level

    # Create a rotating file handler for the logger
    log_file = os.path.join(log_dir, f"{prefix}_consumer_{ipv4}.log")

    # Set maxBytes to 5MB (5 * 1024 * 1024) and backupCount to 0 (maximum 1 files)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=0
    )
    file_handler.setLevel(logging_level)

    # Create a logging format
    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    logger.info("Logger initialization is successful.")
    return logger


def initialize_pinglist_logger(host: str, middlename: str = "server"):
    logger = logging.getLogger(f"pinglist_{middlename}_{host}")
    logger.setLevel(logging_level)  # Set the log level

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)  # 콘솔에는 INFO 이상의 레벨만 출력

    log_file = os.path.join(log_dir, f"pinglist_{middlename}_{host}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=0,
    )
    file_handler.setLevel(logging_level)  # 파일에는 DEBUG 이상의 레벨을 저장

    formatter = logging.Formatter(
        "[%(asctime)s][%(levelname)s][%(filename)s:%(funcName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info("Logger initialization is successful.")
    return logger
