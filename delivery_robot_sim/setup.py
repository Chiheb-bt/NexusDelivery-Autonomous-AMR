import os
from glob import glob
from setuptools import find_packages, setup

pkg = "delivery_robot_sim"


def tree(src, dst):
    """Installe un dossier en conservant son arborescence."""
    out = {}
    for path in glob(os.path.join(src, "**", "*"), recursive=True):
        if os.path.isfile(path):
            out.setdefault(os.path.join("share", pkg, os.path.dirname(path)), []).append(path)
    return list(out.items())


setup(
    name=pkg,
    version="0.1.0",
    packages=find_packages(exclude=["tests"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + pkg]),
        ("share/" + pkg, ["package.xml"]),
        ("share/" + pkg + "/launch", glob("launch/*.py")),
        ("share/" + pkg + "/config", glob("config/*.yaml")),
        ("share/" + pkg + "/models", ["yolov8n.pt"]),
        ("share/" + pkg + "/urdf", glob("urdf/*")),
        ("share/" + pkg + "/worlds", glob("worlds/*.sdf")),
        ("share/" + pkg + "/web_dashboard", [f for f in glob("web_dashboard/*") if os.path.isfile(f)]),
        ("share/" + pkg + "/web_dashboard/downloads", [f for f in glob("web_dashboard/downloads/*") if os.path.isfile(f)]),
    ] + tree("models", "models"),
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Chiheb",
    maintainer_email="chiheb@example.com",
    description="Autonomous delivery robot simulation with ROS 2 and Gazebo for camera-based navigation, traffic-light handling, and headless validation.",
    long_description="A polished ROS 2 / Gazebo robotics project for autonomous delivery robot simulation, featuring camera-based navigation, traffic-light logic, obstacle handling, and headless VM compatibility.",
    long_description_content_type="text/markdown",
    license="MIT",
    keywords="ros2 gazebo robotics autonomous-delivery robot-simulation perception",
    entry_points={
        "console_scripts": [
            "city_driver_node = delivery_robot_sim.city_driver_node:main",
            "order_manager_node = delivery_robot_sim.order_manager_node:main",
            "driver_node = delivery_robot_sim.driver_node:main",
            "evaluator_node = delivery_robot_sim.evaluator_node:main",
            "traffic_light_node = delivery_robot_sim.traffic_light_node:main",
            "web_bridge_node = delivery_robot_sim.web_bridge_node:main",
            "cargo_delivery_manager = delivery_robot_sim.cargo_delivery_manager:main",
        ],
    },
)
