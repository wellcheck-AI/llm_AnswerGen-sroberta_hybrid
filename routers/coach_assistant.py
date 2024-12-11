import os
import uuid
import json
import traceback

from datetime import datetime

import pytz
import openai
import pinecone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from typing import List

from CoachAssistant import (
    Document_,
    Chatbot_,
    PineconeIndexNameError,
    PineconeUnexceptedException
)
from utils.log_schema import LogSchema, APIException
from utils.alert import send_discord_alert, send_discord_alert_pinecone
from utils.firebase_logger import request_log

LOGGER_NAME = "coach"

document = Document_()
llm = Chatbot_()

router = APIRouter()

@router.post("/summary/", response_model=dict)
async def summarize(request:Request):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME + ".summary")

        headers = dict(request.headers)

        x_forwarded_for = headers.get("x-forwarded-for") # 리버스 프록시 뒤에 있는 경우
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host

        request_time = datetime.now(pytz.timezone('Asia/Seoul'))
        method = "POST"

        if "content-type" in headers:
            _log_headers = {"content-type": headers["content-type"]}
        else:
            _log_headers = {}

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")

        _log.set_request_log({"query": query}, ip, method, _log_headers, request_time)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요"
            )
        
        summary = llm.summary(query)
        response_data = {"summary": summary}

        _log.set_response_log(response_data, status_code=200, message=None)
        request_log(LOGGER_NAME + ".summary", _log.get_request_log(), _log.get_reseponse_log(), _log.get_error_log())
        return {
            "status_code": 200, 
            "data": [ response_data ] 
        }
    
    except openai.APIError as e:
        raise APIException(
            code=403,
            name="OpenaiApiKeyException",
            message="현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요."
        )
    
    except APIException as e:
        e.log(_log)
        request_log(logger=LOGGER_NAME + ".summary", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=e.code,
            detail={
                "status_code": e.code,
                "message": e.message
            }
        )
        
    except Exception as e:
        _log.set_error_log("UnexpectedException", traceback=traceback.format_exc(), generated=None)
        _log.set_response_log(None, 500, "알 수 없는 오류가 발생했습니다")
        
        request_log(logger=LOGGER_NAME + ".summary", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "알 수 없는 오류가 발생했습니다"
            }
        )
    
@router.post("/reference/")
async def reference(request:Request):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME + ".reference")

        headers = dict(request.headers)

        x_forwarded_for = headers.get("x-forwarded-for") # 리버스 프록시 뒤에 있는 경우
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host

        request_time = datetime.now(pytz.timezone('Asia/Seoul'))
        method = "POST"

        if "content-type" in headers:
            _log_headers = {"content-type": headers["content-type"]}
        else:
            _log_headers = {}

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")

        _log.set_request_log({"query": query}, ip, method, _log_headers, request_time)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요"
            )
        
        context = document.find_match(query)

        if not all(list(zip(*context))[0]):
            _log.set_response_log(None, 204, "쿼리와 관련된 문서가 없습니다")
            request_log(LOGGER_NAME + ".reference", _log.get_request_log(), _log.get_reseponse_log(), _log.get_error_log())
            return Response(status_code=204)
        
        reference = { "reference": [] }
        for c in context:
            keywords_with_newline = [k + '\n' for k in c[1]] 
            reference["reference"].append({
                "index": c[0],
                "keyword": keywords_with_newline,  
                "text": c[2],
                "image_url": c[3]
            })

        resposne_data = reference

        _log.set_response_log(resposne_data, 200, None)
        request_log(LOGGER_NAME + ".reference", _log.get_request_log(), _log.get_reseponse_log(), _log.get_error_log())
        return { 
            "status_code": 200,    
            "data": [ resposne_data ]
        }

    except openai.APIError as e:
        send_discord_alert(str(e))
        raise APIException(
            code=403,
            name="OpenaiApiKeyError",
            message="현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )
    
    except pinecone.exceptions.PineconeApiException as e:
        send_discord_alert_pinecone(str(e))
        raise APIException(
            code=403,
            name="PineconeApiKeyError",
            message="현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )

    except PineconeIndexNameError as e:
        send_discord_alert_pinecone(str(e))
        raise APIException(
            code=403,
            name="PineconeIndexNameError",
            message="현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )
    
    except PineconeUnexceptedException as e:
        send_discord_alert_pinecone(str(e))
        raise APIException(
            code=500,
            name="PineconeUnexceptedException",
            message="현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )
    
    except APIException as e:
        e.log(_log)
        request_log(logger=LOGGER_NAME + ".reference", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=e.code,
            detail={
                "code": e.code,
                "message": e.message
            }
        )
    
    except Exception as e:
        _log.set_error_log("UnexpectedException", traceback=traceback.format_exc(), generated=None)
        _log.set_response_log(None, 500, "알 수 없는 오류가 발생했습니다")
        
        request_log(logger=LOGGER_NAME, request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요."
            }
        )

@router.post("/answer/")
async def answer(request: Request):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME + ".answer")

        headers = dict(request.headers)

        x_forwarded_for = headers.get("x-forwarded-for") # 리버스 프록시 뒤에 있는 경우
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host

        request_time = datetime.now(pytz.timezone('Asia/Seoul'))
        method = "POST"

        if "content-type" in headers:
            _log_headers = {"content-type": headers["content-type"]}
        else:
            _log_headers = {}

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")
        
        _log.set_request_log({"query": query}, ip, method, _log_headers, request_time)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요"
            )
        
        try:
            reference_list = body.get("data")[0]["reference"]
            context = document.context_to_string(reference_list, query)
        except Exception as e:
            raise APIException(
                code=405,
                name="InvalidInputException",
                message=f"잘못된 reference 입력입니다.\n{body}",
                traceback=traceback.format_exc()
            )

        if not context:
            context = ["참고문서는 없으니 너가 아는 정보로 대답해줘."]
        
        answer = llm.getConversation_prompttemplate(query=query, reference=context)
        response_data = {"answer": answer}
        
        _log.set_response_log(response_data, status_code=200, message=None)
        request_log(LOGGER_NAME + ".answer", _log.get_request_log(), _log.get_reseponse_log(), _log.get_error_log())
        
        return { 
            "status_code": 200,
            "data": [ response_data ] 
        }

    except openai.APIError as e:
        raise APIException(
            code=403,
            name="OpenaiApiKeyError",
            message="현재 AI 답변 추천이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )
    
    except APIException as e:
        e.log(_log)
        request_log(logger=LOGGER_NAME + ".answer", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=e.code,
            detail={
                "status_code": e.code,
                "message": e.message
            }
        )
    
    except Exception as e:
        _log.set_error_log("UnexpectedException", traceback=traceback.format_exc(), generated=None)
        _log.set_response_log(None, 500, "알 수 없는 오류가 발생했습니다")
        
        request_log(logger=LOGGER_NAME + ".answer", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "알 수 없는 오류가 발생했습니다"
            }
        )