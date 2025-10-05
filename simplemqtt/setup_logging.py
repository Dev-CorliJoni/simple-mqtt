import logging

NAMESPACE = "simplemqtt"
logging.getLogger(NAMESPACE).addHandler(logging.NullHandler())


def get_logger(name):
    return logging.getLogger(f"{NAMESPACE}.{name}")
