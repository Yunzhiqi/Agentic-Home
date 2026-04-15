# from utils import config_hander
# print(config_hander.rag_config['chat_model_name'])

# from utils import prompt_loader
# print(prompt_loader.report_prompt+'\n'+prompt_loader.system_prompt)

# from rag.knowledge_service import KnowledgeService
# test=KnowledgeService()
# test.load_doc()
# retriver=test.get_retriever()
# res=retriver.invoke('迷路')
# for r in res:
#     print(r.page_content)
#     print('='*20)

# from rag.rag_service import RagSummarizeService
# test=RagSummarizeService()
# print(test.rag_summarize('小户型适合什么扫地机器人'))

# from agent.tools.agent_tools import external_data,generate_external_data
# generate_external_data()
# print(external_data)

# from agent.react_agent import ReactAgent
# test_agent=ReactAgent()
# for chunk in test_agent.execute_stream("给我生成我的使用报告"):
#     print(chunk, end="", flush=True)

