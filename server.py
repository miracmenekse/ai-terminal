#!/usr/bin/env python3
"""NPU üzerinde çalışan, OpenAI uyumlu küçük LLM sunucusu.
   python server.py test  -> modeli yüklemeden öz-kontrol"""
import json, os, random, re, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HOME = os.path.expanduser("~/.local/share/ai-npu")
MODEL = os.environ.get("AI_NPU_MODEL", f"{HOME}/models/qwen25-coder-npu")
DEVICE = os.environ.get("AI_NPU_DEVICE", "NPU")
_L = {"tr": "ALWAYS answer in Turkish.", "en": "ALWAYS answer in English."}
DIL = _L.get(os.environ.get("AI_NPU_LANG", "auto"),
             "Answer in the same language the user wrote in.")

SYSTEM = ("You are a terminal assistant on Ubuntu 22.04. " + DIL + " "
          "Be brief. A request to install something means the install command itself "
          "(sudo apt install X), never just the name of the program. "
          "When a shell command is the answer, give the command first, "
          "then at most one short line explaining it. If the user pastes command "
          "output, answer their question about that specific output, using its actual "
          "numbers; do not explain what the command does. "
          "If the user says your previous command failed, do NOT repeat it: read their "
          "error text and either give a different command or tell them which command "
          "would show the cause. "
          "This machine: Intel Core Ultra 7 255H with Intel integrated graphics, NO NVIDIA "
          "GPU (never suggest nvidia-smi); audio runs on PipeWire, not PulseAudio. "
          "Never invent package or command names; if unsure, first give a command that "
          "checks (apt search, command -v). gpu-izle already exists here and shows iGPU usage. "
          "If the user names a program you do not genuinely recognise, do NOT accept their "
          "premise that it exists, even when the question takes it for granted ('how do I "
          "configure X', 'how do I update X', 'how do I remove X', 'where are X's settings'). Never describe what such a program is or "
          "does, not even approximately, and never give an install command for it. Say plainly "
          "that you do not know that name and give one command that checks (command -v X, "
          "apt search X). Guessing here is worse than useless: the user cannot tell you guessed. "
          "systemctl --user is only for services in ~/.config/systemd/user; system "
          "services like bluetooth, NetworkManager or ssh need sudo systemctl, and "
          "sudo must never be combined with --user. Prefer ss over netstat, and never "
          "suggest deleting or overwriting anything that was not explicitly asked about.")

# Her istemin sonuna eklenir: istemci kendi talimatini gonderse bile gecerli kalsin.
# (Bu kural once sadece SYSTEM'de vardi; boru modunda istemcinin talimati onu eziyordu.)
EXEC_SYS = (
    "You are a Linux shell expert on Ubuntu 22.04. Reply with ONE shell command and nothing "
    "else: no explanation, no markdown, no backticks. Act on the current directory unless a "
    "path is given; never invent placeholder paths. A request to install something means the "
    "install command, not running the program. Examples: "
    "'vlc kur' -> sudo apt install -y vlc ; "
    "'docker kur' -> sudo apt install -y docker.io ; "
    "'8080 portunu hangi program dinliyor' -> sudo ss -tulnp | grep :8080 ; "
    "'ai-npu kullanici servisinin loglari' -> journalctl --user -u ai-npu -n 50 . "
    "This machine: Intel Core Ultra 7 255H with Intel integrated graphics, NO NVIDIA "
    "GPU (never suggest nvidia-smi); audio runs on PipeWire, not PulseAudio. "
    "Never invent package or command names. If you are not sure a tool exists, give a "
    "command that checks first (apt search ..., command -v ...). Tools already installed "
    "here: intel_gpu_top and gpu-izle (iGPU usage), ss, journalctl, pactl, wpctl, rfkill, "
    "bluetoothctl, nmcli, docker. For GPU usage the answer is gpu-izle, not an apt install. "
    "systemctl --user and journalctl --user are for services under ~/.config/systemd/user; "
    "everything else needs sudo systemctl.")

