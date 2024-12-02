from datetime import datetime
import os
import json
import re
import logging
from dotenv import load_dotenv
import pytz
from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from openai import OpenAI, OpenAIError

from MealRecord import send_discord_alert, SessionLocal, FoodNutrition
from logger_setup import setup_logger

router = APIRouter()
logger = setup_logger("meal_record_logger", "meal_record.log")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
api_key = os.getenv('API_KEY')
openaiClient = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

unit_mapping = {
    0: '인분',
    1: '개',
    2: '접시',
    3: 'g',
    4: 'ml',
}

system_instruction = """
주어진 음식명과 섭취량을 바탕으로, 다음 단계를 순서대로 따라 1회 제공량과 영양 성분을 생성하세요:

1. 음식명을 분석하여 해당 음식의 종류를 파악합니다.
   - 주어진 데이터가 음식명이 아닐 경우, 이후 단계를 생략하고 "None"만을 반환하세요.
2. 음식 종류와 섭취량을 참고하여 1회 제공량(g)을 추정합니다.
3. 주어진 음식명과 섭취량을 바탕으로, 평균적인 영양 성분(탄수화물, 스타치, 당류, 식이섬유, 단백질, 지방)을 생성합니다.
   - 각 영양 성분은 USDA, 한국 식약처 데이터베이스 등 공인된 데이터베이스의 일반적인 수치를 참고하여 생성하세요.
   - 탄수화물(g)은 다음 계산식을 따릅니다:
     탄수화물(g) = 스타치(g) + 당류(g) + 식이섬유(g).
4. 최종 결과를 아래 JSON 형식으로 출력합니다.
   - 출력 형식 이외의 텍스트를 생성하지 않도록 유의하세요.

출력 형식:
{
    "serving_size": (음식의 일반적 1회 제공량 추정치),
    "carbohydrate": (스타치 + 당류 + 식이섬유의 총합),
    "starch": (음식의 평균적 스타치 총량),
    "sugar": (음식의 평균적 당류 총량),
    "dietaryFiber": (음식의 평균적 식이섬유 총량),
    "protein": (음식의 평균적 단백질 총량),
    "fat": (음식의 평균적 지방 총량)
}
"""

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
       
