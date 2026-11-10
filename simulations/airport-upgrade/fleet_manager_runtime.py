"""Reuse the official RMF demo manager, adding a measured arrival fallback.

The installed TinyRobot plugin may retain MODE_MOVING at a +/-pi heading
although path=[], position and wrapped heading remain stationary. The fleet
manager would otherwise wait indefinitely. Only amend this mode for a current
command at its exact requested goal after a continuous measured one-second
stop. No task/path id, position or RMF task result is fabricated.
"""
import copy
from rmf_demos_fleet_adapter import fleet_manager as manager
from rmf_fleet_msgs.msg import RobotMode
from arrival_guard import ArrivalGuard

original_callback=manager.FleetManager.robot_state_cb

def measured_arrival(self,msg):
    if not hasattr(self,"arrival_guard"):
        self.arrival_guard=ArrivalGuard()
    robot=self.robots.get(msg.name)
    target=robot.destination if robot else None
    expected=robot is not None and robot.is_expected_task_id(msg.task_id) and not robot.mode_teleop
    goal=[target.x,target.y,target.yaw] if expected and target is not None else None
    loc=msg.location;t=loc.t.sec+loc.t.nanosec/1e9
    arrived=self.arrival_guard.update(msg.name,msg.task_id,t,loc.x,loc.y,loc.yaw,
        goal,not msg.path,msg.mode.mode==RobotMode.MODE_MOVING)
    if arrived:
        self.get_logger().info(f"Measured arrival {msg.name} command {msg.task_id}: <0.05 m, <0.03 rad, stationary >=1 s")
        msg=copy.deepcopy(msg);msg.mode.mode=RobotMode.MODE_IDLE
    original_callback(self,msg)

manager.FleetManager.robot_state_cb=measured_arrival
if __name__=="__main__":manager.main()
