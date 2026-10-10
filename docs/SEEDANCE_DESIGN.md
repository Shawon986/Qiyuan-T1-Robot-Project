# SeeDance Integration — Design & Implementation Plan

## Page integration API — FINAL Option B contract (2026-10-09)

**Architecture: the robot CONVERSES only; the PAGE generates automatically.**

```
USER speaks → ROBOT (ASR→LLM→TTS) → posts events to the session API
PAGE polls the session API → auto-submits the video_request → generates → renders
PAGE reports its task state back (POST /api/events) → robot can TTS "video ready"
```

Robot app runs the session API (no UI). The developer's page polls:

```
GET http://<robot-or-pc-ip>:8765/api/session        (poll every 1-2 s, CORS enabled)
→ {
    "dialogues": [ {"speaker":"user|robot","text":"...","ts":...}, ... ],
    "pending_request": { "id":"req-...", "prompt":"...", "ts":... } | null,  ← robot asks the page
    "current_task_id": "cgt-...",        ← set by the PAGE (feedback loop)
    "task_status": "idle|queued|running|succeeded|failed",
    "result_url": "https://..." | null
  }
POST /api/events  {"kind":"dialogue|video_request|video_start|video_status|video_result", ...}
```

Page auto-submit rule: remember the last seen `pending_request.id`; when a new id appears,
fill the prompt box and trigger the existing generate action. On `task_status == "succeeded"`
render `result_url` (guard: only while it belongs to the current task — verified by tests).

Stale-video guarantee (verified by unit + live tests): a new video request clears the previous
`result_url`; late results for old tasks are ignored.

## Page patch spec (audited 2026-10-09 against their index.html)

The page's existing generate flow is fully reusable (buildBody → newWork → submit → finish →
works list `<video src=w.videoUrl>` at line ~1128). Required additions:

1. **Dialogue box**: chat panel + `addChatLine(speaker, text)` (absent in the current file).
2. **Robot address setting**: `robotBase` field (default `http://<pc-or-robot-ip>:8765`).
3. **Poll + auto-submit** (core, ~15 lines): poll `/api/session` every 1.5 s; render new dialogue
   lines; when `pending_request.id` is new → `els.prompt.value = req.prompt; els.btnGen.click();`
   (reuses the existing validated generate handler — no refactor needed).
4. **Auto-show finished video**: on `succeeded`, scroll/play the latest `w.videoUrl`
   (currently it needs a manual thumbnail click).
5. **(Optional) Feedback**: POST `video_start/video_status/video_result` to `/api/events`
   so the robot can TTS-announce completion.

## Language requirement (locked 2026-10-10, updated 2026-10-10)

**The visitor may speak Mandarin OR Cantonese; the robot always replies in CANTONESE (粤语).**
Live-verified 2026-10-10: AIChain ASR (engine 5, language zh-HK) transcribes both Mandarin and
Cantonese correctly, and the AIChain persona answers in Cantonese either way.
Robot side confirmed Cantonese: wait phrase 請稍等我馬上幫你生成視頻, AIChain persona replies
(Cantonese), TTS = AIChain voiceId 4 (iFlytek, confirmed Cantonese-sounding 2026-10-10; engine.speak
uses it first), fallback = BytePlus voice zh_female_yueyunv_mars_bigtts.
Developer side must match: the page's own scripted bot lines (pickLine) in Cantonese, and all
text handling in UTF-8 Chinese — the robot's /demo/last `text` and WS `chat` messages arrive in Cantonese.

## Demo UX (confirmed 2026-10-09): three interacting parties

```
USER speaks (Mandarin or Cantonese, wake word 机器人)
  → ROBOT: ASR → Qwen LLM → TTS reply ("好的，马上为您生成")
  → ROBOT: submits to Seedance (15s video), streams events to the PAGE
  → PAGE: renders the dialogue live + plays the generated video (URL passed to page)
```

- Page: served by our skill (`apps/demo_ui`, Flask + WebSocket) — chat bubbles + status + video player.
- Duration: `duration` param added to the client; 15s support to be live-verified per model tier
  (2.0 series may cap at 5/10s — fall back to the max supported or use the 2.5 tier).
- Everything PC-testable: WSL mic/speakers (WSLg) + Seedance + browser page.


## CONFIRMED API — VALIDATED END-TO-END with live key (2026-10-08)

- Seedance model is hosted on **BytePlus ModelArk**: base `https://ark.ap-southeast.bytepluses.com/api/v3`
- Auth: `Authorization: Bearer <ModelArk API Key>`
- Model: `dreamina-seedance-2-0-fast-260128` (tiers: 2.5 / 2.0-fast / 2.0-mini; must be activated in console)
- **Submit**: `POST /contents/generations/tasks`
  `{"model": ..., "content": [{"type":"text","text":"..."}, {"type":"image_url","image_url":{"url":"data:image/png;base64,..."},"role":"first_frame"}]}` → `{"id":"cgt-..."}`