PIPE_SYS = (
    "The user pasted real command output. Answer their question about THAT output in Turkish, "
    "citing its actual numbers. Do not output a shell command and do not explain what the "
    "command does.")

# Surekli oturum: model komut mu cevap mi verecegine kendisi karar verir.
# Calistirilacak komutu ilk satira "$ " ile isaretler; istemci sadece o isaretliyi
# calistirmayi teklif eder. Isaret yoksa duz cevaptir, onay sorulmaz.
OTURUM_SYS = (
    SYSTEM +
    " IMPORTANT: if the user asks you to DO something that a shell command performs, "
    "put that single command on the FIRST line prefixed with '$ ' and nothing else on "
    "that line; one short explanation line may follow. If the user asks a question, "
    "chats, or wants an explanation, just answer normally and NEVER use the '$ ' prefix. "
    "Examples: 'disk doluluk oranini goster' -> '$ df -h'. 'napiyorsun' -> a short "
    "friendly answer with no command. 'chmod 755 ne demek' -> an explanation, no command. "
    "NOTHING TO RUN: if what the user asks for is not something this computer holds or a "
    "shell can produce (their to-do list, daily tasks, calendar, notes, e-mail, messages, "
    "the news, the weather, what they did yesterday), then there is NO command for it. "
    "Say plainly, in one or two sentences, that this information is not on the machine and "
    "you cannot fetch it, and emit NO '$ ' line at all. A loosely related command such as "
    "'$ ls -la' is not an answer: the user will run it, learn nothing, and trust you less. "
    "Saying 'bende böyle bir bilgi yok' is the correct, complete answer. Only suggest a "
    "command when running it would actually produce what was asked for. "
    "DIAGNOSIS LOOP: the user is not a Linux expert, so YOU do the diagnosing, not them. "
    "When they report a problem (no sound, no microphone, wifi down, a program will not "
    "start), do not ask them what they already tried and do not dump a list of steps: give "
    "ONE read-only command that inspects the problem, prefixed with '$ '. You will then be "
    "sent its output as a message starting with 'Komut ciktisi'. Read that output and reply "
    "with EITHER a plain-language verdict naming the cause and what to do, OR, if it is still "
    "not clear, the next single inspecting command with '$ '. Never repeat a command that was "
    "already run in this conversation; if its output did not settle the question, inspect "
    "somewhere else. Prefer the compact form of an inspection command, because long output "
    "gets truncated before you see it: 'wpctl status' or 'pactl list sources short' not "
    "'pactl list sources'; 'systemctl status X --no-pager -n 20' not plain status; pipe "
    "through grep or head when a command is known to be verbose. Inspect before you change anything: only propose a command that modifies "
    "the system once the output has shown the cause, and say in one line what it will change. "
    "Never propose a program that takes over the terminal and waits (bluetoothctl with no "
    "subcommand, htop, nano, watch, ssh): in this loop use its one-shot form instead, e.g. "
    "'bluetoothctl devices' or 'bluetoothctl show'. "
    "TOOLS THAT EXIST ON THIS MACHINE, use these exact ones: audio -> wpctl status, "
    "pactl info, pactl list sources short, pactl list sinks short; bluetooth -> rfkill list, "
    "bluetoothctl devices, systemctl status bluetooth --no-pager; wifi and network -> nmcli "
    "device status, nmcli device wifi list, ip -brief addr (iwconfig and iwlist are NOT "
    "installed, never suggest them); services -> ai-npu is a USER service so it is "
    "'systemctl --user status ai-npu --no-pager' and 'journalctl --user -u ai-npu -n 30', "
    "while bluetooth, NetworkManager and ssh are system services needing sudo systemctl. "
    "CONVERGE (diagnosis only): when you are diagnosing a problem you get at most 3 "
    "inspection commands. By the third output you MUST stop inspecting and give a "
    "plain-language verdict, even an incomplete one, saying what the output showed and "
    "what you could not determine. Looping without a verdict is a failure. This 3-command "
    "limit is about INSPECTING, never about a task: a task takes as many steps as it takes. "
    "TASKS: when the user asks you to DO something rather than report a problem, first "
    "work out every part the request contains, then carry them out. Steps that belong "
    "together go in ONE command joined with && (mkdir -p logs && mv *.log logs/); do not "
    "split a working command into separate turns. Before you say a task is finished you MUST run one command that "
    "shows its end state (ls, cat, git status, git log) and read that output. "
    "NEVER state that something was created, moved, written or configured unless a "
    "command output you were actually shown proves it: saying 'done' for a step you "
    "did not run is the worst failure there is. If a step failed, say which one failed "
    "and fix that step; do not summarise the whole task as successful. "
    "After you fix the cause of a command that failed, RUN THAT SAME COMMAND AGAIN. "
    "Fixing the cause is not the same as completing the step: 'git commit' failing with "
    "'Author identity unknown', then 'git config user.email', still leaves you with no "
    "commit until you run 'git commit' once more. "
    "WRITING A FILE: only the single line after '$ ' is sent to the shell, so a heredoc "
    "(cat > f << EOF) can never work here, its body would be lost. Write the file with one "
    "echo per line in a single command, using SINGLE quotes so nothing is expanded: "
    "echo '#!/bin/sh' > yedekle.sh && echo 'tar -czf notlar-$(date +%F).tar.gz notlar' >> "
    "yedekle.sh && chmod +x yedekle.sh "
    "The first echo uses > and every later one uses >>. Do not use printf for this: printf "
    "eats % signs and silently produces a broken script. "
    "Then run the script and check its result with a separate command.")

