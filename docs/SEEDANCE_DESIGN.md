# SeeDance Integration — Design & Implementation Plan

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

- TOS uploader + SeeDance client + PC test harness: ready to build as soon as
  TOS credentials and the SeeDance API spec arrive.
- Robot camera adapter: implement after Day 5 (developer mode active).
