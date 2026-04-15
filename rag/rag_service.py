from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from rag.knowledge_service import KnowledgeService
from utils.prompt_loader import rag_summarize
from utils.model_factory import chat_model

class RagSummarizeService:
    def __init__(self):
        self.vecotr_store=KnowledgeService()
        self.retriver=self.vecotr_store.get_retriever()
        self.prompt_text=rag_summarize
        self.prompt_template=PromptTemplate.from_template(self.prompt_text)
        self.model=chat_model
        self.chain=self._init_chain()
        return
    def _init_chain(self):
        def print_prompt(prompt):
            print('='*20)
            print(prompt.to_string())
            print('='*20)
            return prompt
        
        chain=self.prompt_template | print_prompt | self.model | StrOutputParser()
    
        return chain
    
    def rag_summarize(self,quary:str):
        context_doc:list[Document]=self.retriver.invoke(quary)
        
        context=''
        counter=0
        for doc in context_doc:
            counter+=1
            context+='\n[参考资料'+str(counter)+']:'+doc.page_content+'\n[参考元数据]'+str(doc.metadata)+'\n'
        return self.chain.invoke(
            {
                'input': quary,
                'context': context
            }
        )