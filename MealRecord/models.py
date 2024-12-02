import os
from sqlalchemy import Column, Integer, String, DateTime, Float, UniqueConstraint
import datetime
import pytz
from .db import DATABASE_SCHEMA
from sqlalchemy.orm import declarative_base

Base = declarative_base()

kst = pytz.timezone('Asia/Seoul')

class FoodNutrition(Base):
    __tablename__ = "food_nutrition"
    
    __table_args__ = (
        UniqueConstraint('food_name', 'quantity', 'unit', name='unique_food_serving'),
        {
            'schema': DATABASE_SCHEMA, 
            'extend_existing': True,
        }
    )

    food_name = Column(String, primary_key=True, index=True)
    quantity = Column(Float, primary_key=True, nullable=False)
    unit = Column(Integer, primary_key=True, nullable=False)
    serving_size = Column(Float, nullable=False)
    carbohydrate = Column(Float)
    sugar = Column(Float)
    dietary_fiber = Column(Float)
    protein = Column(Float)
    fat = Column(Float)
    starch = Column(Float)
    call_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(kst))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(kst), onupdate=lambda: datetime.datetime.now(kst))