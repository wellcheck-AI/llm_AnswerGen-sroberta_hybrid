import os
import re
import json

from datetime import datetime

import pytz
import openai

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from MealRecord import (
    generate_nutrition,
    get_db,
    FoodNutrition,
    MealRecordError
)
from utils.logger_setup import setup_logger
from utils.alert import send_discord_alert

API_KEY = os.environ.get("API_KEY") #API service key

logger = setup_logger("meal_record_logger", "meal_record.log")

router = APIRouter()

class GenNutritionRequest(BaseModel):
    foodName: str
    quantity: float
    unit: int

    def json(self):
        return {
            "food_name": self.foodName,
            "quantity": self.quantity,
            "unit": self.unit
        }

@router.post("/nutrition")
async def nutrition(
        request: GenNutritionRequest, 
        provided_api_key: Optional[str] = Header(None, alias="x-api-key"), 
        content_type: Optional[str] = Header(None, alias="Content-Type"), 
        db: Session = Depends(get_db)
    ):
    try:
        if not provided_api_key or provided_api_key != API_KEY:
            raise MealRecordError.InvalidAPIKeyError(provided_api_key=provided_api_key)
        
        data = request.json()

        food_name = data["food_name"]
        quantity = data["quantity"]
        unit = data["unit"]
        
        logger.info('API Request received', extra=data)

        if not food_name.strip():
            raise MealRecordError.InvalidInputError(
                message='Missing or empty food name', 
                extra={"body": data}, 
                inform_msg="음식명이 없습니다"
            )
        
        food_name_trimmed = food_name.strip()
        special_chars_only = re.compile(r'^[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>/?]+$')

        if special_chars_only.match(food_name_trimmed):
            raise MealRecordError.InvalidInputError(
                message='Special characters only in food name', 
                extra={"foodName": food_name_trimmed},
                inform_msg="올바른 음식명이 아닙니다"
            )
        if not quantity or quantity <= 0 or not isinstance(quantity, (int, float)):
            raise MealRecordError.InvalidInputError(
                message="Invalid quantity",
                extra={"quantity": quantity},
                inform_msg="섭취량이 없습니다"
            )
        if unit is None:
            raise MealRecordError.InvalidInputError(
                message="Invalid unit",
                extra={"unit": unit},
                inform_msg="섭취량 단위가 없습니다"
            )
        if not isinstance(unit, int) or unit < 0 or unit > 4:
            raise MealRecordError.InvalidInputError(
                message="Invalid unit",
                extra={"unit": unit},
                inform_msg="올바르지 않은 섭취량 단위입니다 (0: 인분, 1: 개, 2: 접시, 3: g, 4: ml)"
            )

        existing_record = db.query(FoodNutrition).filter(
            FoodNutrition.food_name == food_name,
            FoodNutrition.quantity == quantity,
            FoodNutrition.unit == unit
        ).first()

        if existing_record:
            existing_record.call_count += 1
            existing_record.updated_at = datetime.now(pytz.timezone('Asia/Seoul'))
            db.commit()

            logger.info('Returning cached nutrition data', extra={
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
            })
            
            response_data = {
                'foodName': food_name,
                'quantity': quantity,
                'unit': unit,
                'carbohydrate': existing_record.carbohydrate,
                'sugar': existing_record.sugar,
                'dietaryFiber': existing_record.dietary_fiber,
                'protein': existing_record.protein,
                'fat': existing_record.fat,
                'starch': existing_record.starch
            }
            return JSONResponse(status_code=200, content=response_data)
        
        new_record = generate_nutrition(food_name=food_name, unit=unit, quantity=quantity)

        db.add(new_record)
        db.commit()

        logger.info('Nutrition data saved to database', extra=new_record.json())
        
        response_data = new_record.json()
        return JSONResponse(status_code=201, content=response_data)
        
    except openai.OpenAIError as e:
        await handle_openai_error(e)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail={
            'code': 400,
            'message': '잘못된 JSON 형식입니다'
        })
    
    except MealRecordError.InvalidInputError as e:
        logger.error(str(e), extra=e.metadata())
        raise HTTPException(
            status_code=400,
            detail={
                "code": 400,
                "message": e.inform_message()
            }
        )
    
    except MealRecordError.InvalidAPIKeyError as e:
        logger.error(str(e), extra=e.metadata())
        raise HTTPException(
            status_code=400,
            detail={
                "code": 400,
                "message": "API 키가 유효하지 않습니다",
                "error": f"Invalid API KEY: {provided_api_key}"
            }
        )
        
    except MealRecordError.GenerationFailedError as e:
        logger.error(str(e), extra={"foodName": food_name})
        raise HTTPException(
            status_code=510,
            detail={
                "code": 510,
                "message": "AI가 계산하기 어려운 영양성분입니다"
            }
        )
    
    except MealRecordError.ResponseParsingError as e:
        logger.error(str(e), extra={"foodName": food_name})
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "영양 성분 계산에 실패했습니다"
            }
        )
    
    except MealRecordError.NutritionError as e:
        logger.error(str(e), extra=e.metadata())

    except Exception as e:
        logger.error('Unexpected error', exc_info=e)
        raise HTTPException(status_code=500, detail={
            'code': 500,
            'message': '영양 성분 계산에 실패했습니다',
        })

async def handle_openai_error(e):
    status_code = getattr(e, 'http_status', 500)
    error_type = getattr(e, 'error', {}).get('type')
    error_code = getattr(e, 'error', {}).get('code')

    if status_code == 400:
        logger.error('Invalid request', exc_info=e)
        raise HTTPException(status_code=500, detail={
            'code': 500,
            'message': '영양 성분 계산에 실패했습니다',
        })
    elif status_code in [401, 403]:
        send_discord_alert(str(e))
        logger.error('Authentication failed', exc_info=e)
        raise HTTPException(status_code=500, detail={
            'code': 500,
            'message': '영양 성분 계산에 실패했습니다',
        })
    elif status_code == 429:
        send_discord_alert(str(e))
        logger.error('Token quota exceeded', exc_info=e)
        if error_type == 'tokens':
            raise HTTPException(status_code=503, detail={
                'code': 503,
                'message': '현재 영양성분 분석이 불가능합니다.',
            })
    elif error_type == 'rate_limit_exceeded':
        logger.error('Rate limit exceeded', exc_info=e)
        raise HTTPException(status_code=503, detail={
            'code': 503,
            'message': '현재 영양성분 분석이 불가능합니다.',
            })
    elif status_code >= 500:
        send_discord_alert(str(e))
        logger.error('>= 500 timeout', exc_info=e)
        raise HTTPException(status_code=503, detail={
            'code': 503,
            'message': '현재 영양성분 분석이 불가능합니다.'
        })
    elif error_code == 'context_length_exceeded':
        logger.error('음식명 길이초과 에러', exc_info=e)
        raise HTTPException(status_code=400, detail={
            'code': 400,
            'message': '입력값이 너무 깁니다'
        })
    else:
        raise HTTPException(status_code=500, detail={
            'code': 500,
            'message': '영양 성분 계산에 실패했습니다'
        })