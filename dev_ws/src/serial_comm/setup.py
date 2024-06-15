from setuptools import find_packages, setup
import os
from glob import glob

package_name = "serial_comm"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            os.path.join("share", package_name, "launch"),
            glob(os.path.join("launch", "*launch.[pxy][yma]*")),
        ),
    ],
    install_requires=["setuptools", "midibot_py"],
    zip_safe=True,
    maintainer="sarpdengizmen",
    maintainer_email="e.dengizmen@gmail.com",
    description="TODO: Package description",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "serial_node = serial_comm.serial_node:main",
        ],
    },
)
