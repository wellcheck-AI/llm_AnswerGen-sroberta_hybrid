import os
import logging
import requests
# from utils.logger import logger

def send_discord_alert(error):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    print('Webhook URL:', 'exists' if webhook_url else 'missing')
    
    if not webhook_url:
        # logger.error('Discord webhook URL is missing')
        return

    try:
        error_message = ''
        error_status = ''
        
        if hasattr(error, 'response') and error.response is not None:
            error_status = getattr(error.response, 'status', '')
            error_data = getattr(error.response, 'data', {})
            error_message = error_data.get('error', {}).get('message', '') or str(error)
        else:
            error_message = str(error)
        
        content = f"🚨 OpenAI API 오류 발생\n상태코드: {error_status}\n```\n{error_message}\n```"
        
        # logger.info('Sending Discord alert', extra={'content': content})
        response = requests.post(webhook_url, json={'content': content})
        response.raise_for_status()
        # logger.info('Discord alert sent successfully')
    except Exception as err:
        # logger.error('Discord alert failed', extra={
        #     'error': str(err),
        #     'originalError': str(error)
        # })
        print(err)
