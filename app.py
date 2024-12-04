from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from prometheus_fastapi_instrumentator import Instrumentator

load_dotenv(override=True)


from routers.coach_assistant import router as coach_assistant_router
from routers.meal_record import router as meal_record_router
from utils.logger_setup import setup_logger

app = FastAPI(
    title="Coach Assistant Chatbot API",
    description="FastAPI로 구성된 Chatbot API",
    version="1.0",
    docs_url="/docs/"
)

logger = setup_logger("main")
logger.info("FastAPI application initialized.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coach_assistant_router, prefix="/api/coach", tags=["Chatbot API"])
app.include_router(meal_record_router, prefix="/api/gen", tags=["Generate nutritions API"])

Instrumentator().instrument(app).expose(app)