import logging
from logging.handlers import TimedRotatingFileHandler
import json

from byled.settings import LOG_FILENAME

byled_logger = logging.getLogger('example')
byled_logger.setLevel(logging.INFO)

strfmt = '[%(asctime)s]  [%(levelname)s]\n%(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(fmt=strfmt, datefmt=datefmt)

hand = TimedRotatingFileHandler(LOG_FILENAME, when='d', interval=1, backupCount=62)

hand.setLevel(logging.INFO)
hand.setFormatter(formatter)

byled_logger.addHandler(hand)


def info(url, body, response):
    return byled_logger.info("url: " + url + "\n"
                             + "body:" + "\n" + json.dumps(body, ensure_ascii=False, indent=4) + "\n"
                             + "response:" + "\n" + json.dumps(response, ensure_ascii=False, indent=4))


def warning(url, body, response):
    return byled_logger.warning("url: " + url + "\n"
                                + "body:" + "\n" + json.dumps(body, ensure_ascii=False, indent=4) + "\n"
                                + "response:" + "\n" + json.dumps(response, ensure_ascii=False, indent=4))