- **Poll**: `GET /contents/generations/tasks/{id}` → `status: running|succeeded|failed`, on success `content.video_url` (TOS-signed mp4)
- **Reference rules (empirically verified)**:
  - images: inline base64 data URI ✅ works (or public URL)
  - videos/audio: ONLY public URL or `asset://` — base64 rejected; Ark Files API ids (`file-...`) are NOT accepted in tasks
  - the official `CreateAsset` (→ asset://) requires AccessKey HMAC signing AND a public URL — so for robot-recorded
    videos a brief public hosting step is unavoidable: **developer's inbox** (PUT /sd-inbox-67862519/<name>, ~2h expiry)
    or **BytePlus Object Storage** (same account, pre-signed/public URL)
- Task list: `GET /contents/generations/tasks`
- Files API (`POST /api/v3/files`, Bearer, multipart) works for raw storage but is not referenceable from generation tasks.
- Browser cannot call upstream directly (CORS) — the web UI uses a forwarder: online at
  https://apivmorai.com/seedance/ (hosted by the developer) or local `node proxy.mjs` on 127.0.0.1:8790.
  The robot-side Python client calls the Ark endpoints server-side — no proxy needed.



Feature 4 of the project: the robot records a video + voice prompt, uploads to Volcano TOS,
submits to the SeeDance platform, which generates an AI video; the web page shows task
status and the result is delivered back to the robot.

## End-to-end flow

```
ROBOT (our Python app)
  1. Voice command -> iFlytek ASR -> prompt text
  2. Camera frames -> OpenCV encode -> mp4 (H.264)
  3. Upload mp4 to Volcano TOS -> object URL
  4. POST SeeDance task {video_url, prompt} -> task_id
  5. Poll GET task status until done/failed
  6. On done: fetch result video -> robot TTS announcement + playback/display
```

## Modules

| Module | Implementation | Dependency |
|---|---|---|
| Video capture | Subscribe `/aima/hal/camera/head_stereo_left_orin` (sensor_msgs/Image, verified in vendor skill) or CaptureJpegImage service or RTSP | Robot (post Day 5) |
| Encoding | OpenCV VideoWriter -> mp4/H.264; configurable resolution/FPS/max-duration | installed |
| Voice prompt | Reuse conversation-pipeline iFlytek ASR result | iFlytek keys |
| TOS upload | Python `tos` SDK; multipart upload; object key `seedance/<date>/<session>.mp4`; public-read or pre-signed URL | TOS AK/SK + bucket |
| SeeDance client | REST wrapper: submit / status / result; timeouts, retries, fail-closed | SeeDance API spec |
| Result delivery | Download result -> robot TTS ("视频已生成") + screen/web display | — |

## Proposed minimal REST contract (if the platform API is not yet defined)

```
POST /api/tasks        {"video_url": "...", "prompt": "...", "session_id": "..."}
                       -> {"task_id": "..."}
GET  /api/tasks/{id}   -> {"status": "queued|processing|done|failed",
                           "result_url": "...", "error": "..."}
```

Auth: bearer token or API key in header (per platform spec).
Both sides develop against this contract with mocks; final integration test at the end.

## PC-first testing (no robot required)

1. Record video with a PC webcam (or use any sample mp4).
2. Upload to TOS -> submit to SeeDance -> poll -> fetch result.
3. Once the cloud chain works, swap the PC-webcam adapter for the ROS camera adapter
   (single module change); everything else is identical.

## Safety / robustness

- Every step has a timeout; failures produce a polite TTS error, never block the conversation.
- Video retention: delete local file after upload (configurable); no audio/video logs by default.
- Secrets only from environment variables (`.env`), never committed.

## Status

- ✅ **Client package built** (`apps/seedance`, 2026-10-08): config (env/.env), Ark client
  (submit/poll/wait, validated payloads), two hosting backends (developer inbox default,
  BytePlus Object Storage fallback), pipeline + CLI. 16/16 offline tests; colcon build clean.
- ✅ **LIVE END-TO-END VALIDATED (2026-10-08) via the developer inbox (Option A)**: upload →
  submit → poll → succeeded → result URL. Reference-video spec: mp4 2–30s, ≥407,696 px.
- ⚠️ TOS fallback (Option B): bucket + keys configured but upload fails with `InvalidPathAccess`
  — likely AccessKey needs TOS permission enabled in console. Non-blocking.
- Robot camera adapter: implement after Day 5 (developer mode active).
