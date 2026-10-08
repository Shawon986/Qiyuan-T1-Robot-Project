from setuptools import find_packages, setup

package_name = "seedance"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "boto3"],
    zip_safe=True,
    maintainer="Shawon",
    maintainer_email="shawonh986@gmail.com",
    description="Seedance video-generation pipeline (BytePlus ModelArk + Object Storage).",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "seedance = seedance.main:main",
        ],
    },
)
