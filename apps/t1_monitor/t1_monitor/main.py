"""Console entry point for t1_monitor."""
from __future__ import annotations

import rclpy

from .monitor_node import T1MonitorNode


def main(args: list[str] | None = None) -> int:
    rclpy.init(args=args)
    node = T1MonitorNode()
    try:
        rclpy.spin(node)
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
