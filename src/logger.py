import logging
import sys
from logging.handlers import RotatingFileHandler

def get_logger(name="subscriber", log_file="app.log"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

logger = get_logger()
