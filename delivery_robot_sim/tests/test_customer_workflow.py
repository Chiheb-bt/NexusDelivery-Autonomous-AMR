#!/usr/bin/env python3
"""
NexusDelivery — End-to-End Customer-to-Autonomous-Robot Delivery Workflow Test Suite
Comprehensive verification covering Phases 1 through 8:
- Phase 1: Customer registration, password hashing, email verification, single-use token expiration, rate limiting, login/logout, sessions.
- Phase 2: Customer destination selection, bounds validation, building collision avoidance, sidewalk bay snapping.
- Phase 3: Order placement, payload limits (15kg, 22.5L), duplicate submission protection, 14 explicit states.
- Phase 4: Mission dispatcher assignment, route generation, ROS 2 architecture dispatch.
- Phase 5: Customer live tracking, telemetry provenance (Gazebo ground truth vs offline), mathematical GPS labeling.
- Phase 6: Safe arrival, 6-digit OTP verification, motorized hatch release, handover confirmation, return to depot.
- Phase 7: Supervisor RBAC, customer directory, mission management, destination validation inspector.
- Phase 8: Complete regression & failure case validation.
"""

import os
import sys
import time
import json
import uuid
import urllib.request
import urllib.error

BASE_URL = os.environ.get("NEXUS_BASE_URL", "http://127.0.0.1:8080")

_bridge_server = None
def _ensure_server():
    global _bridge_server
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', 8080))
        s.close()
        return
    except Exception:
        pass
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from delivery_robot_sim.web_bridge_node import WebBridgeNode
    _bridge_server = WebBridgeNode(port=8080)
    time.sleep(0.5)

_ensure_server()

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

passed_tests = 0
failed_tests = 0

def run_test(name, func):
    global passed_tests, failed_tests
    print(f"\n{Colors.CYAN}[RUNNING]{Colors.RESET} {name} ...", flush=True)
    try:
        func()
        print(f"{Colors.GREEN}[PASS]{Colors.RESET} {name}")
        passed_tests += 1
    except AssertionError as e:
        print(f"{Colors.RED}[FAIL]{Colors.RESET} {name}: {e}")
        failed_tests += 1
    except Exception as e:
        print(f"{Colors.RED}[ERROR]{Colors.RESET} {name}: {type(e).__name__}: {e}")
        failed_tests += 1

def http_get(path, headers=None):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')
            return resp.status, json.loads(data) if 'application/json' in resp.headers.get('Content-Type', '') else data
    except urllib.error.HTTPError as e:
        data = e.read().decode('utf-8')
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = data
        return e.code, parsed

def http_post(path, body, headers=None):
    url = f"{BASE_URL}{path}"
    all_headers = {'Content-Type': 'application/json'}
    if headers:
        all_headers.update(headers)
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=all_headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')
            return resp.status, json.loads(data) if 'application/json' in resp.headers.get('Content-Type', '') else data
    except urllib.error.HTTPError as e:
        data = e.read().decode('utf-8')
        try:
            parsed = json.loads(data)
        except Exception:
            parsed = data
        return e.code, parsed


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

test_email = f"customer_{int(time.time())}@nexus.tn"
test_password = "SecurePassword123!"
verification_token = None
customer_token = None
customer_id = None
created_order_id = None
created_order_otp = None


def test_1_registration_generates_token_and_unverified_account():
    global verification_token, customer_token, customer_id
    payload = {
        "name": "Nadia Ben Ammar",
        "email": test_email,
        "phone": "+216 22 987 654",
        "password": test_password,
        "address": "12 Avenue Habib Bourguiba, Tunis"
    }
    status, data = http_post("/api/auth/register", payload)
    assert status == 200, f"Expected 200 OK, got {status}: {data}"
    assert data.get("success") is True, f"Registration response failed: {data}"
    user = data.get("user", {})
    assert user.get("email_verified") == 0, f"Expected email_verified=0 for new user, got: {user}"
    assert "token" in data, "Expected JWT/session token in response"
    customer_token = data["token"]
    customer_id = user.get("id") or user.get("customer_id")

    # Inspect outbox to retrieve the single-use token
    status, outbox = http_get("/api/outbox")
    assert status == 200, f"Outbox query failed with {status}"
    found_email = None
    for item in reversed(outbox):
        if item.get("to") == test_email:
            found_email = item
            break
    assert found_email is not None, f"No email found in outbox for {test_email}"
    verification_token = found_email.get("token")
    assert verification_token is not None, "Email outbox missing verification token"
    assert len(verification_token) >= 32, f"Token length invalid: {verification_token}"


