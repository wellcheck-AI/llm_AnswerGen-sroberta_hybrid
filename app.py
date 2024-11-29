#!d/usr/bin/python3 -u
import os
import json
import traceback

import openai
import pinecone

from dotenv import load_dotenv
from flask_cors import CORS
from flask import Flask, jsonify, request, make_response
from flask_restx import Api, Resource, fields

from document import Document_
from chat import Chatbot_
from exceptions import PineconeIndexNameError, PineconeUnexceptedException

# *logging
import logging
from datetime import datetime, timezone, timedelta

log_file_path = "api_requests.log"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')


class SeoulFormatter(logging.Formatter):
    def converter(self, timestamp):
        kst = timezone(timedelta(hours=9))
        dt = datetime.fromtimestamp(timestamp, tz=kst)
        return dt.timetuple()


formatter = SeoulFormatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False
CORS(app)

api = Api(
    app,
    version="1.0",
    title="API Document",
    description="Coach assistant Chatbot API Document",
    doc="/docs/",
)

ns_summary = api.namespace("summary", description="요약 API")
ns_reference = api.namespace("reference", description="참고 문서 검색 API")
ns_answer = api.namespace("answer", description="답변 생성 API")

summary_model = api.model(
    "Summary",
    {"query": fields.String(required=True, description="요약할 사용자의 질문 입력")},
)

reference_model = api.model(
    "Reference",
    {
        "query": fields.String(
            required=True,
            description="답변을 생성하기 위해 필요한 문서를 검색하기 위해 질문 입력",
        )
    },
)

answer_model = api.model(
    "Answer",
    {
        "query": fields.String(
            required=True, description="답변을 생성할 사용자의 질문 입력"
        ),
        "data": fields.List(
            fields.Raw(),
            required=True,
            description="검색된 문서의 인덱스와 내용을 리스트 형태로 입력",
        ),
    },
)

llm = Chatbot_()
document = Document_()


@ns_summary.route("/")
class Summary(Resource):
    @api.expect(summary_model)
    @api.response(200, "Success")
    @api.response(403, "Remote API server error")
    @api.response(405, "Query is required")
    @api.response(500, "Internal Server Error")
    def post(self):
        try:
            data = request.json
            query = data["query"]

            if not query.strip():
                return make_response(
                    jsonify(
                        {
                            "status_code": 405,
                            "message": "쿼리를 입력해주세요.",
                            "error": "ValueError: Empty query",
                        }
                    ),
                    405,
                )

            logger.info(f"query: {query}")
            summary = llm.summary(query)

            return jsonify(
                {
                    "status_code": 200,
                    "data": [
                        {
                            "summary": summary,
                        }
                    ],
                }
            )

        except openai.APIError as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 403,
                        "message": "현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": "OpenaiApiKeyError: Invalid OpenAI API Key",
                    }
                ),
                403,
            )

        except Exception as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 500,
                        "message": "현재 AI 질문 요약이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": f"UnexpectedError: {traceback.format_exc()}",
                    }
                ),
                403,
            )


@ns_reference.route("/")
class Reference(Resource):
    @api.expect(reference_model)
    @api.response(200, "Success")
    @api.response(204, "No relevant guide available")
    @api.response(403, "Remote API server error")
    @api.response(405, "Query is required")
    @api.response(500, "Internal Server Error")
    def post(self):
        try:
            data = request.json
            query = data["query"]

            if not query.strip():
                return make_response(
                    jsonify(
                        {
                            "status_code": 405,
                            "message": "쿼리를 입력해주세요.",
                            "error": "ValueError: Empty query",
                        }
                    ),
                    405,
                )

            context = document.find_match(query)

            if not all(list(zip(*context))[0]):
                return make_response(
                    jsonify({"status_code": 204, "date": [{"reference": []}]}), 204
                )

            reference = {"reference": []}
            for c in context:
                keywords_with_newline = [k + "\n" for k in c[1]]
                reference["reference"].append(
                    {
                        "index": c[0],
                        "keyword": keywords_with_newline,
                        "text": c[2],
                        "image_url": c[3],
                    }
                )

            return jsonify({"status_code": 200, "data": [reference]})

        except openai.APIError as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 403,
                        "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": "OpenaiApiKeyError: Invalid OpenAI API Key",
                    }
                ),
                403,
            )

        except pinecone.exceptions.PineconeApiException as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 403,
                        "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": "PineconeApiKeyError: Invalid Pinecone API Key",
                    }
                ),
                403,
            )

        except PineconeIndexNameError as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 403,
                        "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": "PineconeIndexNameError: Pinecone index does not exist",
                    }
                ),
                403,
            )

        except PineconeUnexceptedException as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 500,
                        "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": e,
                    }
                ),
                500,
            )

        except Exception as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 500,
                        "message": "현재 AI 답변 가이드 검색이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": f"UnexpectedError: {traceback.format_exc()}",
                    }
                ),
                500,
            )


# Answer 리소스 클래스 정의
@ns_answer.route("/")
class Answer(Resource):
    @api.expect(answer_model)
    @api.response(200, "Success")
    @api.response(403, "Remote API server error")
    @api.response(405, "Query is required")
    @api.response(500, "Internal Server Error")
    def post(self):
        try:
            json_data = request.json
            query = json_data["query"]
            reference_list = json_data["data"][0]["reference"]

            if not query.strip():
                return make_response(
                    jsonify(
                        {
                            "status_code": 405,
                            "message": "쿼리를 입력해주세요.",
                            "error": "ValueError: Empty query",
                        }
                    ),
                    405,
                )

            context = document.context_to_string(reference_list, query)

            if context:
                reference = context
            else:
                reference = ["참고문서는 없으니 너가 아는 정보로 대답해줘."]
            answer = llm.getConversation_prompttemplate(
                query=query, reference=reference
            )

            return jsonify({"status_code": 200, "data": [{"answer": answer}]})

        except openai.APIError as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 403,
                        "message": "현재 AI 답변 추천이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": "OpenaiApiKeyError: Invalid OpenAI API Key",
                    }
                ),
                403,
            )

        except Exception as e:
            return make_response(
                jsonify(
                    {
                        "status_code": 500,
                        "message": "현재 AI 답변 추천이 어렵습니다. 잠시 후에 다시 사용해주세요.",
                        "error": f"UnexpectedError: {traceback.format_exc()}",
                    }
                ),
                500,
            )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
