import os
from typing import List
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 로드
load_dotenv()

# OpenAI 초기화
client = OpenAI()

# 키워드 tokenizer 초기화 (현재는 사용하지 않으나 이후 하이브리드 써치 반영시 업데이트)
# tokenizer = BertTokenizerFast.from_pretrained('klue/bert-base')

def hybrid_scale(dense, sparse, alpha: float):
    # alpha 값이 0과 1 사이인지 확인
    if alpha < 0 or alpha > 1:
        raise ValueError("Alpha must be between 0 and 1")
    # 각 희소 벡터의 값에 (1 - alpha)를 적용하여 가중치 조정
    hsparse = {
        'indices': sparse['indices'],
        'values':  [v * (1 - alpha) for v in sparse['values']]
    }
    hdense = [v * alpha for v in dense]
    return hdense, hsparse

def query_refiner(query):
    response = client.completions.create(model="gpt-3.5-turbo-instruct",
                                         prompt=f"""Please clarify user's query.
                                         Query: {query}
                                         Never answer, just refine the user's query.
                                         Refined query:""",
    temperature=0.1,
    max_tokens=256,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0)
    return response.choices[0].text

# def build_dict(input):
#     # sparse embedding을 저장할 딕셔너리
#     sparse_emb = []
    
#     # 입력 배치를 순회
#     for token_ids in input:
#         # token_ids의 빈도수를 계산하여 딕셔너리로 변환
#         token_count = dict(Counter(token_ids))

#         # 인덱스와 값 저장
#         indices = list(token_count.keys())
#         values = [float(count) for count in token_count.values()]

#         # 인덱스와 값을 가진 sparse embedding 생성
#         sparse_emb = {'indices': indices, 'values': values}
    
#     # sparse embedding 반환
#     return sparse_emb

# def generate_sparse_vectors(context_batch):
#     # 입력 텍스트를 token_ids로 변환
#     inputs = tokenizer(
#         context_batch, 
#         padding=True,
#         truncation=True,
#         max_length=512
#     )['input_ids']

#     # sparse embedding 딕셔너리 생성
#     sparse_embeds = build_dict([inputs])

#     return sparse_embeds
