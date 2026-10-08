# Credentials & Requirements — Step-by-Step Acquisition Guide

All four cloud platforms below require an account + **real-name verification (实名认证)**
with your phone number — standard for Chinese cloud services. All have free tiers that
are sufficient for the demo.

---

## 1. iFlytek Open Platform (Cantonese ASR + TTS)

**Link:** https://www.xfyun.cn/ (register → 控制台)

1. Register with phone number, complete 实名认证 (personal is fine).
2. In the console: **创建新应用** (Create application) → name it e.g. `qiyuan-t1-demo`.
3. The app page shows **APPID / APIKey / APISecret** — copy all three.
4. Enable these two services for the app (they may need separate activation):
   - **语音听写（流式版）** — the streaming ASR service; its `dialect` parameter supports
     Cantonese (`cantonese`) and it has a daily free tier.
   - **在线语音合成** — TTS service; choose a Cantonese voice (e.g. 粤语女声) when we
     configure it. Free daily quota applies.
5. Docs: https://www.xfyun.cn/doc/asr/voicedictation/API.html and
   https://www.xfyun.cn/doc/tts/online_tts/API.html

> The broken Yuque link (aiui_open_platform) pointed at AIUI docs — for our use the
> classic xfyun WebAPI above is what we integrate; the robot-side AIUI config is not
> needed for the app-layer plan.

**Deliverables:** APPID, APIKey, APISecret

---

## 2. Alibaba Cloud Model Studio / DashScope (Qwen LLM)

**Link:** https://bailian.console.aliyun.com/

1. Register an Alibaba Cloud account (https://www.aliyun.com) and complete 实名认证.
2. Open Model Studio (百炼) console.
3. Go to **API-KEY 管理** (usually under 模型服务 / 应用) → **创建 API Key**.
4. Recommended model for our session-memory conversation: **qwen-long**
   (1M-token context, cheap) or **qwen-plus** (balanced). New users get a free quota.

**Deliverables:** DashScope API key (starts with `sk-`)

---

## 3. Volcano Engine TOS (video storage)

**Link:** https://console.volcengine.com/tos/

1. Register at https://www.volcengine.com (火山引擎), complete 实名认证.
2. Open **对象存储 TOS** → **创建存储桶** (create bucket), region e.g. 北京.
   Keep the bucket **private** (we upload/download with SDK credentials).
3. Get credentials: **访问控制 IAM → 访问密钥** → create **AccessKey/SecretKey**.
4. Note the **endpoint** for your region (e.g. `tos-cn-beijing.volces.com`).

**Deliverables:** AccessKey ID, SecretAccessKey, bucket name, endpoint/region

---

## 4. SeeDance platform (your own system)

No external account. Ask your backend/Java team for:

1. API base URL + environment (test/prod)
2. Endpoints: submit task (video + prompt), query task status, fetch result
3. Authentication (token/API key) and any request/response JSON examples

If the API isn't defined yet, we can jointly freeze a minimal REST contract
(submit → taskId; poll status → done; get result URL) and build both sides to it.

**Deliverables:** API spec document or endpoint list

---

## 5. PrimeBot (robot-side requirements)

Portal account is already created (robot IP `10.1.1.100` registered).

1. **SSH credentials** for `run@<board-IP>`: request from after-sales support via
   - Developer community Q&A board: https://dev.primebot.com/community?board=qa
   - Feedback board: https://dev.primebot.com/community?board=feedback
   - PrimeBOT APP customer service / any official WeChat group
2. In the same ticket ask:
   - Which SDK matches your robot's firmware: portal **v1.0.0.0** or repo **v0.9.4.7**?
   - **Gimbal control resource/action IDs** (MC upper-body command) for follow-and-film
   - List of available **preset motion IDs** (for dancing)
   - Confirm the camera topic `/aima/hal/camera/head_stereo_left_orin` and audio
     topic `/aima/hal/audio/capture` are enabled in Develop+Basic mode

**Deliverables:** SSH credentials + answers to the four questions

---

## 6. How to hand the keys to me (securely)

Never paste secrets in chat. Instead:

1. Copy `apps/.env.example` (in this repo) to `D:\Qiyuan T1 Robotics project\.env`
2. Fill in the values
3. Tell me "keys are in .env" — I will only read them into environment
   variables at runtime and never commit them.

`.env` is already in `.gitignore`.

---

## Summary checklist

| # | Item | Link | Done? |
|---|---|---|---|
| 1 | iFlytek APPID/APIKey/APISecret | https://www.xfyun.cn | ☐ |
| 2 | DashScope API key (Qwen) | https://bailian.console.aliyun.com | ☐ |
| 3 | Volcano TOS AK/SK + bucket | https://console.volcengine.com/tos/ | ☐ |
| 4 | SeeDance API spec | your backend team | ☐ |
| 5 | PrimeBot SSH + 4 answers | https://dev.primebot.com/community?board=qa | ☐ |
| 6 | PrimeBot portal account | https://dev.primebot.com | ✅ |
| 7 | AtomGit account (cloning skills) | https://atomgit.com | ☐ optional |
