import os
import torch
import yaml
import pickle as pk

from pinecone import Pinecone
from typing import List, Tuple
from konlpy.tag import Mecab
from transformers import AutoTokenizer, AutoModel
from sklearn.preprocessing import normalize

from CoachAssistant.utils import query_refiner

with open(os.path.join(os.path.dirname(__file__), "config", 'conf.yaml')) as f:
    config = yaml.full_load(f)

pc = Pinecone()
index = pc.Index(config["pinecone"]["index_name"])

model = AutoModel.from_pretrained(config["embedding_model"]["model_path"])
tok = AutoTokenizer.from_pretrained(config["embedding_model"]["model_path"], clean_up_tokenization_spaces=True)

vectorizer = pk.load(open(os.path.join(os.path.dirname(__file__), "config", "params", "tfidf_params.pkl"), "rb"))


class Document_:
    def __init__(self):
        pass
    
    def _sentence_embedding(self, query:str) -> List[float]:
        inputs = tok(query, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        embeddings = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"]
        mask = attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
        mean_pooling_embedding = torch.sum(embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)

        mean_pooling_embedding = normalize(mean_pooling_embedding, norm="l2")

        return mean_pooling_embedding.reshape(-1).tolist()

    def _tfidf_sparse_vector(self, query:str) -> Tuple[List[int], List[float]]:
        query_tfidf = vectorizer.transform([query])

        indices = query_tfidf.nonzero()[1].tolist()
        values = query_tfidf.data.tolist()
        return {
            "indices": indices,
            "values": values
        }

    def context_to_string(self, contexts, query):
        context = '\n'.join(contexts)
        if len(context) > 2000:
            context = context[:2000]
        if (len(context + query)) > 2500:
            context = context[:2500 - len(query)]
        return context

    def query_refine(self, query):
        return query_refiner(query)
    
    def find_match(self, query):
        embed_query = self._sentence_embedding(query=query)
        sparse_vector = self._tfidf_sparse_vector(query=query)

        if sparse_vector["indices"]:
            result = index.query(
                vector=embed_query,
                sparse_vector=sparse_vector,
                top_k=10, 
                include_metadata=True
            )

            threshold = 0.25
        else:
            result = index.query(
                vector=embed_query,
                top_k=10, 
                include_metadata=True
            )

            threshold = 0.3

        result.matches.sort(key=lambda x: x.score, reverse=True)

        ref_list = []
        for res in result.matches:
            r = []
            if res.score >= threshold:
                reference_id = res['id']

                keywords = res["metadata"]["keywords"]
                answer = res["metadata"]["text"]
                image_url = res["metadata"]["url"]

                r = [reference_id, keywords, answer, image_url]

            else:
                reference_id = None
                r = [reference_id, [], []]

            ref_list.append(r)

        return ref_list