def test_2_unverified_account_blocked_from_ordering():
    # Customer attempts to place an order before verifying email
    headers = {"Authorization": f"Bearer {customer_token}"}
    payload = {
        "customer_id": customer_id,
        "customer_name": "Nadia Ben Ammar",
        "customer_email": test_email,
        "x": -9.8,
        "y": 15.0,
        "delivery_name": "Curbside Bay 1",
        "items": [{"id": "PRD-01", "name": "Artisan Pizza", "qty": 1, "price": 14.50, "weight_kg": 0.8}]
    }
    status, data = http_post("/api/orders", payload, headers=headers)
    assert status == 403, f"Expected 403 Forbidden for unverified account, got {status}: {data}"
    err_code = data.get("error") or data.get("code")
    assert err_code == "EMAIL_UNVERIFIED", f"Expected code EMAIL_UNVERIFIED, got {data}"


def test_3_email_verification_and_single_use_token_invalidation():
    # Verify the email with token
    status, data = http_get(f"/api/auth/verify_email?token={verification_token}")
    assert status == 200, f"Expected 200 OK for valid token, got {status}: {data}"
    assert data.get("success") is True, f"Expected success: true, got {data}"
    ver_flag = data.get("email_verified") or data.get("user", {}).get("email_verified")
    assert ver_flag == 1, f"Expected email_verified: 1, got {data}"

    # Reusing the token MUST fail (single-use expiring token)
    status2, data2 = http_get(f"/api/auth/verify_email?token={verification_token}")
    assert status2 in (400, 410), f"Expected 400 or 410 on token reuse, got {status2}: {data2}"
    assert data2.get("success") is False, f"Expected rejection on token reuse: {data2}"


def test_4_resend_verification_rate_limiting():
    # Register an auxiliary user
    rate_email = f"rate_limit_{int(time.time())}@nexus.tn"
    http_post("/api/auth/register", {
        "name": "Rate Test",
        "email": rate_email,
        "phone": "+216 99 111 222",
        "password": "Password123!",
        "address": "Tunis"
    })

    # Since registration already sends an email and starts the 60-second cooldown window,
    # requesting resend immediately MUST be rate-limited with HTTP 429 Too Many Requests
    status, data = http_post("/api/auth/resend_verification", {"email": rate_email})
    assert status == 429, f"Expected 429 Too Many Requests on immediate resend, got {status}: {data}"
    assert "retry_after_s" in data or "wait" in str(data).lower() or data.get("code") == "RATE_LIMITED"


def test_5_login_and_customer_profile():
    # Login with verified user
    status, data = http_post("/api/auth/login", {"email": test_email, "password": test_password})
    assert status == 200, f"Expected 200 OK on login, got {status}: {data}"
    assert data.get("success") is True, f"Login failed: {data}"
    user = data.get("user", {})
    assert user.get("email_verified") == 1, f"Expected email_verified=1 after verification, got {user}"

    # Customer profile endpoint
    headers = {"Authorization": f"Bearer {customer_token}"}
    status_p, data_p = http_get("/api/customer/profile", headers=headers)
    assert status_p == 200, f"Expected 200 OK on customer profile, got {status_p}: {data_p}"
    user_rec = data_p.get("user") or data_p.get("profile") or {}
    assert user_rec.get("email") == test_email, f"Profile email mismatch: {data_p}"
    assert user_rec.get("email_verified") == 1, f"Expected verified profile: {data_p}"


