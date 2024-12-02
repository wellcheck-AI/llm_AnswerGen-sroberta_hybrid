import os
import traceback

import openai
import pinecone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import List, Dict

from CoachAssistant import (
    Document_,
    Chatbot_,
    PineconeIndexNameError,
    PineconeUnexceptedException
)
from logger_setup import setup_logger

logger = setup_logger("coach_assistant_logger", "coach_assistant.log")

document = Document_()
llm = Chatbot_()

router = APIRouter()

class SummaryRequest(BaseModel):
    query: str

class ReferenceRequest(BaseModel):
    query: str

class ReferenceData(BaseModel):
    index: str
    keyword: List[str]
    text: str

    def __str__(self):
        return self.text

class AnswerRequest(BaseModel):
    query: str
    data: List[dict]


@router.post("/summary/", response_model=dict)
async def summarize(request:SummaryRequest):
    try:
        query = request.query
        
        if not query.strip():
            logger.warning("Empty query received in /summary")
            raise HTTPException(
                status_code=405,
                detail={
                    "status_code": 405,
                    "error": "ValueError: Empty query",
                    "message": "쿼리를 입력해주세요."
                }
            )
        
        logger.info(f"Summary | Input Query | {query}")
        
        summary = llm.summary(query)

        return {
            "status_code": 200, 
            "data": [ { "summary": summary } ] 
        }
    
    except openai.APIError as e:
        logger.error(f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}")
        raise HTTPException(
            status_code=403,
            detail={
                "status_code": 403,
                "message": "현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}"
            }
        )

    except Exception as e:
        logger.error(f"UnexpectedError in /summary: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"UnexpectedError in /summary: {e}"
            }
        )
    
@router.post("/reference/")
async def reference(request:ReferenceRequest):
    try:
        query = request.query
        
        if not query.strip():
            logger.warning("Empty query received in /reference")
            raise HTTPException(
                status_code=405,
                detail={
                    "status_code": 405,
                    "error": "ValueError: Empty query",
                    "message": "쿼리를 입력해주세요."
                }
            )
        
        context = document.find_match(query)

        if not all(list(zip(*context))[0]):
            logger.info(f"No relevant documents found for query: {query}")
            return Response(status_code=204)
        
        reference = { "reference": [] }
        for c in context:
            keywords_with_newline = [k + '\n' for k in c[1]] 
            reference["reference"].append({
                "index": c[0],
                "keyword": keywords_with_newline,  
                "text": c[2],
            })

        return { 
            "status_code": 200,    
            "data": [ reference ]
        }

    except openai.APIError as e:
        logger.error(f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}")
        raise HTTPException(
            status_code=403,
            detail={
                "status_code": 403,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}"
            }
        )
    
    except pinecone.exceptions.PineconeApiException as e:
        logger.error(f"PineconeApiKeyError: Invalid Pinecone API Key: {os.environ.get('PINECONE_API_KEY')}")
        raise HTTPException(
            status_code=403,
            detail={
                "status_code": 403,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"PineconeApiKeyError: Invalid Pinecone API Key: {os.environ.get('PINECONE_API_KEY')}"
            }
        )

    except PineconeIndexNameError as e:
        logger.error(f"PineconeIndexNameError: Pinecone index does not exist.")
        raise HTTPException(
            status_code=403,
            detail={
                "status_code": 403,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"PineconeIndexNameError: Pinecone index does not exist."
            }
        )
    
    except PineconeUnexceptedException as e:
        logger.error(f"PineconeUnexpectedError: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"PineconeUnexpectedError: {e}"
            }
        )

    except Exception as e:
        logger.error(f"UnexpectedError in /reference: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"UnexpectedError in /reference: {e}"
            }
        )

@router.post("/answer/")
async def answer(request: AnswerRequest):
    try:
        query = request.query
        reference_list = request.data[0]["reference"]
        
        if not query.strip():
            logger.warning("Empty query received in /reference")
            raise HTTPException(
                status_code=405,
                detail={
                    "status_code": 405,
                    "error": "ValueError: Empty query",
                    "message": "쿼리를 입력해주세요."
                }
            )
        
        # reference_list = [str(ref) for ref in reference_list]
        context = document.context_to_string(reference_list, query)

        if not context:
            context = ["참고문서는 없으니 너가 아는 정보로 대답해줘."]
        
        answer = llm.getConversation_prompttemplate(query=query, reference=context)

        return { 
            "status_code": 200,
            "data": [ { "answer": answer } ] 
        }

    except openai.APIError as e:
        logger.error(f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}")
        raise HTTPException(
            status_code=403,
            detail={
                "status_code": 403,
                "message": "현재 AI 답변 추천이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"OpenaiApiKeyError: Invalid OpenAI API Key: {os.environ.get('OPENAI_API_KEY')}"
            }
        )
    
    except Exception as e:
        logger.error(f"UnexpectedError in /answer: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                "error": f"UnexpectedError in /answer: {e}"
            }
        )