@router.post("/nutrition")
async def nutrition(request: Request, db: Session = Depends(get_db)):
    try:
        headers = request.headers
        provided_api_key = headers.get('x-api-key')
        if not provided_api_key or provided_api_key != api_key:
            logger.warning('Invalid API key attempt', extra={'providedKey': provided_api_key})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': 'API 키가 유효하지 않습니다',
                'error': 'Invalid API key'
            })
        try:
            raw_body = await request.body()
            body_str = raw_body.decode()
            
            invalid_json_pattern = re.compile(r'[:,]\s*[,}]')
            if invalid_json_pattern.search(body_str):
                raise HTTPException(status_code=400, detail={
                    'code': 400,
                    'message': '필수 파라미터가 없습니다'
                })
                
            body = json.loads(body_str)
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '잘못된 JSON 형식입니다'
            })
        
        food_name = body.get('foodName')
        quantity = body.get('quantity')
        unit = body.get('unit')
        serving_size = body.get('servingSize')
        logger.info('API Request received', extra={
            'foodName': food_name,
            'quantity': quantity,
            'unit': unit
        })

        if not food_name or not food_name.strip():
            logger.warning('Missing or empty food name', extra={'body': body})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '음식명이 없습니다'
            })

        food_name_trimmed = food_name.strip()
        special_chars_only = re.compile(r'^[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>/?]+$')

        if special_chars_only.match(food_name_trimmed):
            logger.warning('Special characters only in food name', extra={'foodName': food_name_trimmed})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '올바른 음식명이 아닙니다'
            })
        if not quantity or quantity <= 0 or not isinstance(quantity, (int, float)):
            logger.warning('Invalid quantity', extra={'quantity': quantity})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '섭취량이 없습니다'
            })
        if unit is None:
            logger.warning('Invalid unit', extra={'unit': unit})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '섭취량 단위가 없습니다'
            })
        if unit is None or not isinstance(unit, int) or unit < 0 or unit > 4:
            logger.warning('Invalid unit', extra={'unit': unit})
            raise HTTPException(status_code=400, detail={
                'code': 400,
                'message': '올바르지 않은 섭취량 단위입니다 (0: 인분, 1: 개, 2: 접시, 3: g, 4: ml)'
            })
        
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
                'serving_size':serving_size,
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
        
        try:
            unit_text = unit_mapping[unit]
            user_input = f"음식명: {food_name}\n서빙 크기: {quantity} {unit_text}"

            response = openaiClient.chat.completions.create(
                model='gpt-4o', 
                messages=[
                    {'role': 'system', 'content': system_instruction},
                    {'role': 'user', 'content': user_input}
                ]
            )
            raw_content = response.choices[0].message.content
            if 'None' in raw_content:
                logger.info('AI unable to calculate nutrition', extra={'foodName': food_name})
                raise HTTPException(status_code=510, detail={
                    'code': 510,
                    'message': 'AI가 계산하기 어려운 영양성분입니다'
                })

            # json_match = re.search(r'{[\s\S]*?}', raw_content)
            # if json_match:
            #     potential_json = json_match.group()
            #     potential_json = re.sub(r'//.*$', '', potential_json, flags=re.MULTILINE)
            #     potential_json = re.sub(r',\s*}', '}', potential_json)
            #     nutrition_data = json.loads(potential_json)
            # else:
            #     raise ValueError('No JSON found in AI response')
            json_match = re.search(r'{[\s\S]*?}', raw_content)
            if not json_match:
                logger.info('openAI response에서 파싱 실패', extra={'foodName': food_name})
                raise HTTPException(status_code=500, detail={
                    'code': 500,
                    'message': '영양 성분 계산에 실패했습니다'
                })

            nutrition_data = json.loads(json_match.group())
               
            def parse_nutrient_value(value):
                if isinstance(value, str):
                    number = re.sub(r'[^\d.]', '', value)
                    return float(number)
                elif isinstance(value, (int, float)):
                    return value
                return float('nan')

            serving_size = parse_nutrient_value(nutrition_data.get('serving_size'))
            carbohydrate = parse_nutrient_value(nutrition_data.get('carbohydrate'))
            sugar = parse_nutrient_value(nutrition_data.get('sugar'))
            dietary_fiber = parse_nutrient_value(nutrition_data.get('dietaryFiber'))
            protein = parse_nutrient_value(nutrition_data.get('protein'))
            fat = parse_nutrient_value(nutrition_data.get('fat'))
            starch = parse_nutrient_value(nutrition_data.get('starch'))

            if any(map(lambda x: x is None or x < 0 or not isinstance(x, (int, float)), 
                       [carbohydrate, sugar, dietary_fiber, protein, fat, starch])):
                logger.error('Invalid nutrient values', extra={
                'foodName': food_name,
                'quantity': quantity,
                'unit': unit,
                'serving_size':serving_size,
                'carbohydrate': carbohydrate,
                'sugar': sugar,
                'dietaryFiber': dietary_fiber,
                'protein': protein,
                'fat': fat,
                'starch': starch
                })
                raise HTTPException(status_code=500, detail={
                    'code': 500,
                    'message': '영양 성분 계산에 실패했습니다',
                    'error': 'Invalid nutrient values'
                })

            new_record = FoodNutrition(
                food_name=food_name,
                quantity=quantity, 
                unit=unit,
                serving_size=serving_size,
                carbohydrate=carbohydrate,
                sugar=sugar,
                dietary_fiber=dietary_fiber,
                protein=protein,
                fat=fat,
                starch=starch,
                call_count=1
            )
            db.add(new_record)
            db.commit()

            logger.info('Nutrition data saved to database', extra={
                'foodName': food_name,
                'quantity': quantity,
                'unit': unit,
                'serving_size':serving_size,
                'nutrition': {
                'carbohydrate': carbohydrate,
                'sugar': sugar,
                'dietaryFiber': dietary_fiber,
                'protein': protein,
                'fat': fat,
                'starch': starch
                }
            })
            
            response_data = {
                'foodName': food_name,
                'quantity': quantity,
                'unit': unit,
                'serving_size':serving_size,
                'carbohydrate': carbohydrate,
                'sugar': sugar,
                'dietaryFiber': dietary_fiber,
                'protein': protein,
                'fat': fat,
                'starch': starch
            }
            return JSONResponse(status_code=201, content=response_data)
        
        except OpenAIError as e:
            await handle_openai_error(e)

        # except OpenAIError as e:
        #     logger.error('OpenAI API Error:', exc_info=e)
        #     status_code = e.http_status
        #     error_code = e.error.get('code')
        #     error_type = e.error.get('type')

        #     await handle_openai_error(
        #         e, food_name, quantity, unit, status_code, error_code, error_type
        #     )

    except HTTPException as http_exc:
        raise http_exc
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
        await send_discord_alert(str(e))
        logger.error('Authentication failed', exc_info=e)
        raise HTTPException(status_code=500, detail={
            'code': 500,
            'message': '영양 성분 계산에 실패했습니다',
        })
    elif status_code == 429:
        await send_discord_alert(str(e))
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
        await send_discord_alert(str(e))
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