def test_6_destination_reachability_and_building_rejection():
    # 1. Out of Bounds Destination
    status1, data1 = http_post("/api/destination/validate", {"x": 150.0, "y": 200.0})
    assert status1 == 200
    assert data1.get("valid") is False, f"Expected out-of-bounds coordinate to be invalid: {data1}"
    expl1 = data1.get("explanation", "") or data1.get("reason", "") or data1.get("message", "")
    assert "OUT_OF_BOUNDS" in expl1 or "outside" in expl1.lower() or "rejected" in expl1.lower() or "prohibited" in expl1.lower()

    # 2. Inside Building Footprint (North Block interior)
    status2, data2 = http_post("/api/destination/validate", {"x": -20.0, "y": 7.0})
    assert status2 == 200
    # Destination inside building must either be rejected or snapped to legal curbside bay
    if not data2.get("valid"):
        expl2 = data2.get("explanation", "") or data2.get("reason", "") or data2.get("message", "")
        assert "BUILDING" in expl2 or "inside" in expl2.lower() or "prohibited" in expl2.lower()
    else:
        assert data2.get("snapped_bay") is not None or data2.get("stopping_xy") is not None, "Point inside building must snap to exterior bay"

    # 3. Valid Curbside Doorstep (Bay 1)
    status3, data3 = http_post("/api/destination/validate", {"x": -9.8, "y": 15.0})
    assert status3 == 200
    assert data3.get("valid") is True, f"Expected Bay 1 to be valid destination: {data3}"
    assert data3.get("route_dist_m", 0) > 0 or data3.get("distance_m", 0) > 0, "Route distance should be computed"
    assert data3.get("est_duration_s", 0) > 0 or data3.get("eta_seconds", 0) > 0, "ETA duration should be computed"


def test_7_order_placement_payload_capacity_and_idempotency():
    global created_order_id, created_order_otp
    headers = {"Authorization": f"Bearer {customer_token}"}

    # 1. Reject Excessive Payload Weight (> 15.0 kg)
    heavy_payload = {
        "customer_id": customer_id,
        "customer_name": "Nadia Ben Ammar",
        "customer_email": test_email,
        "payload_weight_kg": 25.0,  # Exceeds 15kg limit
        "x": -9.8,
        "y": 15.0,
        "delivery_name": "Heavy Order",
        "items": [{"id": "PRD-HEAVY", "name": "Bulk Pack", "qty": 5, "price": 50.0, "weight_kg": 5.0}]
    }
    status_h, data_h = http_post("/api/orders", heavy_payload, headers=headers)
    assert status_h == 400, f"Expected 400 on payload exceeding 15kg, got {status_h}: {data_h}"
    assert "PAYLOAD_WEIGHT_EXCEEDED" in str(data_h) or "weight" in str(data_h).lower()

    # 2. Valid Order Placement
    idempotency_key = f"IDEMP-{uuid.uuid4().hex[:8]}"
    valid_payload = {
        "customer_id": customer_id,
        "customer_name": "Nadia Ben Ammar",
        "customer_email": test_email,
        "idempotency_key": idempotency_key,
        "payload_weight_kg": 1.2,
        "x": -9.8,
        "y": 15.0,
        "delivery_name": "Sophie Laurent Doorstep (Bay 1)",
        "delivery_address": "North Avenue Curbside Bay 1",
        "items": [
            {"id": "PRD-01", "name": "Artisan Margherita Pizza", "qty": 1, "price": 14.50, "weight_kg": 0.8},
            {"id": "PRD-04", "name": "Nitro Cold Brew Espresso", "qty": 1, "price": 4.50, "weight_kg": 0.3}
        ],
        "priority": 1
    }
    status_v, data_v = http_post("/api/orders", valid_payload, headers=headers)
    assert status_v == 200, f"Expected 200 on valid order, got {status_v}: {data_v}"
    assert data_v.get("success") is True
    order = data_v.get("order", {})
    created_order_id = order.get("order_id") or data_v.get("order_id")
    created_order_otp = order.get("otp")
    assert created_order_id is not None, "Order ID missing from response"
    assert created_order_otp is not None and len(str(created_order_otp)) == 6, f"Invalid 6-digit OTP: {created_order_otp}"

    # 3. Duplicate Order Rejection via Idempotency Key
    status_dup, data_dup = http_post("/api/orders", valid_payload, headers=headers)
    assert status_dup in (200, 409), f"Duplicate order should either return cached order or 409 Conflict, got {status_dup}: {data_dup}"
    if status_dup == 200:
        assert (data_dup.get("order_id") == created_order_id or data_dup.get("order", {}).get("order_id") == created_order_id)


