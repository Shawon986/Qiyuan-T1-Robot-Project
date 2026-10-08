from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Start the application in read-only monitoring mode by default."""
    return LaunchDescription(
        [
            Node(
                package="t1_monitor",
                executable="t1_monitor",
                name="t1_monitor",
                output="screen",
                parameters=[
                    {
                        "enable_tts": False,
                        "tts_confirmation_token": "",
                        "tts_text": "",
                        "motion_enabled": False,
                    }
                ],
            )
        ]
    )
