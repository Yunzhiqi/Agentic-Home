import os

def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def get_abs_path(relative_path:str):
    return os.path.join(get_project_root(),relative_path)
    
# print(get_abs_path('test.txt'))