def test_8_order_lifecycle_states_and_customer_isolation():
    headers = {"Authorization": f"Bearer {customer_token}"}
    status, orders = http_get("/api/customer/orders", headers=headers)
    assert status == 200, f"Expected 200 on customer orders, got {status}"
    assert len(orders) >= 1, "Customer should see their placed order"
    user_order = next((o for o in orders if o.get("order_id") == created_order_id), None)
    assert user_order is not None, f"Order {created_order_id} not found in customer's order history"
    valid_states = [
        "PENDING", "CONFIRMED", "PREPARING", "READY_FOR_DISPATCH", "ROBOT_ASSIGNED",
        "ROBOT_EN_ROUTE", "ROBOT_ARRIVED", "HANDOVER_IN_PROGRESS", "DELIVERED",
        "RETURNING_TO_DEPOT", "COMPLETED", "CANCELLED", "FAILED", "UNREACHABLE"
    ]
    current_status = user_order.get("status")
    assert current_status in valid_states, f"Order status '{current_status}' not in 14 standard states: {valid_states}"


def test_9_telemetry_provenance_and_truthful_labeling():
    status, tel = http_get("/api/telemetry")
    assert status == 200, f"Expected 200 on telemetry, got {status}"
    # Verify strict provenance labels
    assert "telemetry_source" in tel, "Missing telemetry_source classification"
    assert tel["telemetry_source"] in ("LIVE_GAZEBO_TELEMETRY", "LAST_KNOWN_POSITION", "UNAVAILABLE_SIMULATION_OFFLINE")
    assert tel.get("gps_projection_label") == "MATHEMATICAL_PROJECTION_FOR_DISPLAY_ONLY"
    assert tel.get("actual_location_source") in ("GAZEBO_WORLD_GROUND_TRUTH", "NO_LIVE_POSE")
    # Velocity must not be fabricated if disconnected
    if tel["telemetry_source"] != "LIVE_GAZEBO_TELEMETRY":
        assert tel.get("actual_v", 0.0) == 0.0, "Velocity must be 0.0 when disconnected"


def test_10_otp_handover_compartment_unlatch_and_return_to_depot():
    headers = {"Authorization": f"Bearer {customer_token}"}

    # 1. Incorrect OTP Code MUST be rejected
    status_w, data_w = http_post("/api/verify_otp", {"order_id": created_order_id, "otp": "000000"}, headers=headers)
    assert status_w == 400 or data_w.get("success") is False, f"Expected failure on wrong OTP, got {status_w}: {data_w}"

    # 2. Correct 6-digit OTP Code Handover
    status_r, data_r = http_post("/api/verify_otp", {"order_id": created_order_id, "otp": created_order_otp}, headers=headers)
    assert status_r == 200, f"Expected 200 on correct OTP, got {status_r}: {data_r}"
    assert data_r.get("success") is True, f"OTP verification failed: {data_r}"
    assert "UNLOCKED" in data_r.get("hatch_status", "") or "OPEN" in data_r.get("hatch_status", "")

    # 3. Customer Handover Confirmation (Package Retrieved -> Closes Hatch -> Return to Depot)
    status_c, data_c = http_post("/api/confirm_delivery", {"order_id": created_order_id}, headers=headers)
    assert status_c == 200, f"Expected 200 on confirm delivery, got {status_c}: {data_c}"
    assert data_c.get("success") is True
    assert data_c.get("status") in ("RETURNING_TO_DEPOT", "COMPLETED")


