from utils.config_hander import prompts_config
from utils.path_tool import get_abs_path
from utils.log import logger

def load_prompts(prompt_type:str):
    try:
        path=get_abs_path(prompts_config[prompt_type])
    except KeyError as e:
        logger.error('[load_prompt]未找到'+prompt_type+'配置项')
        raise e
    
    try:
        return open(path,'r',encoding='utf-8').read()
    except Exception as e:
        logger.error('[load_prompt]解析'+prompt_type+'提示词时出错,'+str(e))
        raise e
    
system_prompt=load_prompts('system_prompt_path')
rag_summarize=load_prompts('rag_summarize_path')
report_prompt=load_prompts('report_prompt_path')
frontend_prompt=load_prompts('frontend_prompt_path')
iot_backend_prompt=load_prompts('iot_backend_prompt_path')
