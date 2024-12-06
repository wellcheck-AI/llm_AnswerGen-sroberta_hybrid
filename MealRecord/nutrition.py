import os
import re
import json

import httpx
import asyncio

from openai import OpenAI

from MealRecord import MealRecordError
from .models import FoodNutrition

client = OpenAI()

UNIT_MAPPING = {
    0: '인분',
    1: '개',
    2: '접시',
    3: 'g',
    4: 'ml',
}

SYSTEM_INSTRUCTION = """
주어진 음식명과 섭취량을 바탕으로, 다음 단계를 순서대로 따라 섭취한 음식의 무게(g)와 영양 성분을 생성하세요:

1. 음식명을 분석하여 해당 음식의 종류를 파악합니다.
   - 주어진 데이터가 음식명이 아닐 경우, 이후 단계를 생략하고 "None"만을 반환하세요.
2. 음식 종류와 섭취량을 참고하여 섭취한 음식의 무게(g)를 추정합니다.
3. 주어진 음식명과 섭취량을 바탕으로, 평균적인 영양 성분(탄수화물, 스타치, 당류, 식이섬유, 단백질, 지방)을 생성합니다.
   - 각 영양 성분은 USDA, 한국 식약처 데이터베이스 등 공인된 데이터베이스의 일반적인 수치를 참고하여 생성하세요.
   - 탄수화물(g)은 다음 계산식을 따릅니다:
     탄수화물(g) = 스타치(g) + 당류(g) + 식이섬유(g).
   - 1회 제공량에 대한 영양성분이 아닌, 섭취량 기준의 영양성분을 생성해야 함에 유의하세요. 
4. 최종 결과를 아래 JSON 형식으로 출력합니다.
   - 출력 형식 이외의 텍스트를 생성하지 않도록 유의하세요.

출력 형식:
{
    "serving_size": (섭취한 음식의 무게),
    "carbohydrate": (스타치 + 당류 + 식이섬유의 총합),
    "starch": (섭취한 음식의 스타치 총량),
    "sugar": (섭취한 음식의 당류 총량),
    "dietaryFiber": (섭취한 음식의 식이섬유 총량),
    "protein": (섭취한 음식의 단백질 총량),
    "fat": (섭취한 음식의 지방 총량)
}
"""

def generate_nutrition(food_name:str, unit:int, quantity:int | float) -> FoodNutrition:
    unit_text = UNIT_MAPPING[unit]
    user_input = f"음식명: {food_name}\n섭취량: {quantity} {unit_text}"

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
    ).choices[0].message.content

    if "None" in response:
        raise MealRecordError.GenerationFailedError(food_name=food_name)
    
    json_match = re.search(r'{[\s\S]*?}', response)
    if not json_match:
        raise MealRecordError.ResponseParsingError(raw_response=response)

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

    generated_data = FoodNutrition(
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

    if any(map(lambda x: x is None or x < 0 or not isinstance(x, (int, float)), 
            [carbohydrate, sugar, dietary_fiber, protein, fat, starch])):
        raise MealRecordError.NutritionError(nutrition=generated_data.json())
    
    return generated_data


async def async_generate_nutrition(food_name: str, unit: int, quantity: int | float) -> FoodNutrition:
    unit_text = UNIT_MAPPING[unit]
    user_input = f"음식명: {food_name}\n섭취량: {quantity} {unit_text}"

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_input}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)

    response = response.json()["choices"][0]["message"]["content"]

    if "None" in response:
        raise MealRecordError.GenerationFailedError(food_name=food_name)
    
    json_match = re.search(r'{[\s\S]*?}', response)
    if not json_match:
        raise MealRecordError.ResponseParsingError(raw_response=response)

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

    generated_data = FoodNutrition(
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

    if any(map(lambda x: x is None or x < 0 or not isinstance(x, (int, float)), 
            [carbohydrate, sugar, dietary_fiber, protein, fat, starch])):
        raise MealRecordError.NutritionError(nutrition=generated_data.json())
    
    return generated_data
