import traceback

from datetime import datetime

import pytz

from fastapi import Request

class LogSchema:
    def __init__(self, _id:str, logger:str):
        self._payload = {
            "document_id": _id,
            "logger": logger,
            "timestampe": None,
            "request": None,
            "response": None,
            "error": {
                "name": None,
                "generated": None,
                "traceback": None
            }
        }
    
    def set_request_log(self, body:dict, request:Request) -> None:
        headers = dict(request.headers)
        
        x_forwarded_for = headers.get("x-forwarded-for") # 리버스 프록시 뒤에 있는 경우
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host

        request_time = datetime.now(pytz.timezone('Asia/Seoul'))
        _log_headers = {key:headers[key] for key in ["x-api-key", "content-type"] if key in headers}

        method = "POST"

        self._payload["request"] = {
            "request_data": body,
            "ip": ip,
            "method": method,
            "headers": _log_headers,
            "timestamp": request_time
        }
    
    def set_response_log(self, content:dict, status_code:int, message:str|None) -> None:
        timestamp = datetime.now(pytz.timezone('Asia/Seoul'))
        self._payload["response"] = {
            "content": content,
            "status_code": status_code,
            "message": message,
            "timestamp": timestamp
        }
        self._payload["timestamp"] = timestamp

    def set_error_log(self, name:str, traceback:str, generated:str|None) -> None:
        self._payload["error"] = {
            "name": name,
            "traceback": traceback,
            "generated": generated
        }

    def get_request_log(self) -> dict | None:
        return self._payload["request"]
    
    def get_reseponse_log(self) -> dict | None:
        return self._payload["response"]
    
    def get_error_log(self) -> dict | None:
        return self._payload["error"]

    def to_json(self) -> dict:
        return self._payload
    
class APIException(Exception):
    def __init__(
            self,
            code:int, 
            name:str, 
            message:str,
            traceback:str|None=None, 
            gpt_output:str|None=None
        ):
        self.code = code
        self.name = name
        self.message = message
        self.traceback = traceback
        self.gpt_output = gpt_output
        super().__init__(self.message)

    def __str__(self):
        return f"{self.name}: {self.message}"
    
    def log(self, log_data: LogSchema):
        log_data.set_error_log(self.name, self.traceback, self.gpt_output)
        log_data.set_response_log(content=None, status_code=self.code, message=self.message)

def log_custom_error():
    stack_info = traceback.extract_stack()[:-1]
    for frame in reversed(stack_info):
        if "site-packages" not in frame.filename:
            location = f"{frame.filename}:{frame.lineno}"
            return location
    return "Unknown location"