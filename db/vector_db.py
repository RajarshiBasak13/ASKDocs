from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader, DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters.sentence_transformers import SentenceTransformer
import chromadb
import uuid
import os

class Embedding_Model:
    def __init__(self):
        self.embedding_model_name = "BAAI/bge-base-en-v1.5"
        self.model = SentenceTransformer(model_name_or_path=self.embedding_model_name)

    def generateEncoding(self, sens):
        return self.model.encode(sens, batch_size=4)


class VectorDb():
    def __init__(self, storage_path, collection_name):
        os.makedirs(storage_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=storage_path)
        # Note: Truncating the whole collection deletes EVERYONE'S data.
        # I've disabled auto-truncate in get_db to prevent accidental data loss.
        self.get_db(collection_name)

    def truncate_user_data(self, user_id):
        """Deletes only the records belonging to a specific user."""
        self.db.delete(where={"user_id": user_id})
        print(f"Truncated data for user: {user_id}")

    def get_db(self, collection_name):
        self.db = self.client.get_or_create_collection(collection_name, metadata={'desc': 'pdf'})

    def add_rows(self, embed_li, doc_chunks, user_id):
        total_chunks = len(embed_li)
        text_chunks = [doc.page_content for doc in doc_chunks]

        # Inject user_id into every chunk's metadata
        metadatas = []
        for doc in doc_chunks:
            meta = doc.metadata.copy()
            meta['user_id'] = user_id
            metadatas.append(meta)

        ids = [f"{user_id}_{uuid.uuid4().hex[:8]}_{i}" for i in range(total_chunks)]

        self.db.add(
            ids=ids,
            embeddings=embed_li.tolist(),  # Ensure it's a list for Chroma
            metadatas=metadatas,
            documents=text_chunks
        )
        print(f"Added {total_chunks} records for {user_id}. Total: {self.db.count()}")

    def get_contexts(self, embedded_queries, n_results, confidence_threshold, user_id):
        # The 'where' clause restricts results to the specific user_id
        results = self.db.query(
            query_embeddings=embedded_queries,
            n_results=n_results,
            where={"user_id": user_id}
        )

        text_chunks = results['documents'][0]
        context_li = []
        citation = []

        for i, dist in enumerate(results['distances'][0]):
            similarity = 1 - dist
            if similarity > confidence_threshold:
                context_li.append(text_chunks[i])
                metadata = results['metadatas'][0][i]

                citation.append({
                    'source': metadata.get('source', 'unknown').split("\\")[-1],
                    'page': metadata.get('page', ''),
                    'chunk': text_chunks[i],
                    'user': user_id,
                    'confidence': round(similarity, 3)
                })

        return context_li, citation


embedModel = Embedding_Model()
vectorDb = VectorDb(storage_path='./db/vector_db', collection_name='pdf_collections')


def load_data(user_id, upload_st={}, upload_key='', filename=None, custom_text=None):
    docs = []
    if filename:
        file_ext = filename.split(".")[-1]
        file_types = {'pdf': PyPDFLoader, 'txt': TextLoader}

        for file_type, load_class in file_types.items():
            if file_type == file_ext:
                loaded_docs = DirectoryLoader(
                    path=r'sources',
                    glob=f"{filename}",
                    loader_cls=load_class,
                    loader_kwargs={'encoding': 'utf-8'} if (file_type == 'txt') else None,
                    show_progress=True
                ).load()
                docs.extend(loaded_docs)

    if custom_text:
        docs.append(Document(page_content=custom_text, metadata={"source": "custom"}))

    def chunk_split(docs, chunk_size, chunk_overlap):
        chuck_obj = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=['\n\n', '\n', ' ', ''],
            add_start_index=True
        )
        return chuck_obj.split_documents(docs)

    doc_chunks = chunk_split(docs, chunk_size=500, chunk_overlap=40)

    text_li = [chunk.page_content for chunk in doc_chunks]
    embed_li = embedModel.generateEncoding(text_li)

    # Pass user_id here
    vectorDb.add_rows(embed_li, doc_chunks, user_id)

    upload_st[upload_key] = 'done'
    print(f'Data load complete for {user_id}')
