# Root Cause Analysis: OTP Handover to Depot Return Failure

## 1. Bug Description
In prior releases, when a customer placed an order on the web portal and validated their OTP at doorstep arrival, the motorized hatch opened to $60^\circ$, but the robot remained permanently stationary at the delivery location and failed to return to the depot.

---

## 2. Event Chain & Execution Path Inspection

```mermaid
flowchart TD
    Client["Customer Portal (Browser)"] -->|POST /api/verify_otp| WB["WebBridgeNode (/api)"]
    WB -->|gz joint cargo_hatch_joint 1.05| CDM["CargoDeliveryManager"]
    Client -->|POST /api/confirm_delivery| WB
    WB -->|/delivery/confirm_handover| OMN["OrderManagerNode"]
    OMN -->|evaluate_next_action()| OM["OrderManager Class"]
    OMN -->|/delivery/current_target| CDN["CityDriverNode"]
    CDN -->|/cmd_vel| GZ["Gazebo Classic 11"]
```

---

## 3. The Smoking Gun Root Cause

### 3.1 Unmatched Order IDs Across Process Boundaries
When orders were placed dynamically via the client browser, `WebBridgeNode` generated an order ID (e.g., `ORD-029` or `ORD-031`) and stored it in SQLite `nexus_delivery.db`.

Meanwhile, `OrderManagerNode` launched with static scenario orders in memory (e.g., `ORD-001`), with `self.order_mgr.current_order` initialized to `ORD-001`.

In `order_manager_node.py`, the handover callback was implemented as:
```python
# FAULTY HISTORICAL CODE:
def _on_handover_confirmed(self, msg: String):
    data = json.loads(msg.data)
    order_id = data.get('order_id', self.dwell_order_id or '')
    if order_id in self.order_mgr.orders:
        self.order_mgr.confirm_delivery(order_id, now=now)
    # Notice: if order_id was NOT in self.order_mgr.orders, NOTHING HAPPENED!
```

### 3.2 Target Overwrite by Periodic Timer Loop
`OrderManagerNode` maintained a periodic 2Hz timer (`_on_timer`):
```python
def _on_timer(self):
    ...
    act = self.order_mgr.evaluate_next_action(self.robot_xy, now=now)
    msg_target.data = json.dumps(act)
    self.pub_target.publish(msg_target)
```
Because `order_id` `ORD-031` was not found in `self.order_mgr.orders`, `confirm_delivery` was **never called** on `order_mgr`. As a result:
1. `self.order_mgr.current_order` remained active and stuck in `GOING_TO_DELIVERY`.
2. Every 500ms, `_on_timer` called `evaluate_next_action()`, which repeatedly evaluated Rule 1:
   ```python
   if self.current_order:
       return {
           'target_name': self.current_order.delivery_name,
           'target_xy': self.current_order.delivery_xy,
           'action': 'DELIVERY'
       }
   ```
3. Even if `web_bridge_node` published `action: 'PARK'` to `/delivery/current_target`, half a second later `order_manager_node`'s timer published `action: 'DELIVERY'` back to the delivery bay!
4. `CityDriverNode` received the conflicting `DELIVERY` target and kept the robot halted at the doorstep.

---

## 4. Engineering Fix & Permanent Resolution

### 4.1 Order Manager Node Handover Resolution
Updated `OrderManagerNode._on_handover_confirmed` to guarantee state clearance:
```python
# RESOLVED IMPLEMENTATION:
if order_id in self.order_mgr.orders:
    self.order_mgr.confirm_delivery(order_id, now=now)
elif self.order_mgr.current_order:
    cur_id = self.order_mgr.current_order.order_id
    self.order_mgr.confirm_delivery(cur_id, now=now)
elif self.dwell_order_id and self.dwell_order_id in self.order_mgr.orders:
    self.order_mgr.confirm_delivery(self.dwell_order_id, now=now)

# Clear active mission & dwell locks unconditionally
self.dwell_until = None
self.dwell_action = None
self.dwell_order_id = None
self.dwell_otp = None
self.order_mgr.current_order = None
self.order_mgr.carried_packages.clear()
self.order_mgr.returning_to_depot = True
self.order_mgr.mission_state = MissionLifecycleState.RETURNING_TO_DEPOT.value

# Publish PARK target immediately
ret_act = {
    'target_name': self.order_mgr.depot_name,
    'target_xy': list(self.order_mgr.depot_xy),
    'target_heading': 0.0,
    'action': 'PARK',
    'order_id': order_id,
    'package_id': 'NONE'
}
self.pub_target.publish(String(data=json.dumps(ret_act)))
```

### 4.2 Web Bridge Node Target Synchronization
In `WebBridgeNode.confirm_delivery()`, both `/delivery/confirm_handover` and `/delivery/current_target` are published with `action: 'PARK'` and coordinates `(-31.5, -0.75)`, ensuring total idempotency even across network retries.

### 4.3 Closed-Loop Joint Interlock in Driver Node
Added hardware safety gating in `city_driver_node.py`:
```python
if getattr(self, 'hatch_is_open', False) and self.target_action != 'WAIT':
    self.cmd_v = 0.0
    self.cmd_w = 0.0
    self._send_cmd(0.0, 0.0)
    self.state = 'CARGO_DOOR_AJAR'
    return
```
The robot will never apply torque or navigate while the hatch is unlatched. As soon as joint feedback verifies closure ($|\theta| < 0.08\text{ rad}$), navigation automatically engages.
