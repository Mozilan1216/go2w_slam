import requests
import base64
import json  # 🔥 补上了这个致命的 import！

# 1. 读取现实世界的彩色照片
try:
    with open("test.jpeg", "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
except FileNotFoundError:
    print("❌ 找不到 test.jpeg，请检查路径！")
    exit()

# 2. 发给 Moondream 的请求数据
payload = {
    "model": "moondream",
    # 顺应它的天性，直接要 bounding box
    "prompt": "You are a coordinate detector. Locate the door in the image. Return ONLY a valid JSON object containing the bounding box with keys 'x', 'y', 'w', 'h'.",
    "images": [base64_image],
    "stream": False,
    "format": "json",
    "options": {
        "temperature": 0.0
    }
}

print("🧠 正在呼叫 Moondream 大模型，请稍候...")

# 3. 跨越 Docker 次元壁调用
try:
    response = requests.post("http://127.0.0.1:11434/api/generate", json=payload)
    if response.status_code == 200:
        result = response.json()
        print("\n🐶 机器狗看到的原始答案：", result['response'])
        
        # 4. JSON 解析与真实像素计算
        try:
            box_data = json.loads(result['response'])
            
            # 假设你的 D435i 彩色图分辨率是 640 x 480 (你可以根据实际情况修改)
            IMG_WIDTH = 640
            IMG_HEIGHT = 480
            
            # 提取归一化坐标
            norm_x = box_data.get('x', 0)
            norm_y = box_data.get('y', 0)
            
            # 转换为实际像素中心点 (u, v)
            u = int(norm_x * IMG_WIDTH)
            v = int(norm_y * IMG_HEIGHT)
            
            print(f"🎯 成功提取并解算！目标中心点像素坐标：(u={u}, v={v})")
            print("接下来可以直接拿着这个 (u,v) 去查深度图里的 Z 值了！")
            
        except json.JSONDecodeError:
            print("⚠️ 警告：JSON 解析失败。")
    else:
        print(f"❌ 请求失败，状态码：{response.status_code}")
except Exception as e:
    print(f"❌ 程序发生错误：{e}")