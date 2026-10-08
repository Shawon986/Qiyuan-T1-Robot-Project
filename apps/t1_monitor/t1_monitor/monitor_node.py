"""T1 read-only monitor node: BMS + touch + ASR observation and guarded TTS.

Verified endpoint defaults are supplied as parameters. The node NEVER publishes
motion commands and never treats graph discovery as proof that a robot feature
is available on a particular firmware or hardware batch.
"""
from __future__ import annotations

from typing import Any

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from aimdk_msgs.msg import AsrResult, Bms, TouchState
from aimdk_msgs.srv import PlayTts

from .policy import GuardedTtsPolicy, MotionGuard

DEFAULT_BMS_TOPIC = "/aima/hal/bms/state"
DEFAULT_TOUCH_TOPIC = "/aima/hal/touch/state"
DEFAULT_ASR_TOPIC = "/aima/agent/asr_result"
DEFAULT_TTS_SERVICE = "/aimdk_5Fmsgs/srv/PlayTts"

TTS_PRIORITY_INTERACTION_L6 = 6


class T1MonitorNode(Node):
    """Read BMS/touch/ASR state; optionally send one bounded, guarded TTS request."""

    def __init__(self) -> None:
        super().__init__("t1_monitor")
        self.declare_parameter("bms_topic", DEFAULT_BMS_TOPIC)
        self.declare_parameter("touch_topic", DEFAULT_TOUCH_TOPIC)
        self.declare_parameter("asr_topic", DEFAULT_ASR_TOPIC)
        self.declare_parameter("tts_service", DEFAULT_TTS_SERVICE)
        self.declare_parameter("enable_tts", False)
        self.declare_parameter("tts_confirmation_token", "")
        self.declare_parameter("tts_text", "")
        # Informational only: this package has no motion path at all.
        self.declare_parameter("motion_enabled", False)

        self._bms_topic = self._str_parameter("bms_topic")
        self._touch_topic = self._str_parameter("touch_topic")
        self._asr_topic = self._str_parameter("asr_topic")
        self._tts_service = self._str_parameter("tts_service")
        self._tts_policy = GuardedTtsPolicy()
        self._motion_guard = MotionGuard()
        self._tts_attempted = False

        self._bms_subscription = self.create_subscription(
            Bms, self._bms_topic, self._on_bms, qos_profile_sensor_data
        )
        self._touch_subscription = self.create_subscription(
            TouchState, self._touch_topic, self._on_touch, qos_profile_sensor_data
        )
        self._asr_subscription = self.create_subscription(
            AsrResult, self._asr_topic, self._on_asr, qos_profile_sensor_data
        )
        # Creating a client has no control effect; an RPC fires only after guards pass.
        self._tts_client = self.create_client(PlayTts, self._tts_service)

        self._startup_timer = self.create_timer(1.0, self._startup_once)
        self.get_logger().info(
            f"Monitoring: bms={self._bms_topic} touch={self._touch_topic} "
            f"asr={self._asr_topic}; guarded_tts={self._tts_service}"
        )
        self.get_logger().info(self._motion_guard.request("startup").reason)

    # ------------------------------------------------------------------ helpers
    def _str_parameter(self, name: str) -> str:
        value = self.get_parameter(name).value
        if not isinstance(value, str):
            raise ValueError(f"Parameter {name} must be a string, got {type(value).__name__}")
        return value

    def _startup_once(self) -> None:
        self._startup_timer.cancel()
        self._log_runtime_graph()
        self._send_tts_if_explicitly_approved()

    def _log_runtime_graph(self) -> None:
        # Count PUBLISHERS on the robot side, not graph entries: our own
        # subscriptions also appear in topic lists, so a topic name alone
        # proves nothing (handbook Chapter 1: schema != live publisher).
        bms_pub = self.count_publishers(self._bms_topic)
        touch_pub = self.count_publishers(self._touch_topic)
        asr_pub = self.count_publishers(self._asr_topic)
        tts_ready = self._tts_client.service_is_ready()
        self.get_logger().info(
            f"Robot-side publishers: bms={bms_pub} touch={touch_pub} asr={asr_pub}; "
            f"tts_service_ready={tts_ready}"
        )
        if bms_pub == 0:
            self.get_logger().warning(
                "No BMS publisher detected (0 = robot not publishing; check developer "
                "mode, reboot, subnet, ROS_DOMAIN_ID, QoS)."
            )

    # ------------------------------------------------------------------ sensors
    def _on_bms(self, message: Bms) -> None:
        self.get_logger().info(
            f"BMS: voltage={message.voltage / 1000.0:.3f} V "
            f"current={message.current / 1000.0:.3f} A "
            f"temperature={message.temperature:.3f} degC "
            f"remaining={int(message.remaining_capacity_percentage)}% "
            f"status=0x{int(message.status):08x}"
        )

    def _on_touch(self, message: TouchState) -> None:
        self.get_logger().info(
            f"Touch: sensor_id={int(message.sensor_id)} event_type={int(message.event_type)}"
        )

    def _on_asr(self, message: AsrResult) -> None:
        self.get_logger().info(
            f"ASR: text='{message.text}' is_final={bool(message.is_final)} "
            f"confidence={message.confidence:.3f} language={message.language} "
            f"event_id={message.event_id}"
        )

    # --------------------------------------------------------------------- TTS
    def _send_tts_if_explicitly_approved(self) -> None:
        if self._tts_attempted:
            return
        self._tts_attempted = True
        enabled = bool(self.get_parameter("enable_tts").value)
        token = self._str_parameter("tts_confirmation_token")
        text = self._str_parameter("tts_text")
        decision = self._tts_policy.decide(enabled=enabled, confirmation_token=token, text=text)
        if not decision.allowed:
            self.get_logger().warning(f"TTS blocked locally: {decision.reason}")
            return
        if not self._tts_client.wait_for_service(timeout_sec=0.0):
            self.get_logger().error(
                f"TTS blocked: verified service name {self._tts_service} is not available "
                "at this time; no retry is sent."
            )
            return
        request = PlayTts.Request()
        request.tts_req.text = text
        request.tts_req.priority_level.value = TTS_PRIORITY_INTERACTION_L6
        request.tts_req.priority_weight = 0
        request.tts_req.domain = "t1_monitor"
        request.tts_req.trace_id = "guarded_startup"
        request.tts_req.is_interrupted = False
        future = self._tts_client.call_async(request)
        future.add_done_callback(self._on_tts_response)
        self.get_logger().info("One guarded TTS request was sent; awaiting service response.")

    def _on_tts_response(self, future: Any) -> None:
        try:
            response = future.result()
        except Exception as exc:  # rclpy surfaces transport/RPC failures here
            self.get_logger().error(f"TTS RPC failed: {exc}")
            return
        framework_code = response.header.header.code
        business_state = response.header.status.value
        success = response.tts_resp.is_success
        if framework_code == 0 and business_state == 1 and success:
            self.get_logger().info(
                "TTS accepted: "
                f"estimated_duration_ms={response.tts_resp.estimated_duration} "
                f"trace_id={response.tts_resp.trace_id}"
            )
        else:
            self.get_logger().error(
                "TTS was not accepted: "
                f"framework_code={framework_code} business_state={business_state} "
                f"is_success={success} error={response.tts_resp.error_message}"
            )
