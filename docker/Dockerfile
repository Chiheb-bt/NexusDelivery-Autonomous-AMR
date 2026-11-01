# Reproducible Dockerfile for RDSim Autonomous Delivery Robot Simulation
# ROS 2 Humble + Gazebo Classic 11 + Headless offscreen camera support via xvfb

FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive

# Install Gazebo Classic 11 and required ROS 2 packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    python3-colcon-common-extensions \
    python3-rosdep \
    xvfb \
    xauth \
    python3-pip \
    python3-opencv \
    python3-numpy \
    python3-matplotlib \
    git \
    wget \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set up Gazebo resource paths
ENV GAZEBO_RESOURCE_PATH=/usr/share/gazebo-11:$GAZEBO_RESOURCE_PATH
ENV ROS_DISTRO=humble

# Source ROS 2 Humble in bash sessions
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

WORKDIR /ws

CMD ["bash"]
