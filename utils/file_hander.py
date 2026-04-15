import os,hashlib
import chardet
from utils.log import logger
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader,TextLoader

def get_file_md5(filepath:str):
    if not os.path.exists(filepath):
        logger.error('[md5]文件路径'+filepath+'不存在')
        return
    elif not os.path.isfile(filepath):
        logger.error('[md5]路径'+filepath+'不是文件')
        return
    md5_obj=hashlib.md5()
    chnuk_size=4096
    try:
        with open(filepath,'rb') as f:
            while chunk:=f.read(chnuk_size):
                md5_obj.update(chunk)
            md5_hex=md5_obj.hexdigest()
            return md5_hex 
    except Exception as e:
        logger.error('[md5]计算'+filepath+'md5失败,'+str(e))
        return None

def list_dir_with_allow_type(path:str,allow_type:tuple[str]):
    ans=[]
    if not os.path.isdir(path):
        logger.error('[文件遍历]路径'+path+'不是文件夹')
    for file in os.listdir(path):
        if file.endswith(allow_type):
            ans.append(os.path.join(path,file))
    return tuple(ans)


def pdf_loader(file_path:str,pwd=None)->list[Document]:
    return PyPDFLoader(file_path,password=pwd).load()
def txt_loader(filepath:str)->list[Document]:
    with open(filepath, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result['encoding']
    return TextLoader(filepath,encoding=encoding).load()