from openai import OpenAI
import os

# 外部独立工具函数
def get_prompt(texts: list[str]) -> str:
    '''通过提示词，使得大模型输出格式化'''
    return f"""请严格输出标准SRT字幕，只返回字幕内容，无多余文字：
1. 序号从1递增
2. 时间格式 00:00:00,000 --> 00:00:05,000
文案：{texts}"""

def llm_inference(client: OpenAI, model: str, prompt: str) -> str:
    '''调用大模型'''
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()

def save_llm_result(srt_path: str, content: str):
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(content)

def gen_video(in_path: str, out_path: str, srt_path: str):
    '''生成视频字幕'''
    print(f"FFmpeg开始处理：{in_path}")
    srt_path = os.path.abspath(srt_path)
    in_path = os.path.abspath(in_path)
    out_path = os.path.abspath(out_path)
    res = os.system(f'ffmpeg -i "{in_path}" -i "{srt_path}" -c:v copy -c:a copy -c:s mov_text "{out_path}" -y')
    assert res == 0
    print(f"成功输出：{out_path}")


class SubtitleAgent:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.in_video = "src.mp4"
        self.out_video = "sub_out.mp4"
        self.srt_path = "sub.srt"
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def run(self, text_list: list[str]) -> str:
        prompt = get_prompt(text_list)
        llm_result = llm_inference(self._client, self.model, prompt)
        save_llm_result(self.srt_path, llm_result)
        gen_video(self.in_video, self.out_video, self.srt_path)
        return self.out_video