from transformers import AutoTokenizer, AutoModel
import gradio as gr
from pathlib import Path
import re
import pandas as pd

# 加载模型
model = AutoModel.from_pretrained("/chatglm3-6b", trust_remote_code=True).to("mps").eval()
tokenizer = AutoTokenizer.from_pretrained("/chatglm3-6b", trust_remote_code=True)



def read_tbl_2_pd(filename):
    if filename.endswith('.csv'):
        df = pd.read_csv(filename)
    elif filename.endswith('.xlsx') or filename.endswith('.xls'):
        pd.read_excel(filename, sheet_name=None)
    return df

def fn_analysis_table(query, robot,  filename):


    if robot is None:
        robot = []
    robot.append([query, " "])
    
    if filename.endswith('.csv'):
        schema = pd.read_csv(filename).columns
    elif filename.endswith('.xlsx') or filename.endswith('.xls'):
        schema = pd.read_excel(filename, sheet_name=None)['Sheet1'].columns
    
    
    chat_history = []
    
    prompt = f"已知文件:{filename}\n\n文件Schema:{schema}\n\n问题:{query}\n\n请利用Pandas生成Python代码解决这个问题，把最后的结果赋值给变量result\n\ndPython代码:\n\n"
    
    print(prompt)
    
    response, history = model.chat(tokenizer, prompt, history=[])
    print(response)
    
    pat = re.compile(r'```python\n([\s\S]+)\n```')
    code_string = pat.findall(response)[0]
    print(code_string)


    loc = {}
    exec(code_string, None, loc)
    result = loc['result']    
    
    response, history = model.chat(tokenizer, f'result:{result}', history=history, role='observation')
    
    robot[-1] = [query, response]
    yield robot



with gr.Blocks() as app:

    with gr.Tab("与CSV对话"):

         with gr.Row():

            with gr.Column(scale=1):
                upload = gr.File(label="上传csv文档")
                df = gr.Dataframe()

                chatbot = gr.Chatbot(
                    label="ChatBot",
                    height=500,
                    bubble_full_width=False
                )
                instruction = gr.Textbox(lines=2, label="请输入您的问题", placeholder="问题...", max_lines=2)
                with gr.Row():
                    submit = gr.Button("提交", size="sm",interactive=True)
                    clean = gr.Button("清除", size="sm")
   
             
            upload.upload(fn=read_tbl_2_pd, inputs=[upload], outputs=[df], queue=False)
            
            submit.click(
                fn=fn_analysis_table,
                inputs=[instruction, chatbot,  upload],
                outputs=[chatbot],
                queue=True
                
            )
            clean.click(fn=lambda: None, inputs=None, outputs=chatbot, queue=False)
app.queue(max_size=3)
app.launch(share=False)
