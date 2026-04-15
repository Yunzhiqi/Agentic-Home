from langchain_community.embeddings import DashScopeEmbeddings
from langchain_openai import ChatOpenAI
from utils.config_hander import rag_config

class EmbeddingModelFactory():
    def generator(self):
        return DashScopeEmbeddings(model=rag_config['embbeding_fun_name'])
    
class ChatModelFactory():
    def generator(self):
        return ChatOpenAI(model=rag_config['chat_model_name'],base_url='https://api.deepseek.com/v1')
    

    
chat_model=ChatModelFactory().generator()
embedding_model=EmbeddingModelFactory().generator()