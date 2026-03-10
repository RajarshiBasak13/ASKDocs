import numpy as np
import pandas as pd
import os
import sys
from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader, DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters.sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import uuid
from sklearn.metrics.pairwise import cosine_similarity
from langchain_groq import ChatGroq
import dotenv
dotenv.load_dotenv()

class Embedding_Model:
    def __init__(self):
        self.embedding_model_name = "BAAI/bge-base-en-v1.5"
        self.model = SentenceTransformer(model_name_or_path=self.embedding_model_name)
    def generateEncoding(self, sens):
        return self.model.encode(sens)


class VectorDb():

    def __init__(self, storage_path,collection_name):
        self.client = chromadb.PersistentClient(path=storage_path)
        self.get_db(collection_name)

    def truncate_db(self, collection_name):
        print("in truncate DB")
        if(self.client.list_collections() and self.client.list_collections()[0].name==collection_name):
            print("truncate22222")
            ids = self.client.get_collection(collection_name).get(include=[]).get("ids", [])
            if ids:
                self.client.get_collection(collection_name).delete(ids=ids)

    def get_db(self,collection_name,truncate=True):
        if truncate:
            self.truncate_db(collection_name)
        self.db = self.client.get_or_create_collection(collection_name,metadata={'desc':'pdf'})

    def add_rows(self,embed_li, doc_chunks):
        total_chunks = len(embed_li)
        text_chunks = [doc.page_content for doc in doc_chunks]
        metadata = [doc.metadata for doc in doc_chunks]
        ids = [f"doc_{uuid.uuid4().hex[:8]}_{i}" for i in range(total_chunks)]
        self.db.add(ids=ids,
                    embeddings=embed_li,
                    metadatas=metadata,
                    documents=text_chunks)
        print("Total record added->",self.db.count())
    
    def get_contexts(self,embedded_queries,n_results,confidence_thresold):
        results = self.db.query(query_embeddings=embedded_queries,n_results=n_results)
        text_chunks = results['documents'][0]
        context_st = ''
        citation = []
        for i, dist in enumerate(results['distances'][0]):
            similarity = 1-dist
            if similarity>confidence_thresold:
                context_st += '/n/n' + text_chunks[i]
                metadata = results['metadatas'][0][i]
                start_index = metadata['start_index']
                source = metadata['source'].split("\\")[-1]
                page = metadata.get('page','')
                confidence = similarity
                tmp = dict()
                tmp['source'] = source
                tmp['page'] = page
                tmp['chunk'] = text_chunks[i]
                citation.append(tmp)


        return context_st, citation
    

embedModel = Embedding_Model()
vectorDb = VectorDb(storage_path='../vector_db',collection_name='pdf_collections')

def load_data(filename=None,custom_text=None):
    docs=[]
    if filename:
        ### LOAD Data
        file_ext = filename.split(".")[-1]

        file_types = {'pdf':PyPDFLoader, 'txt':TextLoader}
        for file_type, load_class in file_types.items():
            if(file_type==file_ext):
                docs.extend(DirectoryLoader(path=r'sources',
                                glob=f"{filename}",
                                loader_cls=load_class,
                                loader_kwargs={'encoding':'utf-8'} if (file_type=='txt') else None,
                                show_progress=True).load())
    if custom_text:
        docs.append(Document(page_content=custom_text,metadata={"source":"custom"}))
    print(len(docs))

    ### Split Data in Chunks
    def chunk_split(docs,chunk_size,chunk_overlap):
        chuck_obj = RecursiveCharacterTextSplitter(chunk_size=chunk_size, 
                                                chunk_overlap=chunk_overlap, 
                                                separators=['\n\n','\n','',' '],
                                                add_start_index=True)
        return chuck_obj.split_documents(docs)
    doc_chunks = chunk_split(docs,chunk_size=1000, chunk_overlap=200)
    for i in doc_chunks:
        print(len(i.page_content),end=" ")

    ### Embed Chunks
    text_li = [chunk.page_content for chunk in doc_chunks]
    embed_li = embedModel.generateEncoding(text_li)

    vectorDb.add_rows(embed_li, doc_chunks)


#load_data()
def get_answer(prompt):
    embedded_prompt = embedModel.generateEncoding([prompt])[0]
    contexts, citation = vectorDb.get_contexts(embedded_prompt,5,0.1)
    print("contexts",len(contexts))

    ### Run Model
    if len(contexts)==0:
        return "Sorry, We couldnt find answer using the source given by you!", []
    api = os.getenv('GROQ_API_KEY')
    query = f"""Using the following context only, answer the question correctly.
                    context={contexts}
                    question={prompt}
                    answer="""
    model = ChatGroq(model='llama-3.1-8b-instant',temperature=0.1,max_tokens=1024,api_key=api)
    return model.invoke([query]).content, citation
