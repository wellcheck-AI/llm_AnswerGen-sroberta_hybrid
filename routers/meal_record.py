import os
import re
import json
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
    async_generate_nutrition,
    get_db,
    FoodNutrition,
    MealRecordError
)
from utils.logger_setup import setup_logger
from utils.alert import send_discord_alert

API_KEY = os.environ.get("API_KEY") #API service key

logger = setup_logger("meal_record_logger", "meal_record.log")

router = APIRouter()

@router.post("/nutrition")
async def nutrition(
        request: Request, 
        #db: Session = Depends(get_db)
        db: AsyncSession = Depends(get_db)
    ):
    try:
        headers = request.headers
        provided_api_key = headers.get("x-api-key")

        if not provided_api_key or provided_api_key != API_KEY:
            raise MealRecordError.InvalidAPIKeyError(provided_api_key=provided_api_key)
        
        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        food_name = body.get("foodName")
        quantity = body.get("quantity", -1)
        unit = body.get("unit", -1)

        if not food_name.strip():
            raise MealRecordError.InvalidInputError(
                message='Missing or empty food name', 
                extra={"body": body}, 
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

        # existing_record = db.query(FoodNutrition).filter(
        #     FoodNutrition.food_name == food_name,
        #     FoodNutrition.quantity == quantity,
        #     FoodNutrition.unit == unit
        # ).first()

        existing_record_result = await db.execute(
            select(FoodNutrition).where(
                FoodNutrition.food_name == food_name,
                FoodNutrition.quantity == quantity,
                FoodNutrition.unit == unit
            )
        )
        existing_record = existing_record_result.scalar()

        if existing_record:
            existing_record.call_count += 1
            existing_record.updated_at = datetime.now(pytz.timezone('Asia/Seoul'))
            await db.commit()

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
        
        # new_record = generate_nutrition(food_name=food_name, unit=unit, quantity=quantity)
        new_record = await async_generate_nutrition(food_name=food_name, unit=unit, quantity=quantity)

        db.add(new_record)
        await db.commit()

        logger.info('Nutrition data saved to database', extra=new_record.json())
        
        response_data = new_record.json()
        try:
            return JSONResponse(status_code=201, content=response_data)
        except Exception as e:
            raise MealRecordError.ResponseParsingError(raw_response=response_data)
        
    except openai.OpenAIError as e:
        await handle_openai_error(e)

    except json.JSONDecodeError as e:
        logger.error(f"{str(e)}\n{body_str}", exc_info=traceback.format_exc())
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
        logger.error(str(e), extra=e.metadata(), exc_info=traceback.format_exc())
        raise HTTPException(
            status_code=510,
            detail={
                "code": 510,
                "message": "AI가 계산하기 어려운 영양성분입니다"
            }
        )

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