MODLAR = {"exec": EXEC_SYS, "pipe": PIPE_SYS, "oturum": OTURUM_SYS}

SAFETY = (" Safety rules, these always apply: give only the safest fix and only one; "
          "never suggest deleting system files such as lock files, caches or anything "
          "under /var, /etc or /usr; never suggest rebooting or reinstalling as a fix; "
          "never delete or overwrite anything the user did not ask about. If the "
          "information you were given does not show the cause, say which command would "
          "show it instead of guessing. Never invent package or command names."
          " LANGUAGE, this overrides everything above and is the last word: " + DIL +
          " These instructions are in English; your answer is not.")

FENCE = re.compile(r"^[ \t]*```\w*[ \t]*$\n?", re.M)

# Dusunen modeller akil yurutmeyi cevabin onune koyuyor: Qwen3/LFM <think>...</think>,
# gpt-oss harmony ise "analysis...assistantfinal...". Terminalde ikisi de okunmaz.
# Kapanis etiketi yoksa (butce bitti) elde cevap yok demektir; o zaman dokunma ki
# kullanici bos ekran yerine ham ciktiyi gorsun.
DUSUNCE = re.compile(r"\A\s*(?:<think>.*?</think>|analysis.*?assistantfinal)\s*", re.S)

# Modelin urettigi metinde geri donusu olmayan komutlari isaretle. Engellemiyorum,
# uyariyorum: karar kullanicinin, ama farkinda olmadan uygulamasin.
RISKLI = re.compile(r"""
      \brm\s+(-\w+\s+)*(/|~|\$HOME|/var|/etc|/usr|/lib|/boot)   # sistem yolu silme
    | \brm\s+-\w*[rf]                                          # rm -rf / -f
    | \bmkfs\b | \bfdisk\b | \bparted\b
    | \bdd\s+[^\n]*\bof=/dev/
    | >\s*/dev/(sd|nvme)
    | \bchmod\s+-R\s+777
    | \b(reboot|shutdown|halt|poweroff)\b
    | \bapt\b[^\n]*\b(remove|purge)\b
    | \bdpkg\s+--(purge|force)
    | :\(\)\s*\{                                              # fork bomb
""", re.X | re.I)


def clean(text):
    """Terminalde markdown çiti ve düşünce bloğu okunmaz; ikisini at, içeriğe dokunma."""
    return FENCE.sub("", DUSUNCE.sub("", text)).strip()


