# Exhibition Demo System — Robot-Side Feature Handover

Version: 2026-10-11 (after full deep verification) | Audience: page-side developer team

---

## 1. System Architecture Overview

```
Visitor (Mandarin or Cantonese)
  → Robot app (Python, deployed on the brain board)
      ├─ AIChain: speech recognition + dialogue understanding (iFlytek)
      ├─ AIChain TTS voiceId 94 "子谦(粤)": Cantonese speech synthesis
      ├─ Official RTSP capture tool: 5 s reference video (get_video_stream.py, used verbatim)
      ├─ TOS (BytePlus bucket qiyuanseedance): temporary hosting for reference clips
      └─ Seedance (dreamina-seedance-2-0-fast-260128): 15 s / 16:9 video generation
  → Your v2 page (direct mode)
      ├─ Polls GET :8766/demo/last for tasks
      └─ Polls Ark itself for results and plays them
```

On-site page URL: `http://<robot-ip>:8766/v2-aurora-flow.html`
(:8766 serves the page, the fallback video assets, AND the /demo/last JSON.)

---

## 2. Verified Feature List (with evidence)

| # | Feature | Verification |
|---|---|---|
| 1 | Bilingual conversation | Mandarin AND Cantonese inputs transcribed correctly (AIChain STT engine 5, zh-HK); NLU always replies in Cantonese (multiple live tests incl. a recorded 3-turn conversation) |
| 2 | Cantonese TTS | AIChain voiceId 94 "子谦(粤)" (male) confirmed by ear; BytePlus female Cantonese voice as fallback |
| 3 | Video flow | Dedicated visitor phrases (e.g. 帮我生成视频) → Cantonese wait line 「請稍等，我馬上幫你生成視頻。」 → 5 s capture → FIXED prompt generation (visitors give no scenario; the scene comes entirely from the footage) |
| 4 | Fixed prompt | `VIDEO_GEN_PROMPT=把這個場景變成一段自然流暢、色彩生動的電影感短片。` (editable in .env) |
| 5 | Reference video rules | Resolution must be ≥ 854×480 (API hard requirement; robot camera far exceeds it); 640×480 is rejected (HTTP 400) |
| 6 | Video-only generation (no audio) | `generate_audio=false` by default: avoids the output-audio copyright policy (real office footage consistently triggered `OutputAudioSensitiveContentDetected`; the same footage succeeds in video-only mode) |
| 7 | Generation time | Measured 117–237 s (2.0-fast model) |
| 8 | Multi-visitor concurrency | Unique temp file per round (no clobbering); capture starts immediately on intent (footage = exactly what the robot sees at that moment); uploads/submits serialized; older rounds never overwrite newer ones on /demo/last |
| 9 | Data-sharing control | **The page receives video-generation instructions ONLY**: /demo/last is written by video rounds only; WS chat replies are NOT broadcast by default (`SHARE_CHAT_WITH_PAGE=0`); conversations never leave the robot |
| 10 | Biped camera flip | In biped form the left camera's raw picture is upside-down (stated in the official manual); robot side auto-rotates 180° before upload (`CAMERA_FLIP_180=1`, confirmed on-site) |
| 11 | Upload path | TOS bucket (ap-southeast-1, virtual-hosted addressing; path-style is rejected with InvalidPathAccess — fixed and roundtrip-tested) |
| 12 | Page package integration | Your 2026-10-10 page package installed and served from :8766; page and robot use the SAME model `dreamina-seedance-2-0-fast-260128` (their pollArk filtering depends on this match) |
| 13 | Simulation rehearsal | Official MuJoCo model (T1-V2mesh.xml) + simulated view → full generation chain succeeded (156 s) |
| 14 | Automated tests | demo_ui 33 / conversation 26 / seedance 21 — all green |

---

## 3. Page-Side API Contract

### GET http://<host>:8766/demo/last
```json
{"round": 2, "text": "帮我生成一个视频", "time": "15:01", "taskId": "cgt-..."}
```
- Only VIDEO request rounds update this endpoint; chat never writes here (regression-tested)
- `text` = the visitor's utterance (the trigger); the generation prompt itself is the fixed VIDEO_GEN_PROMPT
- Older rounds never overwrite newer rounds

### WS ws://<host>:8765 (contract v2.0, backup channel)
- Message types: system / pong / chat / video_failed
- Video rounds broadcast: visitor utterance + Cantonese wait line (these ARE video instructions — allowed)
- Chat rounds: replies are NOT broadcast by default (data-sharing control); debugging via `SHARE_CHAT_WITH_PAGE=1`

### Model consistency requirement
Your page's pollArk filters tasks by model — **both sides must keep `dreamina-seedance-2-0-fast-260128`**.

---

## 4. Key Configuration (.env, copied to the robot at deploy)

```
SEEDANCE_MODEL_ID=dreamina-seedance-2-0-fast-260128
VIDEO_GEN_PROMPT=<fixed Cantonese prompt>
AICHAIN_TTS_VOICE_ID=94 / AICHAIN_TTS_ENABLED=1
CAMERA_VIDEO_REFERENCE=1 / CAMERA_CAPTURE_SECONDS=5.0 / CAMERA_FLIP_180=1
SEEDANCE_GENERATE_AUDIO=0 (default, avoids the copyright policy)
SHARE_CHAT_WITH_PAGE=0 (default, video instructions only)
```

---

## 5. Known Behavior & Limits

1. **Generated videos have NO audio** (default). To enable: `SEEDANCE_GENERATE_AUDIO=1` — but some footage may then trip the output-audio copyright policy and need retries.
2. **AIChain TTS is fixed at 16 kHz raw**; 24 kHz and opus requests are ignored; speed/pitch params have no effect.
3. **PrimeConsole's live view shows the raw stream** (may appear upside-down in biped form) — a platform-side display matter; it does NOT affect the robot-side capture (already auto-flipped).
4. While a generation is in progress, new video requests queue (the wait line is answered immediately); the page's 台面独占 (table-exclusive) switch complements the robot-side behavior.

---

## 6. Deployment & Startup (robot side)

```bash
bash scripts/deploy_to_robot.sh <robot-ip> <SN_soc0-key-dir>
# start on the board:
setsid bash /home/user/qiyuan-demo/run_demo_robot.sh > /tmp/qiyuan-demo.log 2>&1 < /dev/null &
```

---

## 7. Items to Confirm with the Page Side

1. Is it acceptable that generated videos have **no audio**? (The fallback videos do have sound; the page could layer ambient audio if consistency is needed.)
2. In 台面独占 mode, does the page keep polling /demo/last while waiting? (It currently does.)
3. The page's robotUrl should be `http://127.0.0.1:8766/demo/last` on the board (loopback); on the dev PC use the WSL NAT IP.
