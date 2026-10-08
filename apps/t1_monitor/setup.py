from setuptools import find_packages, setup

package_name = "t1_monitor"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/t1_monitor.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Shawon",
    maintainer_email="shawonh986@gmail.com",
    description="Fail-closed read-only T1 monitor (BMS/touch/ASR + guarded TTS).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "t1_monitor = t1_monitor.main:main",
        ],
    },
)
