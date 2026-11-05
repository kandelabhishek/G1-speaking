import json
import time
import rclpy
from rclpy.node import Node
from unitree_api.msg import Request, Response

class G1Speaker(Node):
    def __init__(self):
        super().__init__("g1_speaker")
        self.app_name = "g1_communication"
        self.current_id = None
        self.current_response = None

        self.publisher = self.create_publisher(
            Request,
            "/api/voice/request",
            10,
        )

        self.subscription = self.create_subscription(
            Response,
            "/api/voice/response",
            self.recieve_response,
            10,
        )

    def wait_until_ready(self, timeout = 10):
        deadline = time.monotonic() + timeout

        while (
            self.publisher.get_subscription_count() == 0 or self.count_publishers("/api/voice/response") == 0
        ):
            if time.monotonic() >= deadline:
                raise RuntimeError("G1 audio was not found")
            rclpy.spin_once(self, timeout_sec=0.1)

            self.wait(1.0)

    def recieve_response(self, message):
        if message.header.identity.id == self.current_id:
            self.current_response = message

    def wait(self, seconds):
        deadline = time.monotonic() + seconds

        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
    def call(self, api_id, parameters, pcm=b"", timeout = 5):
        request = Request()

        request.header.identity.id = time.monotonic_ns()
        request.header.identity.api_id = api_id
        request.header.policy.noreply = False

        request.parameter = json.dumps(parameters)
        request.binary = list(pcm)

        self.current_id = request.header.identity.id
        self.current_response = None

        self.publisher.publish(request)

        deadline = time.monotonic()+timeout

        while self.current_response is None:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"G1 audio API{api_id} timed out")

            rclpy.spin_once(self, timeout_sec=0.05)

        code = self.current_response.header.status.code

        if code != 0:
            raise RuntimeError(f"G1 Audio API {api_id} returned error {code}")

    def play(self, pcm):
        if not pcm:
            return

        stream_id = str(time.monotonic_ns())
        playback_end = time.monotonic()

        for offset in range(0, len(pcm), 96000):
            chunk = pcm[offset:offset + 96000]

            self.call(
                1003,
                {
                    "app_name":self.app_name,
                    "stream_id":stream_id,
                },
                chunk,
            )

            playback_end = (
                max(playback_end, time.monotonic()) + len(chunk)/32000
            )

            self.wait(min(1.0, len(chunk)/32000))

        remaining = playback_end - time.monotonic()
        self.wait(max(0.0, remaining) + 0.3)

    def stop(self):
        self.call(
            1004,
            {"app_name":self.app_name},
            timeout=2,
        )