LIMIT = 900 if DEVICE == "NPU" else 0   # token; 0 = sinir yok (CPU/GPU dinamik sekil)


def fit(text):
    """NPU'nun statik istem siniri var; sigana kadar bastan kirp."""
    while LIMIT and len(tok.encode(text).input_ids.data[0]) > LIMIT:
        text = text[len(text) // 4:]
    return text


def build_prompt(messages, mode=None):
    msgs = [dict(m) for m in messages]
    if msgs and msgs[-1].get("role") == "user":
        msgs[-1]["content"] = fit(msgs[-1]["content"])
    if not any(m.get("role") == "system" for m in msgs):
        msgs = [{"role": "system", "content": MODLAR.get(mode, SYSTEM)}] + msgs
    for m in msgs:
        if m.get("role") == "system":
            m["content"] = m["content"] + SAFETY
    return tok.apply_chat_template(msgs, True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/v1/models"):
            self.reply({"object": "list", "data": [{"id": os.path.basename(MODEL),
                                                    "object": "model", "owned_by": DEVICE}],
                        "system": SYSTEM})
            return
        # Sayfayi her istekte diskten okuyorum: duzenleyince sunucuyu yeniden baslatma
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat.html"), "rb") as f:
            self.send_bytes(f.read(), "text/html; charset=utf-8")

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        cfg = og.GenerationConfig()
        cfg.max_new_tokens = int(body.get("max_tokens") or 400)
        temp = float(body.get("temperature") or 0)
        cfg.do_sample = temp > 0          # 0 = her zaman ayni cevap
        if cfg.do_sample:
            cfg.temperature = temp
            cfg.top_p = float(body.get("top_p") or 1.0)
            # tohum sabit kalirsa ayni sicaklikta ayni cevap gelir
            cfg.rng_seed = int(body.get("seed") or random.randrange(2**31))
        if body.get("repetition_penalty"):
            cfg.repetition_penalty = float(body["repetition_penalty"])
        text = clean(str(pipe.generate(
            build_prompt(body.get("messages", []), body.get("mode")), cfg)))
        self.reply({"choices": [{"message": {"role": "assistant", "content": text},
                                 "finish_reason": "stop", "index": 0}],
                    "risk": bool(RISKLI.search(text)),
                    "model": os.path.basename(MODEL), "object": "chat.completion"})

    def reply(self, obj):
        self.send_bytes(json.dumps(obj).encode(), "application/json")

    def send_bytes(self, data, ctype):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def selftest():
    assert clean("```bash\ndf -h\n```") == "df -h"
    assert clean("df -h") == "df -h"
    assert clean("önce:\n```\nls\n```\nsonra") == "önce:\nls\nsonra"
    assert clean("echo ```") == "echo ```"        # satır ortasındaki çite dokunma
    assert clean("<think>uzun uzun</think>\ndf -h") == "df -h"
    assert clean("analysis kullanici disk soruyor assistantfinal df -h") == "df -h"
    assert clean("<think>yarim kalmis") == "<think>yarim kalmis"   # kapanmadan kesme
    riskli = ["sudo rm /var/lib/dpkg/lock-frontend", "rm -rf ~/projects", "sudo reboot",
              "mkfs.ext4 /dev/sda1", "dd if=x of=/dev/sda", "sudo apt purge nginx",
              "chmod -R 777 /etc"]
    temiz = ["df -h", "ls -lt | head -n 6", "systemctl --user restart ai-npu",
             "rm dosya.txt", "sed -i 's/a/b/g' not.txt", "sudo apt update"]
    for t in riskli:
        assert RISKLI.search(t), f"yakalanmadi: {t}"
    for t in temiz:
        assert not RISKLI.search(t), f"yanlis alarm: {t}"
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
    HTTPServer(("127.0.0.1", int(os.environ.get("AI_NPU_PORT", 11435))), Handler).serve_forever()
