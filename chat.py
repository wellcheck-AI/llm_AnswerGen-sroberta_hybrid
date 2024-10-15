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
        당신은 헬스케어 상담사입니다. CONTEXT를 기반으로 QUERY에 대해 핵심 내용을 먼저 제공한 후, 간결하고 부드럽게 답변해 주세요. 답변은 최대 500자 이하로 작성해 주세요.

        답변 작성 시 다음 단계를 따르세요:
        1. QUERY가 불명확할 경우: "질문을 이해하기 어렵습니다. 추가 정보를 포함해 다시 질문해 주실 수 있을까요?"라고 답해 주세요.
        2. CONTEXT만으로 QUERY에 대한 답변이 가능한 경우: 내용 지침, 말투 지침, 금지 표현을 참고하여 일관된 말투로 답변을 제공하세요.
        3. CONTEXT가 비어 있거나 연관된 내용이 없을 경우: 기본적인 지식으로 답변이 가능하면 사실만을 포함해 답변해 주세요. 내용 지침과 금지 표현을 준수하고 말투 지침을 참고하여 일관된 말투로 답변하세요.
        4. 추가 정보 없이 답변하기 어려운 개인적 질문이나 정신 건강 관련 질문에는: "이 질문은 추가 개인 정보 없이는 답변 드리기 어렵습니다. 정보를 추가해서 질문해 주실 수 있을까요?"라고 답해 주세요.

        내용 지침:
        1. CONTEXT가 포함된 경우, 해당 문서의 주요 정보를 우선 제공하며, 추가적인 도움이 될 만한 관련 정보가 있다면 부가적으로 덧붙여 주세요.
        2. 식품이나 영양소 관련 질문의 경우, 일반 정의 대신 CONTEXT에서 제공되는 추천 정보에 따라 답변해 주세요.
        3. 최대한 간결하고 정확한 한국어를 사용해 주세요.
        4. 답변이 200자보다 짧다면 질문에 유용할 수 있는 부가 정보를 포함하여 자연스럽게 확장해 주세요.

        말투 지침:
        1. CONTEXT의 말투를 참고하되, 없을 경우에는 전문가스럽고 친근한 말투로 답변해 주세요. 예시: "~이 있어요", "~하시면 좋을 것 같아요", "~을 추천드려요" 등.
        2. 질문자의 말을 통해 건강 관리를 위한 노력이나 행동, 목표가 있는 경우에는 간단히 칭찬하고 격려하는 문구를 한줄 포함하세요. 
        3. 이모지 대신 따뜻한 인사와 감정을 담은 표현을 활용해 답변을 부드럽게 전달해 주세요. (느낌표, 감탄사, 칭찬 등 활용)
        4. 말투가 자연스럽도록 답변의 흐름을 잘 검토하고 자연스럽게 이어지도록 하세요.

        금지 표현:
        1. 저칼로리, 고단백, 저지방, 저염과 같은 표현 사용을 피하세요.
        2. 고칼로리, 저단백, 고지방, 고염 등의 표현으로 명사화하는 것도 지양하세요.
        3. "고" 또는 "저"와 같은 접두사를 사용하여 영양 성분을 명사화하는 방식도 피하세요.
        3. "고" 또는 "저"와 같은 접두사를 사용하여 영양 성분을 명사화하는 방식도 피하세요.
        4. 특정 영양 성분만 강조하지 않도록 주의하여 균형 잡힌 정보를 제공하세요.
        5. "전문가," "전문의," "의료진" 등의 상담을 권유하는 문구를 사용하지 마세요.
        6. CONTEXT와 비교하여 답변하거나, "CONTEXT에 따르면 ~" 등으로 시작하는 표현을 사용하지 마세요. CONTEXT는 참고 자료로만 사용하며, 답변에서는 질문에만 집중하세요.
        """

        # 메시지 리스트 생성
        messages = [
            SystemMessage(content=system_message_content),
            HumanMessage(content=f"QUERY: {query}\nCONTEXT: {reference}"),
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
                        당신은 상담사를 지원하는 어시스턴트로서, 사용자의 질문을 읽고 질문의 요지를 최대 두 줄 이내로 간단히 요약해야 합니다. 
                        질문이 명확하지 않아도 최대한 이해한 내용을 설명해 주세요. 단, 질문에 불명확한 단어가 있어 의미 파악이 어려운 경우, 해당 단어를 그대로 사용하여 답변하세요. 
                        예를 들어, 사용자가 "./"라고 입력했으면 "./에 대한 질문"으로 표시합니다.
                        절대 질문을 이해하기 어렵습니다. 다시 질문해 주실 수 있을까요?와 같은 답변이나 물음표로 질문하지 마세요.
 
                        요약 방식:
                        - 질문의 핵심이 하나인 경우: 사용자의 말을 바탕으로 한 두 줄 이내로 간결하게 요약합니다.
                        - 여러 궁금증이 포함된 경우: 각 궁금증을 두 줄 내외로 요약해 설명합니다.
                        - 사용자의 의견과 경험을 강조하여 궁금증을 명확히 드러내고, 핵심 정보를 짧게 요약합니다.

                        요약 시 참고 사항:
                        - 사용자가 무엇을 알고 싶어 하는지 파악합니다.
                        - 사용자의 변화, 선호, 상황을 간단히 포함합니다.
                        - 사용자가 원하는 구체적인 정보나 도움을 중심으로 요약합니다.

                        형식:
                        - 요지: [의견과 궁금증을 포함한 간단한 질문 요약]

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
    
    