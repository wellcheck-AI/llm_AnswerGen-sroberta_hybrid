from utils.firebase import db
from utils.alert import send_discord_alert
import uuid

import pytz
from datetime import datetime
seoul_tz = pytz.timezone('Asia/Seoul')

def request_log(logger, request_data, response_data, error=None):
    current_time = datetime.now(seoul_tz)
    try:
        logging_data = {
            "document_id": str(uuid.uuid4()),
            "timestamp": current_time,
            "request": request_data,
            "logger": logger,
            "response": response_data,
            "error": error or {
                "name": None,
                "generated": None,
                "traceback": None
            }
        }
        db.collection('logs').add(logging_data)
    except Exception as e:
        send_discord_alert(f'Firebase logging failed:, {str(e)}')