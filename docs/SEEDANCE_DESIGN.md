# SeeDance Integration — Design & Implementation Plan

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
  (submit/poll/wait, validated payloads), BytePlus Object Storage uploader (boto3 S3 + pre-signed URLs),
  pipeline + CLI. 10/10 offline tests; colcon build clean.
- Decision (2026-10-08): **Option B — BytePlus Object Storage** for robot-recorded videos.
- ⏳ Needs user: TOS_ACCESS_KEY / TOS_SECRET_KEY / TOS_BUCKET / TOS_ENDPOINT in `.env` for live video tests.
- Robot camera adapter: implement after Day 5 (developer mode active).
