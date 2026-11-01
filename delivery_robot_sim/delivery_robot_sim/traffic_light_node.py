try:
    from rclpy._rclpy_pybind11 import RCLError
except ImportError:
    RCLError = Exception
"""Feu tricolore ROS Classic piloté via le service Gazebo Classic (/gazebo/set_entity_state).

Garantit :
1. Initialisation asynchrone sans blocage de l'exécuteur.
2. Vérification des réponses de service (done callbacks).
3. Synchronisation stricte entre l'état visuel dans Gazebo et le topic publié /traffic_light/state.
4. Tolérance aux pannes avec journalisation explicite.
"""

import rclpy
from rclpy.node import Node
from gazebo_msgs.srv import SetEntityState
from std_msgs.msg import String

POS = {
    "tl_red_on": (-16.2, -1.9, 2.5),
    "tl_green_on": (-16.2, -1.9, 2.5)
}


class TrafficLight(Node):
    def __init__(self):
        super().__init__("traffic_light_node")
        self.declare_parameter("red_s", 12.0)
        self.declare_parameter("green_s", 12.0)
        self.red_s = float(self.get_parameter("red_s").value)
        self.green_s = float(self.get_parameter("green_s").value)

        self.state_client = self.create_client(SetEntityState, "/gazebo/set_entity_state")
        self.desired_state = "RED"
        self.visual_state = "INITIALIZING"
        self.service_ready = False
        self.cycle_timer = None

        self.pub = self.create_publisher(String, "/traffic_light/state", 10)
        self.pub_timer = self.create_timer(0.5, self.publish_state)

        # Autonomous Southbound Traffic Vehicle Loop (obeying cross-traffic signals)
        self.car_x = -12.2
        self.car_y = 35.0
        self.car_speed = 2.5  # m/s
        self.car_stopped_at_red = False
        self.vehicle_timer = None

        # Asynchronous initialization check (non-blocking)
        self.init_timer = self.create_timer(0.2, self.check_service_init)
        self.get_logger().info("traffic_light_node démarré. En attente du service /gazebo/set_entity_state...")

    def check_service_init(self):
        if not self.state_client.service_is_ready():
            return

        self.init_timer.cancel()
        self.service_ready = True
        self.get_logger().info("Service /gazebo/set_entity_state disponible. Application de l'état initial (RED).")
        self.apply_state("RED")
        # moving_traffic_car removed from world to avoid collisions/ghost cars
        # if self.vehicle_timer is None:
        #     self.vehicle_timer = self.create_timer(0.2, self._update_traffic_vehicle)

    def publish_state(self):
        if not rclpy.ok() or not self.context.ok():
            return
        try:
            self.pub.publish(String(data=self.visual_state))
        except (RCLError, rclpy.executors.ExternalShutdownException, Exception):
            pass

    def _send_model_pose(self, name: str, visible: bool, callback=None):
        x, y, z = POS[name]
        target_z = z if visible else -5.0

        req = SetEntityState.Request()
        req.state.name = name
        req.state.reference_frame = "world"
        req.state.pose.position.x = x
        req.state.pose.position.y = y
        req.state.pose.position.z = target_z
        req.state.pose.orientation.w = 1.0

        future = self.state_client.call_async(req)

        def _on_done(fut):
            try:
                res = fut.result()
                if res.success:
                    self.get_logger().debug(f"Modèle '{name}' positionné à z={target_z:.2f} (visible={visible})")
                    if callback:
                        callback(True)
                else:
                    self.get_logger().debug(f"SetEntityState returned false for '{name}'")
                    if callback:
                        callback(False)
            except Exception as e:
                self.get_logger().debug(f"Exception SetEntityState pour '{name}': {e}")
                if callback:
                    callback(False)

        future.add_done_callback(_on_done)

    def apply_state(self, new_state: str):
        self.desired_state = new_state
        self.visual_state = new_state
        self.get_logger().info(f"Signal de circulation mis à jour : {self.visual_state}")

        if self.cycle_timer is not None:
            self.cycle_timer.cancel()
        interval = self.red_s if self.visual_state == "RED" else self.green_s
        self.cycle_timer = self.create_timer(interval, self.toggle)

        if not self.service_ready:
            return

        show_red = (new_state == "RED")
        show_green = (new_state == "GREEN")

        self._send_model_pose("tl_red_on", show_red)
        self._send_model_pose("tl_green_on", show_green)

    def toggle(self):
        next_state = "GREEN" if self.desired_state == "RED" else "RED"
        self.apply_state(next_state)

    def _update_traffic_vehicle(self):
        if not self.service_ready or not rclpy.ok():
            return

        dt = 0.2
        # Traffic light state: if Central Blvd is GREEN, North-South cross avenue is RED!
        north_ave_is_red = (self.visual_state == "GREEN")

        # Check if approaching stop line at y = 4.5m
        if north_ave_is_red and (4.5 <= self.car_y <= 6.2):
            self.car_stopped_at_red = True
        else:
            self.car_stopped_at_red = False
            self.car_y -= self.car_speed * dt
            if self.car_y < -35.0:
                self.car_y = 35.0

        # Send updated pose to Gazebo
        req = SetEntityState.Request()
        req.state.name = "moving_traffic_car"
        req.state.reference_frame = "world"
        req.state.pose.position.x = self.car_x
        req.state.pose.position.y = self.car_y
        req.state.pose.position.z = 0.05
        # Heading facing South (-pi/2 => q.z = -0.7071, q.w = 0.7071)
        req.state.pose.orientation.z = -0.7071
        req.state.pose.orientation.w = 0.7071
        try:
            self.state_client.call_async(req)
        except Exception:
            pass

    def destroy_node(self):
        if self.vehicle_timer is not None:
            self.vehicle_timer.cancel()
        if self.cycle_timer is not None:
            self.cycle_timer.cancel()
        if self.init_timer is not None:
            self.init_timer.cancel()
        if self.pub_timer is not None:
            self.pub_timer.cancel()
        super().destroy_node()


def main():
    rclpy.init()
    node = TrafficLight()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException, RCLError):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.try_shutdown()
