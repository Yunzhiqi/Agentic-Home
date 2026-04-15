import yaml
from utils.path_tool import get_abs_path


def load_config(config_path: str, encoding: str="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)



rag_config = load_config(config_path=get_abs_path("config/rag.yml"))
chroma_config = load_config(config_path=get_abs_path("config/chroma.yml"))
prompts_config = load_config(config_path=get_abs_path("config/prompts.yml"))
agent_config = load_config(config_path=get_abs_path("config/agent.yml"))
system_config = load_config(config_path=get_abs_path("config/system.yml"))


if __name__ == '__main__':
    print(rag_config["chat_model_name"])
