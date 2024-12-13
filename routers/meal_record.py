import os
import re
import json
import uuid
import traceback

from datetime import datetime

import pytz
import openai

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from MealRecord import (
    generate_nutrition,
    get_db,
    FoodNutrition
)
from utils.alert import send_discord_alert
from utils.log_schema import LogSchema, APIException, log_custom_error
from utils.firebase_logger import request_log

API_KEY = os.environ.get("API_KEY") #API service key

LOGGER_NAME = "meal"

router = APIRouter()

@router.post("/nutrition")
async def nutrition(
        request: Request, 
        db: AsyncSession = Depends(get_db)
    ):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME)

        headers = dict(request.headers)

        provided_api_key = headers.get("x-api-key")

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        _log.set_request_log(body, request)

        if not provided_api_key or provided_api_key != API_KEY:
            raise APIException(
                code=400,
                name="InvalidAPIKeyException",
                message="API 키가 유효하지 않습니다",
                traceback=log_custom_error()
            )
        
        food_name = body.get("foodName")
        quantity = body.get("quantity", -1)
        unit = body.get("unit", -1)
        
        if not food_name.strip():
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="음식명이 없습니다",
                traceback=log_custom_error()
            )
        
        food_name_trimmed = food_name.strip()
        special_chars_only = re.compile(r'^[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>/?]+$') # 안걸러짐 (ex: ×÷=/_[]-'; / `~\€£¥°•○●□■♤♡◇♧☆▪︎¤《》¡¿)

        if special_chars_only.match(food_name_trimmed):
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="올바른 음식명이 아닙니다",
                traceback=log_custom_error()
            )
        if len(food_name_trimmed) > 255:
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="음식명이 너무 깁니다",
                traceback=log_custom_error()
            )
        if not quantity or quantity <= 0 or not isinstance(quantity, (int, float)):
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="섭취량이 없습니다",
                traceback=log_custom_error()
            )
        if unit is None:
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="섭취량 단위가 없습니다",
                traceback=log_custom_error()
            )
        if not isinstance(unit, int) or unit < 0 or unit > 4:
            raise APIException(
                code=400,
                name="InvalidInputException",
                message="올바르지 않은 섭취량 단위입니다 (0: 인분, 1: 개, 2: 접시, 3: g, 4: ml)",
                traceback=log_custom_error()
            )
        
        response_content = {}

        existing_record_result = await db.execute(
            select(FoodNutrition).where(
                FoodNutrition.food_name == food_name,
                FoodNutrition.quantity == quantity,
                FoodNutrition.unit == unit
            )
        )
        existing_record = existing_record_result.scalar()

        if existing_record:
            response_content = {
                'foodName': food_name,
                'quantity': quantity,
                'unit': unit,
                "serving_size": existing_record.serving_size,
                'nutrition': {
                    'carbohydrate': existing_record.carbohydrate,
                    'sugar': existing_record.sugar,
                    'dietaryFiber': existing_record.dietary_fiber,
                    'protein': existing_record.protein,
                    'fat': existing_record.fat,
                    'starch': existing_record.starch
                }
            }

            existing_record.call_count += 1
            
            timestamp = datetime.now(pytz.timezone('Asia/Seoul'))
            existing_record.updated_at = timestamp
            await db.commit()
            
            response_data = {key: value for key, value in response_content.items() if key != "nutrition"}
            response_data.update(response_content.get("nutrition", {}))

            try:
                status_code = 200
                message = "Returning cached nutrition data"
                return JSONResponse(status_code=status_code, content=response_data)
            except Exception as e:
                status_code = 500
                message = "알 수 없는 오류가 발생했습니다"
                raise APIException(
                    code=status_code,
                    name="UnexpectedException",
                    message="알 수 없는 오류가 발생했습니다",
                    gpt_output=response_data,
                    traceback=traceback.format_exc()
                )
            finally:
                if status_code == 200:
                    try:
                        _log.set_response_log(content=response_content, status_code=status_code, message=message)
                        request_log(logger=LOGGER_NAME, request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
                    except Exception as log_exception:
                        pass
        
        new_record = await generate_nutrition(food_name=food_name, unit=unit, quantity=quantity)

        db.add(new_record)
        await db.commit()

        response_content = new_record.json()
        
        response_data = {key: value for key, value in response_content.items() if key != "nutrition"}
        response_data.update(response_content.get("nutrition", {}))
        
        try:
            status_code = 201
            message = "Nutrition data saved to database"
            return JSONResponse(status_code=status_code, content=response_data)
        except Exception as e:
            status_code = 500
            message = "알 수 없는 오류가 발생했습니다"
            raise APIException(
                code=status_code,
                name="UnexpectedException",
                message=message,
                gpt_output=response_data,
                traceback=traceback.format_exc()
                )
        finally:
            try:
                if status_code == 201:
                    _log.set_response_log(content=response_content, status_code=status_code, message=message)
                    request_log(logger=LOGGER_NAME, request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
            except Exception as log_exception:
                pass
    
    except openai.OpenAIError as e:
        await handle_openai_error(e)
    
    except APIException as e:
        try:
            e.log(_log)
            request_log(logger=LOGGER_NAME, request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        except Exception as log_exception:
            pass

        raise HTTPException(
            status_code=e.code,
            detail={
                "code": e.code,
                "message": e.message
            }
        )
    
    except Exception as e:
        try:
            _log.set_error_log("UnexpectedException", traceback=traceback.format_exc(), generated=None)
            _log.set_response_log(None, 500, "알 수 없는 오류가 발생했습니다")
            
            request_log(logger=LOGGER_NAME, request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        except Exception as log_exception:
            pass

        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "알 수 없는 오류가 발생했습니다"
            }
        )
    
async def handle_openai_error(e):
    status_code = getattr(e, 'http_status', 500)
    error_type = getattr(e, 'error', {}).get('type')
    error_code = getattr(e, 'error', {}).get('code')

    if status_code == 400:
        raise APIException(
            code=500,
            name="OpenAIError.InvalidRequest",
            message="영양 성분 계산에 실패했습니다",
            traceback=e
        )
    elif status_code in [401, 403]:
        send_discord_alert(str(e))
        raise APIException(
            code=500,
            name="OpenAIError.AuthenticationFailed",
            message="영양 성분 계산에 실패했습니다",
            traceback=e
        )
    elif status_code == 429:
        send_discord_alert(str(e))
        if error_type == 'tokens':
            raise APIException(
                code=503,
                name="OpenAIError.TokenQuotaExceeded",
                traceback=e,
                message="현재 영양성분 분석이 불가능합니다"
            )
    elif error_type == 'rate_limit_exceeded':
        raise APIException(
            code=503,
            name="OpenAIError.RateLimitExceeded",
            traceback=e,
            message="현재 영양성분 분석이 불가능합니다"
        )
    elif status_code >= 500:
        send_discord_alert(str(e))
        raise APIException(
            code=503,
            name="OpenAIError.Timeout",
            traceback=e,
            message="현재 영양성분 분석이 불가능합니다"
        )
    elif error_code == 'context_length_exceeded':
        raise APIException(
            code=400,
            name="OpenAIError.ContextLengthExceeded",
            traceback=e,
            message="입력값이 너무 깁니다"
        )
    else:
        raise APIException(
            code=500,
            name="OpenAIError.UnexpectedException",
            traceback=e,
            message="영양 성분 계산에 실패했습니다"
        )