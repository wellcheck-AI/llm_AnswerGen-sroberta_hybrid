import os
import logging
from logging.handlers import RotatingFileHandler
import json

log_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "utils_logs")
os.makedirs(log_dir, exist_ok=True)

_loggers = {}

class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }
        
        if hasattr(record, 'ip'):
            log_data['ip'] = record.ip
        if hasattr(record, 'method'):
            log_data['method'] = record.method
        if hasattr(record, 'path'):
            log_data['path'] = record.path
        if hasattr(record, 'request_data'):
            log_data['request_data'] = record.request_data
        if hasattr(record, 'response_data'):
            log_data['response_data'] = record.response_data
        if hasattr(record, 'status_code'):
            log_data['status_code'] = record.status_code
        if hasattr(record, 'error'):
            log_data['error'] = record.error
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

def setup_logger(name:str="dafult", log_file:str="app.log", level:int=logging.DEBUG):
    global _loggers

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, log_file),
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(CustomFormatter())
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(CustomFormatter())
    logger.addHandler(console_handler)

    logger.propagate = False

    _loggers[name] = logger
    return logger

def log_request_info(request, body=None):
    return {
        'ip': request.client.host,
        'method': request.method,
        'path': request.url.path,
        'request_data': body,
        'headers': dict(request.headers)
    }

def log_response_info(response_data, status_code, duration_ms):
    return {
        'response_data': response_data,
        'status_code': status_code,
        'duration_ms': duration_ms
    }