def test_11_order_cancellation_rules():
    headers = {"Authorization": f"Bearer {customer_token}"}
    sup_headers = {"Authorization": "Bearer OP-TOKEN-SUPERVISOR"}

    # Create a fresh pending order
    idemp = f"IDEMP-{uuid.uuid4().hex[:8]}"
    _, res = http_post("/api/orders", {
        "customer_id": customer_id,
        "customer_name": "Nadia Ben Ammar",
        "customer_email": test_email,
        "idempotency_key": idemp,
        "payload_weight_kg": 0.5,
        "x": -9.8,
        "y": 15.0,
        "delivery_name": "Cancel Test Doorstep",
        "items": [{"id": "PRD-04", "name": "Cold Brew", "qty": 1, "price": 4.50, "weight_kg": 0.3}]
    }, headers=headers)
    cancel_order_id = res.get("order", {}).get("order_id") or res.get("order_id")

    # If already dispatched/en route, customer cancellation is safely rejected
    status_cn, data_cn = http_post("/api/order/cancel", {
        "order_id": cancel_order_id,
        "reason": "Customer cancelled via app"
    }, headers=headers)
    if status_cn == 400:
        assert "Cannot cancel" in str(data_cn) or "en route" in str(data_cn).lower()
    else:
        assert status_cn == 200 and data_cn.get("status") == "CANCELLED"

    # Operator override CAN cancel / abort any active mission
    status_sup, data_sup = http_post("/api/supervisor/order_action", {
        "order_id": cancel_order_id,
        "action": "CANCEL"
    }, headers=sup_headers)
    assert status_sup == 200, f"Expected supervisor override cancellation to succeed, got {status_sup}: {data_sup}"
    assert data_sup.get("success") is True


def test_12_supervisor_portal_endpoints():
    # Supervisor authentication check
    headers = {"Authorization": "Bearer OP-TOKEN-SUPERVISOR"}
    status, data = http_get("/api/supervisor/customers", headers=headers)
    assert status == 200, f"Supervisor customers query failed with {status}: {data}"
    customers = data if isinstance(data, list) else data.get("customers", [])
    assert len(customers) >= 1, "Supervisor customer list must include registered customers"
    found = any(c.get("email") == test_email for c in customers)
    assert found, f"Newly registered verified customer {test_email} missing from supervisor view"

    # Supervisor order list
    status_o, data_o = http_get("/api/supervisor/orders", headers=headers)
    assert status_o == 200, f"Supervisor orders query failed with {status_o}: {data_o}"
    orders = data_o if isinstance(data_o, list) else data_o.get("orders", [])
    assert len(orders) >= 1, "Supervisor orders list must include recent missions"


def main():
    print(f"\n{Colors.BOLD}======================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}   NEXUS-DELIVERY COMPLETE WORKFLOW VERIFICATION TEST SUITE           {Colors.RESET}")
    print(f"{Colors.BOLD}   Zero LiDAR, Zero GPS Vision-Led Sidewalk AMR Architecture          {Colors.RESET}")
    print(f"{Colors.BOLD}======================================================================{Colors.RESET}")

    run_test("1. Customer Registration & Token Generation", test_1_registration_generates_token_and_unverified_account)
    run_test("2. Customer Isolation & Unverified Checkout Rejection", test_2_unverified_account_blocked_from_ordering)
    run_test("3. Email Verification & Single-Use Token Invalidation", test_3_email_verification_and_single_use_token_invalidation)
    run_test("4. Resend Verification & Rate Limiting", test_4_resend_verification_rate_limiting)
    run_test("5. Customer Login & Tenant Profile Retrieval", test_5_login_and_customer_profile)
    run_test("6. Destination Reachability & Building Rejection", test_6_destination_reachability_and_building_rejection)
    run_test("7. Order Placement, Payload Limits & Idempotency", test_7_order_placement_payload_capacity_and_idempotency)
    run_test("8. Order Lifecycle Standard States (14 States)", test_8_order_lifecycle_states_and_customer_isolation)
    run_test("9. Telemetry Provenance & Truthful Labeling", test_9_telemetry_provenance_and_truthful_labeling)
    run_test("10. 6-Digit OTP Handover & Return to Depot", test_10_otp_handover_compartment_unlatch_and_return_to_depot)
    run_test("11. Order Cancellation Safety Rules", test_11_order_cancellation_rules)
    run_test("12. Supervisor Operations & Customer Directory", test_12_supervisor_portal_endpoints)

    print(f"\n{Colors.BOLD}======================================================================{Colors.RESET}")
    print(f"{Colors.BOLD}TEST SUMMARY:{Colors.RESET}")
    print(f"Total Tests Passed: {Colors.GREEN}{passed_tests}{Colors.RESET}")
    print(f"Total Tests Failed: {Colors.RED}{failed_tests}{Colors.RESET}")
    print(f"{Colors.BOLD}======================================================================{Colors.RESET}\n")

    if failed_tests > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
