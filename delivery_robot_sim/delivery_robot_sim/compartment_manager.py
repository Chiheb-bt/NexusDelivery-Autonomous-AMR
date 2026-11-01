"""Secure Delivery Compartment & Customer Authentication Manager.

Implements:
- Physical cargo compartment abstraction (solenoid lock/unlock states).
- Dynamic 6-digit One-Time Password (OTP) and cryptographic token generation.
- Token expiration (300s window) and replay protection.
- Customer verification workflow before hatch unlocking.
- Tamper detection and anti-tamper lockouts after 3 invalid attempts.
- Idempotent delivery verification.
"""

import hashlib
import hmac
import time
from enum import Enum
from typing import Dict, Optional, Tuple


class CompartmentLockState(str, Enum):
    LOCKED = 'LOCKED'
    UNLOCKED_PICKUP = 'UNLOCKED_PICKUP'
    LOCKED_IN_TRANSIT = 'LOCKED_IN_TRANSIT'
    CUSTOMER_VERIFYING = 'CUSTOMER_VERIFYING'
    UNLOCKED_DELIVERY = 'UNLOCKED_DELIVERY'
    DELIVERY_VERIFIED = 'DELIVERY_VERIFIED'
    TAMPER_ALERT = 'TAMPER_ALERT'


class CompartmentManager:
    """Manages physical cargo compartments, solenoid locks, and customer authentication."""

    def __init__(self, secret_key: str = 'rdsim_secure_fleet_salt_2026', token_validity_s: float = 300.0):
        self.secret_key = secret_key.encode('utf-8')
        self.token_validity_s = token_validity_s

        # Map order_id -> compartment details
        self.compartments: Dict[str, dict] = {
            'COMPARTMENT_1': {'status': CompartmentLockState.LOCKED, 'package_id': None, 'order_id': None},
            'COMPARTMENT_2': {'status': CompartmentLockState.LOCKED, 'package_id': None, 'order_id': None},
        }
        self.active_tokens: Dict[str, dict] = {}   # order_id -> {otp, token_hash, expires_at, attempts}
        self.used_tokens: set = set()               # Set of consumed token hashes (Replay protection)

    def assign_package(self, compartment_id: str, package_id: str, order_id: str) -> bool:
        """Assign package to a compartment at depot pickup."""
        if compartment_id not in self.compartments:
            return False
        comp = self.compartments[compartment_id]
        comp['package_id'] = package_id
        comp['order_id'] = order_id
        comp['status'] = CompartmentLockState.LOCKED_IN_TRANSIT
        return True

    def generate_delivery_token(self, order_id: str, now: float) -> Tuple[str, str]:
        """Generate a deterministic 6-digit OTP and HMAC token upon arrival at client."""
        # Generate numeric 6-digit OTP derived from HMAC of order_id and timestamp
        mac = hmac.new(self.secret_key, f'{order_id}:{int(now)}'.encode('utf-8'), hashlib.sha256).hexdigest()
        otp = str(int(mac[:8], 16) % 900000 + 100000)  # 6-digit code between 100000 and 999999
        token_hash = hashlib.sha256(f'{order_id}:{otp}'.encode('utf-8')).hexdigest()

        self.active_tokens[order_id] = {
            'otp': otp,
            'token_hash': token_hash,
            'expires_at': now + self.token_validity_s,
            'attempts': 0
        }
        return otp, token_hash

    def authenticate_customer(self, order_id: str, candidate_otp: str, now: float) -> Tuple[bool, str]:
        """Verify the candidate OTP entered by the customer."""
        if order_id not in self.active_tokens:
            return False, 'NO_ACTIVE_TOKEN_FOR_ORDER'

        token_info = self.active_tokens[order_id]

        # Check token expiration
        if now > token_info['expires_at']:
            return False, 'TOKEN_EXPIRED'

        # Check replay protection
        if token_info['token_hash'] in self.used_tokens:
            return False, 'TOKEN_ALREADY_USED'

        # Check tamper lockout
        if token_info['attempts'] >= 3:
            self._trigger_tamper_alert(order_id)
            return False, 'TAMPER_ALERT_MAX_ATTEMPTS_EXCEEDED'

        # Verify code
        if candidate_otp.strip() == token_info['otp']:
            # Success!
            self.used_tokens.add(token_info['token_hash'])
            self._unlock_for_order(order_id)
            return True, 'AUTHENTICATION_SUCCESS'
        else:
            token_info['attempts'] += 1
            if token_info['attempts'] >= 3:
                self._trigger_tamper_alert(order_id)
                return False, 'TAMPER_ALERT_MAX_ATTEMPTS_EXCEEDED'
            return False, f'INVALID_OTP (Attempts remaining: {3 - token_info["attempts"]})'

    def _unlock_for_order(self, order_id: str):
        for comp_id, comp in self.compartments.items():
            if comp['order_id'] == order_id:
                comp['status'] = CompartmentLockState.UNLOCKED_DELIVERY

    def _trigger_tamper_alert(self, order_id: str):
        for comp_id, comp in self.compartments.items():
            if comp['order_id'] == order_id:
                comp['status'] = CompartmentLockState.TAMPER_ALERT

    def confirm_compartment_closed_and_locked(self, order_id: str) -> bool:
        """Confirm customer has closed the hatch and lock bolt is engaged."""
        for comp_id, comp in self.compartments.items():
            if comp['order_id'] == order_id:
                comp['status'] = CompartmentLockState.DELIVERY_VERIFIED
                comp['package_id'] = None
                return True
        return False

    def get_compartment_status(self, order_id: str) -> str:
        for comp in self.compartments.values():
            if comp['order_id'] == order_id:
                return comp['status'].value
        return CompartmentLockState.LOCKED.value
