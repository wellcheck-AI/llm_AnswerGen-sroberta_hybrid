import os

import torch
import yaml
import pandas as pd
import pickle as pk

from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from typing import Literal, List, Tuple
from transformers import AutoTokenizer, AutoModel
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer

load_dotenv()
with open(os.path.join(os.path.dirname(__file__), "config", 'conf.yaml')) as f:
    config = yaml.full_load(f)

index_name = config["pinecone"]["index_name"]

def tfidf_sparse_vector(query:str, vectorizer:Literal["TfidfVectorizer"]) -> Tuple[List[int], List[float]]:
    query_tfidf = vectorizer.transform([query])

    indices = query_tfidf.nonzero()[1].tolist()
    values = query_tfidf.data.tolist()
    return indices, values

def get_document_embedding(
        document:str, 
        model:Literal["Huggingface BERT Model"],
        tok:Literal["Huggingface BERT Tokenizer"],
        max_length=512
    ) -> List[float]:
    tokens = tok.encode(document, truncation=False)
    
    if len(tokens) <= max_length - 2:
        chunk = [tok.cls_token_id] + tokens + [tok.sep_token_id]
        chunk_inputs = torch.tensor([chunk])
        
        with torch.no_grad():
            outputs = model(chunk_inputs)

        embeddings = outputs.last_hidden_state
        attention_mask = torch.ones(embeddings.size()[:-1])
        mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        pooled_embedding = torch.sum(embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)

        pooled_embedding = normalize(pooled_embedding, norm="l2")

        return pooled_embedding.reshape(-1).tolist()
    else:
        chunks = [tokens[i:i + (max_length - 2)] for i in range(0, len(tokens), max_length - 2)]
        
        chunk_embeddings = []
        
        for chunk in chunks:
            chunk = [tok.cls_token_id] + chunk + [tok.sep_token_id]
            chunk_inputs = torch.tensor([chunk])
            
            with torch.no_grad():
                outputs = model(chunk_inputs)
        
            chunk_embedding = outputs.last_hidden_state
            attention_mask = torch.ones(chunk_embedding.size()[:-1])
            mask = attention_mask.unsqueeze(-1).expand(chunk_embedding.size()).float()
            pooled_embedding = torch.sum(chunk_embedding * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
                
            chunk_embeddings.append(pooled_embedding)
        
        document_embedding = torch.mean(torch.stack(chunk_embeddings), dim=0)
        document_embedding = normalize(document_embedding, norm="l2")

        return document_embedding.reshape(-1).tolist()    # shape: [1, 768]

def get_sentence_embedding(
        query:str,
        model:Literal["Huggingface BERT Model"],
        tok:Literal["Huggingface BERT Tokenizer"],
        ) -> List[float]:
    inputs = tok(query, return_tensors="pt", padding=True, truncation=True, max_length=512)
    
    with torch.no_grad():
        outputs = model(**inputs)

    embeddings = outputs.last_hidden_state
    attention_mask = inputs["attention_mask"]
    mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()

    pooled_embedding = torch.sum(embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)

    pooled_embedding = normalize(pooled_embedding, norm="l2")

    return pooled_embedding.reshape(-1).tolist()

def build(index:Pinecone.Index) -> Tuple[AutoModel, AutoTokenizer, TfidfVectorizer]:
    filelist = os.listdir("data")
    if len(filelist) > 1:
        for i, fn in enumerate(filelist, start=1):
            print(f"{i}. {fn}")

        swt = int(input("DB에 업로드할 파일을 선택해주세요(-1 입력 시 종료): "))
        if swt == -1:
            exit()
        else:
            file_path = filelist[swt - 1]
    elif len(filelist) < 1:
        raise Exception("The file does not exist")
    else:
        file_path = filelist[0]

    file_path = os.path.join(os.path.dirname(__file__), "data", file_path)

    if file_path.endswith(".csv"):
        data = pd.read_csv(file_path)
    else:
        data = pd.read_excel(file_path)
        
    data.fillna({"답변": ""}, inplace=True)
    data = data[data["답변"] != ""]

    docs = data["답변"].values.tolist()

    model_path = "jhgan/ko-sroberta-multitask"
    model = AutoModel.from_pretrained(model_path)
    tok = AutoTokenizer.from_pretrained(model_path, clean_up_tokenization_spaces=True)

    vectorizer = TfidfVectorizer(tokenizer="korean")
    vectorizer.fit(docs)

    save_params_path = os.path.join(os.path.dirname(__file__), "config", "params", "tfidf_params.pkl")
    pk.dump(vectorizer, open(save_params_path, "wb"))

    category_col = data.columns.tolist()[1]

    for idx in tqdm(range(len(data)), total=len(data)):
        doc_id = data.iloc[idx]["번호"]
        keywords = [keyword.strip() for keyword in data.iloc[idx]["키워드"].split("#") if keyword.strip()]
        category = data.iloc[idx][category_col]
        content = data.iloc[idx]["답변"]

        metadata = {
            "text": content,
            "category": category,
            "keywords": keywords
        }

        embed_docs = get_document_embedding(document=content, model=model, tok=tok)
        sparse_vector_indices, sparse_vector_values = tfidf_sparse_vector(content, vectorizer)
        sparse_vector = {
            "indices": sparse_vector_indices,
            "values": sparse_vector_values
        }

        index.upsert(
            vectors=[{
                "id": str(doc_id),
                "values": embed_docs,
                "sparse_values": sparse_vector,
                "metadata": metadata
            }]
        )
    
    return model, tok, vectorizer

def search_test(
        query: str, 
        index: Pinecone.Index, 
        model: AutoModel, 
        tok: AutoTokenizer,
        vectorizer: TfidfVectorizer, 
        topk:int=10
    ):
    embed_query = get_sentence_embedding(query, model=model, tok=tok)

    query_sparse_vector_indices, query_sparse_vector_values = tfidf_sparse_vector(query, vectorizer)
    sparse_vector = {
        "indices": query_sparse_vector_indices,
        "values": query_sparse_vector_values
    }

    results = index.query(
        vector=embed_query,
        sparse_vector=sparse_vector,
        top_k=topk,
        include_metadata=True
    )

    matches = [
        { "id": match["id"], "score": match["score"], "content": match["metadata"]["text"] }
        for match in results['matches']
    ]

    return matches

def run() -> None:
    pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
    existing_indexes = [index["name"] for index in pc.list_indexes()]

    if index_name in existing_indexes:
        # raise Exception(f"Index {index_name} already exist!")
        pc.delete_index(index_name)

    pc.create_index(
        name=index_name,
        dimension=768,
        metric="dotproduct",
        spec=ServerlessSpec(
            cloud="aws", region="us-east-1"
        )
    )

    index = pc.Index(index_name)

    model, tok, vectorizer = build(index)

    test_query = "식후 혈당 관리는 어떻게 하는게 좋을까?"
    results = search_test(test_query, index, model, tok, vectorizer)
    print(results)

if __name__ == "__main__":
    run()