import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
    PromptTemplate,
    MessagesPlaceholder
)

# .env 파일 로드
load_dotenv()

class Chatbot_:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name="gpt-4o", 
            openai_api_key=os.environ['OPENAI_API_KEY'], 
            temperature=0.1,
            max_tokens=500,
            frequency_penalty=1.0, # 반복 감소, 다양성 증가. (0-1)
            presence_penalty=0,  # 새로운 단어 사용 장려. (0-1)
            top_p=0              # 상위 P% 토큰만 고려 (0-1)
        )
        self.mention = " 해당 질문은 챗봇이 답변하기 어렵습니다. 코치님께 전달드려 답변드리도록 하겠습니다."
        
        system_msg_template = SystemMessagePromptTemplate.from_template(
        template=f"""당신은 헬스케어 상담사입니다.
반드시 CONTEXT의 내용을 참고하여 답변하라.

1. 사용자의 질문을 이해하기 위해 CoT 방식을 이용하라.
2. 답변을 작성할 때 ToT 방식을 사용하라.
3. 답변을 작성할 때 사용자의 정보가 필요한 질문에는 원인을 유추하지 말고 "~한 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?" 와 같이 답하라: (예시: "혈압이 오른 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?", "소화가 잘 안되는 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?")
4. CONTEXT만으로 답변을 생성할 수 없고, 답변을 작성할 때 사용자의 정보가 필요하다면 "~한 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?" 와 같이 답하라: (예시: "혈압이 오른 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?", "소화가 잘 안되는 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?")
5. 이전 답변에서 "~한 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?"와 같이 답변했다면, 사용자가 정보를 제공했을 것이다. 사용자가 제공한 정보와 CONTEXT로 답변할 수 없다면 다음과 같이 답하라: {self.mention}
6. CONTEXT가 비어있다면, 다음과 같이 답하라: {self.mention}
7. 사용자의 질문에 CONTEXT만 이용하여 답변을 할 수 있는지 판단하라.
8. CONTEXT만으로 답변을 생성할 수 없다면 다음과 같이 답변: {self.mention}
9. 질문에 대한 답을 모르겠다면 다음과 같이 답변: {self.mention}
10. CONTEXT의 키워드와 가이드만으로 답변을 할 수 있다면, 문법적으로 올바른 한국어 문장으로 답변하라.
11. 절대 CONTEXT에 없는 정보를 추가하지 마라.
12. 전문가와 상담하라는 말을 하지 마라.
13. 답변 작성 후 문장 단위로 CONTEXT와 일치하는지 다시 한 번 검토하라.
14. 각 답변을 작성할 때마다 위의 지침을 체크리스트로 활용하여 모든 조건을 만족하는지 확인하라.
        """ 
)

        human_msg_template = HumanMessagePromptTemplate.from_template(template="{input}")
        self.prompt_template = ChatPromptTemplate.from_messages([system_msg_template, MessagesPlaceholder(variable_name="history"), human_msg_template])

    def getConversation_chatprompttemplate(self,memory,lang='kor'):
        if lang == 'kor':
            return ConversationChain(memory=memory,
                                    prompt=self.prompt_template,
                                    llm=self.llm,
                                    verbose=False)
        elif lang == 'en':
            system_msg_template_en = SystemMessagePromptTemplate.from_template(template= f"""You are a healthcare counselor.
Be sure to answer by referring to the contents of CONTEXT.

1. Use the CoT method to understand the user's questions.
2. Use the ToT method when writing your answers.
3. For questions that require user's information when writing your answers, do not deduce the cause. Answer: "There could be many reasons. Could you give me additional information that you expect?" (Example: "There could be many reasons why your blood pressure has risen. Could you give me additional information that you expect?" and "There could be many reasons why you have indigestion. Could you give me additional information that you expect?")
4. If CONTEXT alone cannot produce an answer and you need user's information when writing one, respond with, "There could be a number of reasons. Could you give me additional information that you expect?" (Example: "There could be a number of reasons why blood pressure has risen. Could you give me additional information that you expect?" and "There could be a number of reasons why your have indigestion. Could you give me additional information that you expect?")
5. If the previous answer was answered with "~There can be many reasons. Can you give me the additional information you expect?" the user would have provided the information. If you cannot answer with CONTEXT with the information provided by the user, answer as follows: {self.mention}
6. If CONTEXT is empty, answer: {self.mention}
7. Determine if the user's questions can be answered using only CONTEXT.
8. If CONTEXT alone cannot generate an answer: {self.mention}
9. If you don't know the answer to your question: {self.mention}
10. If you can answer only with keywords and guides from CONTEXT, answer with grammatically correct Korean sentences.
11. Never add information that is not in CONTEXT.
12. Don't tell me to consult a professional.
13. Write your answers and review again to see if they match CONTEXT on a sentence-by-sentence basis.
14. Whenever you write each answer, use the above instructions as a checklist to make sure you meet all the conditions.
        """ )
            human_msg_template_en = HumanMessagePromptTemplate.from_template(template="{input}")
            prompt_template_en = ChatPromptTemplate.from_messages([system_msg_template_en, MessagesPlaceholder(variable_name="history"), human_msg_template_en])

            return ConversationChain(memory=memory,
                                    prompt=prompt_template_en,
                                    llm=self.llm,
                                    verbose=False)
    
    def getConversation_prompttemplate(self, memory):


        template="""
당신은 헬스케어 상담사입니다.
반드시 아래의 지침에 따라 답변하라.

0. 사용자의 질문을 이해하기 위해 CoT 방식을 이용하라.
1. 답변을 작성할 때 ToT 방식을 사용하라.
2. 답변을 작성할 때 사용자의 개인 정보가 필요한 질문(예시: 혈압, 체중 변화, 특정 증상, 질병, 복용 중인 약물, 식습관, 운동 습관, 정신 건강 상태 등 건강 관련 질문)인지 판단하라.
3. 사용자의 정보가 필요한 질문에서는 원인을 유추하지 말고 "~한 이유는 여러 가지가 있을 수 있어요. 예상하시는 추가정보를 주실 수 있을까요?"라고 요청하라.
4. CONTEXT와 제공된 정보만으로 충분히 답변이 가능하다면, 추가 정보 요청 없이 직접 답변하라.
5. 절대 반복해서 추가 정보를 요청하지마라. CONTEXT와 사용자 제공 정보만으로 답변이 불가능하면 "해당 질문은 챗봇이 답변하기 어렵습니다. 코치님께 전달드려 답변드리도록 하겠습니다."라고 답하라.
6. CONTEXT가 비어있다면, "해당 질문은 챗봇이 답변하기 어렵습니다. 코치님께 전달드려 답변드리도록 하겠습니다."라고 답하라.
7. 질문에 대한 답을 모를 때도 동일하게 "해당 질문은 챗봇이 답변하기 어렵습니다. 코치님께 전달드려 답변드리도록 하겠습니다."라고 답하라.
8. CONTEXT에 없는 정보를 추가하지 말고, 전문가와 상담하라는 말도 피하라.
9. 답변 작성 후 문장 단위로 CONTEXT와 일치하는지 검토하라.
10. 모든 지침을 체크리스트로 활용하여 답변의 적합성을 확인하라.
11. 각 문장이 CONTEXT와 일치하는지에 대해 언급하지 말고, 문법적으로 올바른 한국어 문장으로 답변하라.


Chat History
{history}

User Input:
{input}
        """    
        prompt = PromptTemplate(template=template, input_variables=["history","input"])
        return ConversationChain(prompt=prompt,
                                    llm=self.llm,
                                    verbose=True,
                                    memory=memory,
)
    def predict(self):
        pass