import os
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from utils.config_hander import chroma_config
from utils.path_tool import get_abs_path
from utils.model_factory import chat_model,embedding_model
from utils.log import logger
from utils.file_hander import txt_loader,pdf_loader,list_dir_with_allow_type,get_file_md5
class KnowledgeService:
    def __init__(self):
        self.vector_store=Chroma(
            collection_name=chroma_config['collection_name'],
            embedding_function=embedding_model,
            persist_directory=get_abs_path(chroma_config['persist_path'])
        )
        self.spliter=RecursiveCharacterTextSplitter(
            separators=chroma_config['seperators'],
            chunk_size=chroma_config['chunk_size'],
            chunk_overlap=chroma_config['chunk_overlap']
        )
    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={'k':chroma_config['topk']})
    
    def load_doc(self):
        def check_md5(md5_str:str):
            if not os.path.exists(get_abs_path(chroma_config['md5_data_path'])):
                # 创建
                open(get_abs_path(chroma_config['md5_data_path']),'w',encoding='utf-8').close()
                return False
            with open(get_abs_path(chroma_config['md5_data_path']),'r',encoding='utf-8') as f:
                for line in f.readlines():
                    if md5_str==line.strip():
                        return True
            return False

        def save_md5(md5_str:str):
            with open(get_abs_path(chroma_config['md5_data_path']),'a',encoding='utf-8') as f:
                f.write(md5_str+'\n')
            return
        
        def file_to_doc(file_path:str):
            if file_path.endswith('.txt'):
                return txt_loader(file_path)
            elif file_path.endswith('.pdf'):
                return pdf_loader(file_path)
            return []
        
        allowed_files_path=list_dir_with_allow_type(get_abs_path(chroma_config['data_path']),tuple(chroma_config['allow_knowledge_file_type']))

        for path in allowed_files_path:
            md5_hex=get_file_md5(path)
            if check_md5(md5_hex):
                logger.info('[加载知识库]'+path+'已经存在知识库中')
                continue

            try:
                documents:list[Document]=file_to_doc(path)
                if not documents:
                    logger.warning('[加载知识库]'+path+'文件内无有效信息')
                    continue
                split_doc:list[Document]=self.spliter.split_documents(documents)
                if not split_doc:continue
                
                
                self.vector_store.add_documents(split_doc)
                save_md5(md5_hex)
                logger.info('[加载知识库]'+path+'成功加载进知识库中')
            except Exception as e:
                logger.error('[加载知识库]'+path+'加载失败,'+str(e),exc_info=True)
            

        return