import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import uvicorn

# 1. 初始化 FastAPI
app = FastAPI()

# 2. 加载 Moondream 模型
# 你可以使用本地路径，比如 "./moondream2"，或者直接用 HuggingFace 的 repo 名
model_path = "vikhyatk/moondream2" 
print(f"正在加载模型 {model_path} 到显存...")

# Moondream 需要 trust_remote_code=True
tokenizer = AutoTokenizer.from_pretrained(model_path, revision="2024-08-26")
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    trust_remote_code=True, 
    revision="2024-08-26",
    torch_dtype=torch.float16, # 使用半精度节省显存
    device_map="auto"
).eval()

class CommandQuery(BaseModel):
    text: str

@app.post("/parse_command")
async def parse_command(query: CommandQuery):
    try:
        # 3. 构造针对导航任务的提示词
        # 强烈建议 Moondream 使用英文 Prompt 以获得最佳的逻辑推理能力
        prompt = (
            "You are a robot assistant. Available locations are: main_gate, northwest_gate, building_4, building_7, building_5.\n"
            f"User command: '{query.text}'\n"
            "Extract the destination location name from the user command. Output ONLY the English location name without any punctuation. If no match is found, output 'unknown'."
        )

        # 构造 Moondream 最适应的问答格式
        formatted_prompt = f"Question: {prompt}\n\nAnswer:"

        # 处理输入
        inputs = tokenizer(formatted_prompt, return_tensors="pt").to("cuda")

        # 4. 执行推理生成
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=16)
            
        # 解码结果
        # 生成的结果会包含输入的 Prompt，我们需要把它去掉
        output_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
        
        # 5. 提取模型回复的内容
        if "Answer:" in output_text:
            final_result = output_text.split("Answer:")[-1].strip().lower()
        else:
            final_result = output_text.replace(formatted_prompt, "").strip().lower()

        # 简单清理一下可能的标点符号
        final_result = final_result.strip(".,!?\"'")

        print(f"指令: '{query.text}' -> 解析结果: {final_result}")
        return {"target": final_result}

    except Exception as e:
        print(f"推理发生错误: {e}") # 在服务端终端打印具体错误
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)