# -*- coding: utf-8 -*-
import os
import re
from dotenv import load_dotenv
from openai import OpenAI as summaryai
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

load_dotenv()

class Chatbot_:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4o", 
            openai_api_key=os.environ['OPENAI_API_KEY'], 
            temperature=0.1,
            max_tokens=500,
            frequency_penalty=0.25, # 반복 감소, 다양성 증가. (0-1)
            presence_penalty=0,  # 새로운 단어 사용 장려. (0-1)
            top_p=0              # 상위 P% 토큰만 고려 (0-1)
        )

    def getConversation_prompttemplate(self, query, reference):
        # 프롬프트 템플릿 설정
        system_message_content = """
        당신은 헬스케어 상담사입니다. CONTEXT를 기반으로 Query에 대해 핵심 내용을 먼저 제공한 후, 간결하고 부드럽게 답변해 주세요. 답변은 최대 350자 이하로 작성해 주세요.

        답변 작성 시 다음 단계를 따르세요:
        1. Query가 불명확할 경우, "질문을 이해하기 어렵습니다. 추가 정보를 포함해 다시 질문해 주실 수 있을까요?"라고 답해 주세요.
        2. CONTEXT만으로 Query에 대한 답변이 가능한 경우 추가 지침을 참고해서 답변이 가능하면 제공해 주세요.
        3. CONTEXT가 비어있거나 연관된 내용이 없는 경우, Query에 기본적인 지식으로 답변이 가능하면 사실만을 추가 지침에 맞게 대답하고, 맨 앞에 "관련 정보가 없으므로 기본적인 지식으로 답변드리겠습니다.\n"라고 추가해 주세요.
        4. 그 외 추가 정보 없이 질문에 대답하기 어려운 개인적인 질문이나 마음 건강에 관련해서는, "이 질문은 추가 개인 정보 없이는 답변 드리기 어렵습니다. 다시 질문해 주실 수 있을까요?"라고 답해 주세요.

        추가 지침:
        - CONTEXT가 있다면 Query와 관련된 정보를 두괄식으로 제공한 후, 간결한 설명을 덧붙여 주세요.
        - CONTEXT가 있다면 그 말투를 참고하고 없다면 전문가스럽지만 부드럽고 친근한 말투로 답변해 주세요. (예시: 끝맺음에 "~있어요", "~좋아요" 등을 적절히 섞어 사용)
        - 강한 어조로 단호하게 말하지 않고 문법적으로 정확한 한국어를 사용해 주세요.
        - 글자 수 제한을 엄격히 지켜 350자를 초과하지 않도록 해 주세요.
        - 마지막으로 질문에 맞는 답변이 명확하게 전달되었는지 확인해 주세요. 필요하다면 핵심 내용을 유지하면서 말투를 유지해주세요.

        금지 표현:
        - 저칼로리, 고단백, 저지방, 저염과 같은 표현 사용을 피하세요.
        - 고칼로리, 저단백, 고지방, 고염 등의 표현으로 명사화하는 것도 지양하세요.
        - "고" 또는 "저"와 같은 접두사를 사용하여 영양 성분을 명사화하는 방식도 피하세요.
        - 특정 영양 성분만 강조하지 않도록 주의하여 균형 잡힌 정보를 제공하세요.
        """

        # 메시지 리스트 생성
        messages = [
            SystemMessage(content=system_message_content),
            HumanMessage(content=f"Query: {query}\nCONTEXT: {reference}"),
        ]
        # OpenAI API 호출
        response = self.llm.invoke(messages)
        return response.content
    
    def summary(self, query):
        client = summaryai(
            api_key= os.environ['OPENAI_API_KEY'],
        )
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f'''
                        사용자의 질문을 읽고, 질문의 요지를 최대 2줄 이내로 간략하게 요약해 주세요.

                        - 질문의 핵심이 하나인 경우: 질문의 요지를 간결하게 한 두줄로 사용자가 말한 내용에 집중하여 요약해 주세요.
                        - 질문에 여러 가지 궁금증이 포함된 경우: 각 궁금증을 최대 2줄 이내로 요약하여 설명해 주세요.
                        - 사용자의 의견이나 경험을 강조하고, 궁금증을 명확하게 드러내어 핵심 정보만 짧은 말투로 추출해 주세요.

                        질문을 요약할 때 고려할 점:
                        - 사용자가 무엇을 알고 싶어 하는지 명확히 이해해 주세요.
                        - 사용자의 변화나 선호, 상황을 간단히 설명해 주세요.
                        - 사용자가 질문을 통해 얻고자 하는 구체적인 정보나 도움을 드러내 주세요.

                        형식:
                        - 요지: [의견과 궁금증을 포함한 간단한 질문에 대한 요약]
                    '''
                },
                {
                    "role": "user",
                    "content": f'''질문: {query}\n요약: ''',
                },
            ],
            model="gpt-4o",
        )

        summary = chat_completion.choices[0].message.content
        summary = re.sub("-?\ ?요(약|지)\ ?:", "", summary).strip()
        return summary
    
    def summary_add_guid(self, query):
        client = summaryai(
            api_key= os.environ['OPENAI_API_KEY'],
        )
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": f'''
                    사용자의 질문을 읽고, 질문의 요지를 최대 2줄 이내로 간략하게 요약하세요.
                    
                    - 질문의 핵심이 하나인 경우: 요지를 한 줄로 간단히 제공하세요.
                    - 질문에 여러 궁금증이 포함된 경우: 각 포인트를 최대 2줄 이내로 요약하세요.
                    
                    답변 흐름은 다음과 같이 안내하세요:
                    - **기본 원인 설명y**: 질문에 대한 일반적인 원인을 간단히 설명하세요.
                    - **상세 원인 제공**: 추가로 고려해야 할 특정 상황이나 원인을 설명하세요.
                            
                            형식:
                            · 요지: [간단한 한 줄 요약 또는 각 포인트 요약 (최대 2줄)]
                            · 가이드: [답변 흐름에 대한 간략한 단계별 가이드(최대 2줄)]
                '''},
                {
                    "role": "user",
                    "content": f'''질문: {query}\n요약: ''',
                },
            ],
            model="gpt-4o",
        )

        summary = chat_completion.choices[0].message.content
        return summary