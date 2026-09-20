#!/usr/bin/env python3
"""NPU üzerinde çalışan, OpenAI uyumlu küçük LLM sunucusu.
   python server.py test  -> modeli yüklemeden öz-kontrol"""
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HOME = os.path.expanduser("~/.local/share/ai-npu")
MODEL = os.environ.get("AI_NPU_MODEL", f"{HOME}/models/qwen25-coder-npu")
DEVICE = os.environ.get("AI_NPU_DEVICE", "NPU")

SYSTEM = ("You are a terminal assistant on Ubuntu 22.04. Answer in the user's language. "
          "Be brief. When a shell command is the answer, give the command first, "
          "then at most one short line explaining it. Prefer ss over netstat, "
          "systemctl --user for user services, and never suggest deleting or "
          "overwriting anything that was not explicitly asked about.")

FENCE = re.compile(r"^[ \t]*```\w*[ \t]*$\n?", re.M)


def clean(text):
    """Terminalde markdown çiti okunmaz; çit satırlarını at, içeriğe dokunma."""
    return FENCE.sub("", text).strip()


LIMIT = 900 if DEVICE == "NPU" else 0   # token; 0 = sinir yok (CPU dinamik sekil)


def fit(text):
    """NPU'nun statik istem siniri var; sigana kadar bastan kirp."""
    while LIMIT and len(tok.encode(text).input_ids.data[0]) > LIMIT:
        text = text[len(text) // 4:]
    return text


def build_prompt(messages):
    msgs = [dict(m) for m in messages]
    if msgs and msgs[-1].get("role") == "user":
        msgs[-1]["content"] = fit(msgs[-1]["content"])
    if not any(m.get("role") == "system" for m in msgs):
        msgs = [{"role": "system", "content": SYSTEM}] + msgs
    return tok.apply_chat_template(msgs, True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        cfg = og.GenerationConfig()
        cfg.max_new_tokens = int(body.get("max_tokens") or 400)
        cfg.do_sample = False
        text = clean(str(pipe.generate(build_prompt(body.get("messages", [])), cfg)))
        data = json.dumps({
            "choices": [{"message": {"role": "assistant", "content": text},
                         "finish_reason": "stop", "index": 0}],
            "model": os.path.basename(MODEL), "object": "chat.completion"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def selftest():
    assert clean("```bash\ndf -h\n```") == "df -h"
    assert clean("df -h") == "df -h"
    assert clean("önce:\n```\nls\n```\nsonra") == "önce:\nls\nsonra"
    assert clean("echo ```") == "echo ```"        # satır ortasındaki çite dokunma
    print("öz-kontrol geçti")


if __name__ == "__main__":
    if sys.argv[1:2] == ["test"]:
        selftest()
        sys.exit()
    print(f"model derleniyor ({DEVICE})... ilk açılışta uzun sürer", file=sys.stderr, flush=True)
    import openvino_genai as og
    # statik sekil ayari NPU'ya ozel; CPU reddediyor ve zaten istem siniri yok
    kw = {"MAX_PROMPT_LEN": 1024, "MIN_RESPONSE_LEN": 128} if DEVICE == "NPU" else {}
    pipe = og.LLMPipeline(MODEL, DEVICE, CACHE_DIR=f"{HOME}/cache/{DEVICE}", **kw)
    tok = pipe.get_tokenizer()
    print("hazır", file=sys.stderr, flush=True)
    HTTPServer(("127.0.0.1", 11435), Handler).serve_forever()
