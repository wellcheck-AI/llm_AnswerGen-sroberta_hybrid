import os
import uuid
import json
import traceback

from datetime import datetime

import pytz
import openai
import pinecone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from typing import List

from CoachAssistant import (
    Document_,
    Chatbot_,
    PineconeIndexNameError,
    PineconeUnexceptedException
)
from utils.log_schema import LogSchema, APIException, log_custom_error
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

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")

        _log.set_request_log({"query": query}, request)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요",
                traceback=log_custom_error()
            )
        
        summary = llm.summary(query)
        response_data = {"summary": summary}

        try:
            _log.set_response_log(response_data, status_code=200, message="")
            return JSONResponse(status_code=200, content={"status_code": 200, "data": [response_data]})
        except:
            raise APIException(
                code=500,
                name="UnexpectedException",
                message="알 수 없는 오류가 발생했습니다",
                gpt_output=summary,
                traceback=traceback.format_exc()
            )
    
    except openai.APIError as e:
        raise APIException(
            code=403,
            name="OpenaiApiKeyException",
            message="현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요."
        )
    
    except APIException as e:
        e.log(_log)

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

        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "알 수 없는 오류가 발생했습니다"
            }
        )
    
    finally:
        try:
            request_log(logger=LOGGER_NAME + ".summary", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        except Exception as log_exception:
            pass
    
@router.post("/reference/")
async def reference(request:Request):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME + ".reference")

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")

        _log.set_request_log({"query": query}, request)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요",
                traceback=log_custom_error()
            )
        
        context = document.find_match(query)

        if not all(list(zip(*context))[0]):
            _log.set_response_log(None, 204, "쿼리와 관련된 문서가 없습니다")
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

        try:
            _log.set_response_log(resposne_data, 200, None)
            return JSONResponse(status_code=200, content={"status_code": 200, "data": [resposne_data]})
        except:
            raise APIException(
                code=500,
                name="UnexpectedException",
                message="결과 반환 중 알 수 없는 오류가 발생했습니다",
                gpt_output=resposne_data,
                traceback=traceback.format_exc()
            )

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

        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요."
            }
        )
    
    finally:
        try:
            request_log(LOGGER_NAME + ".reference", _log.get_request_log(), _log.get_reseponse_log(), _log.get_error_log())
        except Exception as log_exception:
            pass

@router.post("/answer/")
async def answer(request: Request):
    try:
        _log = LogSchema(_id=str(uuid.uuid4()), logger=LOGGER_NAME + ".answer")

        raw_body = await request.body()
        body_str = raw_body.decode()

        body = json.loads(body_str)

        query = body.get("query")
        
        _log.set_request_log({"query": query}, request)
        
        if not query.strip():
            raise APIException(
                code=405,
                name="InvalidInputException",
                message="쿼리를 입력해주세요",
                traceback=log_custom_error()
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
        
        try:
            _log.set_response_log(response_data, status_code=200, message=None)
            return JSONResponse(status_code=200, content={"status_code": 200, "data": [response_data]})
        except:
            raise APIException(
                code=500,
                name="UnexpectedError",
                message="결과 반환 중 알 수 없는 오류가 발생했습니다",
                gpt_output=answer,
                traceback=traceback.format_exc()
            )

    except openai.APIError as e:
        raise APIException(
            code=403,
            name="OpenaiApiKeyError",
            message="현재 AI 답변 추천이 어렵습니다. 잠시 후에 다시 사용해주세요.",
            traceback=traceback.format_exc()
        )
    
    except APIException as e:
        e.log(_log)

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

        raise HTTPException(
            status_code=500,
            detail={
                "status_code": 500,
                "message": "알 수 없는 오류가 발생했습니다"
            }
        )

    finally:
        try:
            request_log(logger=LOGGER_NAME + ".answer", request_data=_log.get_request_log(), response_data=_log.get_reseponse_log(), error=_log.get_error_log())
        except Exception as log_exception:
            pass