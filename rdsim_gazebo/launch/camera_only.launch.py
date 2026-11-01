import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.conditions import IfCondition
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    description = FindPackageShare('rdsim_description')
    gazebo = FindPackageShare('rdsim_gazebo')
    delivery = FindPackageShare('delivery_robot_sim')
    robot_xacro = PathJoinSubstitution([description, 'urdf', 'rdsim.urdf.xacro'])
    world = PathJoinSubstitution([gazebo, 'worlds', LaunchConfiguration('world_name')])
    params = PathJoinSubstitution([delivery, 'config', 'params.yaml'])
    results_dir = LaunchConfiguration('results_dir')
    gui = LaunchConfiguration('gui')
    traffic_light = LaunchConfiguration('traffic_light')

    robot_description = ParameterValue(Command(['xacro ', robot_xacro]), value_type=str)
    model_path = os.path.join(get_package_share_directory('rdsim_gazebo'), 'models')
    gazebo_model_path = os.pathsep.join(
        path for path in (model_path, '/rdsim/rdsim_gazebo/models', os.environ.get('GAZEBO_MODEL_PATH', '')) if path
    )

    display_env = os.environ.get('DISPLAY', '')
    gzserver_cmd = (
        ['gzserver', '--verbose', '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so', world]
        if display_env
        else ['xvfb-run', '-a', 'gzserver', '--verbose', '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so', world]
    )

    server = ExecuteProcess(
        cmd=gzserver_cmd,
        additional_env={
            'GAZEBO_MODEL_PATH': gazebo_model_path,
            'GAZEBO_MODEL_DATABASE_URI': ''
        },
        output='screen',
    )
    gazebo_client = ExecuteProcess(
        cmd=['gzclient', '--verbose'],
        additional_env={
            'GAZEBO_MODEL_PATH': gazebo_model_path,
            'GAZEBO_MODEL_DATABASE_URI': ''
        },
        condition=IfCondition(gui),
        output='screen',
    )
    camera_viewer = Node(
        package='rqt_image_view',
        executable='rqt_image_view',
        arguments=['/camera/image_raw'],
        condition=IfCondition(gui),
        output='screen',
    )
    state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen',
    )
    spawn = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'rdsim', '-topic', 'robot_description',
            '-x', LaunchConfiguration('spawn_x'),
            '-y', LaunchConfiguration('spawn_y'),
            '-z', LaunchConfiguration('spawn_z'),
            '-timeout', '600',
        ],
        output='screen',
    )

    def pipeline_node(executable, log_name=None, condition=None, extra_params=None):
        node_parameters = [params, {'use_sim_time': True}]
        if extra_params is not None:
            node_parameters.append(extra_params)
        if log_name is not None:
            node_parameters[1]['log_path'] = PathJoinSubstitution([results_dir, log_name])
        if executable == 'evaluator_node':
            node_parameters[1]['summary_path'] = PathJoinSubstitution([results_dir, 'eval_summary.json'])
        return Node(
            package='delivery_robot_sim',
            executable=executable,
            parameters=node_parameters,
            condition=condition,
            output='screen',
        )

    def start_runtime_after_spawn(event, context):
        if event.returncode != 0:
            return [
                EmitEvent(
                    event=Shutdown(
                        reason=f'Robot spawn failed with exit code {event.returncode}'
                    )
                )
            ]

        selected_world = LaunchConfiguration('world_name').perform(context)
        if selected_world.startswith('small_city'):
            # Authentic Camera-Only Urban Autonomous Delivery Stack (NO LiDAR, NO GPS)
            return [
                Node(
                    package='delivery_robot_sim',
                    executable='order_manager_node',
                    name='order_manager_node',
                    parameters=[{
                        'use_sim_time': True,
                        'depot_x': -31.5,
                        'depot_y': -0.75,
                        'results_dir': results_dir,
                        'dynamic_order_time_s': 15.0,
                        'dwell_time_s': 2.0
                    }],
                    output='screen'
                ),
                Node(
                    package='delivery_robot_sim',
                    executable='city_driver_node',
                    name='driver_node',
                    parameters=[{
                        'use_sim_time': True,
                        'log_path': PathJoinSubstitution([results_dir, 'driver_log.csv']),
                        'traffic_lights_enabled': traffic_light,
                        'max_linear_speed': 1.30,
                        'arrival_tolerance_m': 1.20,
                        'simulate_depth_drop_t': ParameterValue(LaunchConfiguration('simulate_depth_drop_t'), value_type=float)
                    }],
                    output='screen'
                ),
                Node(
                    package='delivery_robot_sim',
                    executable='web_bridge_node',
                    name='web_bridge_node',
                    parameters=[{
                        'use_sim_time': True,
                        'static_dir': '/rdsim/delivery_robot_sim/web_dashboard',
                    }],
                    output='screen'
                ),
                Node(
                    package='delivery_robot_sim',
                    executable='cargo_delivery_manager',
                    name='cargo_delivery_manager',
                    parameters=[{
                        'use_sim_time': True,
                    }],
                    output='screen'
                ),
                Node(
                    package='delivery_robot_sim',
                    executable='evaluator_node',
                    name='evaluator_node',
                    parameters=[{
                        'use_sim_time': True,
                        'log_path': PathJoinSubstitution([results_dir, 'eval_log.csv']),
                        'summary_path': PathJoinSubstitution([results_dir, 'eval_summary.json']),
                        'obstacle_x': ParameterValue(LaunchConfiguration('obstacle_x'), value_type=float),
                        'obstacle_y': ParameterValue(LaunchConfiguration('obstacle_y'), value_type=float)
                    }],
                    output='screen'
                ),
                Node(
                    package='delivery_robot_sim',
                    executable='traffic_light_node',
                    name='traffic_light_node',
                    condition=IfCondition(
                        PythonExpression(["'", traffic_light, "' == 'true'"])
                    ),
                    output='screen'
                ),
                ExecuteProcess(
                    cmd=['bash', '-c', 'sleep 3; for cam in $(gz camera -l 2>/dev/null); do gz camera -c "$cam" -f rdsim; done || gz camera -c default::user_camera -f rdsim || true'],
                    condition=IfCondition(gui),
                    output='screen'
                ),
            ]
        elif selected_world == 'camera_delivery.world':
            return [
                pipeline_node(
                    'driver_node',
                    'driver_log.csv',
                    extra_params={'traffic_lights_enabled': traffic_light},
                ),
                pipeline_node('evaluator_node', 'eval_log.csv'),
                pipeline_node(
                    'traffic_light_node',
                    condition=IfCondition(
                        PythonExpression(["'", traffic_light, "' == 'true'"])
                    ),
                ),
            ]
        return []

    return LaunchDescription([
        DeclareLaunchArgument('results_dir', default_value=os.path.join(os.getcwd(), 'results')),
        DeclareLaunchArgument('gui', default_value='false', description='Show Gazebo GUI and ROS camera viewer'),
        DeclareLaunchArgument(
            'world_name',
            default_value='small_city_dynamic.world',
            description='Gazebo world file installed in rdsim_gazebo/worlds',
        ),
        DeclareLaunchArgument('spawn_x', default_value='-30.0'),
        DeclareLaunchArgument('spawn_y', default_value='0.0'),
        DeclareLaunchArgument('spawn_z', default_value='0.05'),
        DeclareLaunchArgument(
            'traffic_light',
            default_value='true',
            description='Run the traffic light controller',
        ),
        DeclareLaunchArgument('obstacle_x', default_value='-23.0', description='Ground truth obstacle x coordinate'),
        DeclareLaunchArgument('obstacle_y', default_value='0.25', description='Ground truth obstacle y coordinate'),
        DeclareLaunchArgument('simulate_depth_drop_t', default_value='0.0', description='Simulate depth drop timestamp'),
        server,
        RegisterEventHandler(
            OnProcessExit(
                target_action=server,
                on_exit=[EmitEvent(event=Shutdown(reason='Gazebo server exited'))],
            )
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=gazebo_client,
                on_exit=[EmitEvent(event=Shutdown(reason='Gazebo client exited'))],
            )
        ),
        gazebo_client,
        camera_viewer,
        state_publisher,
        RegisterEventHandler(
            OnProcessExit(target_action=spawn, on_exit=start_runtime_after_spawn)
        ),
        spawn,
    ])
