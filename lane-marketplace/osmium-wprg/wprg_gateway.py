"""Enterprise Webhook Ingestion & Payment Reconciliation Gateway (WPRG)
Vendor: Xsolve Systems
Architectural Standard: Constant-time verification, strict idempotency, monotonic state latching.
"""

import hmac
import hashlib
import time
import json
import threading
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass, field

class PaymentState(Enum):
    INITIATED = "INITIATED"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    SETTLED = "SETTLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"

# Valid forward transitions in the payment lifecycle state machine
VALID_TRANSITIONS = {
    PaymentState.INITIATED: {PaymentState.AUTHORIZED, PaymentState.FAILED},
    PaymentState.AUTHORIZED: {PaymentState.CAPTURED, PaymentState.FAILED},
    PaymentState.CAPTURED: {PaymentState.SETTLED, PaymentState.REFUNDED},
    PaymentState.SETTLED: {PaymentState.REFUNDED},
    PaymentState.REFUNDED: set(),
    PaymentState.FAILED: set()
}

@dataclass
class WebhookEvent:
    event_id: str
    order_id: str
    target_state: PaymentState
    amount_cents: int
    currency: str
    timestamp: float
    payload: Dict[str, Any]
    signature: str

@dataclass
class ReconciliationLedgerEntry:
    order_id: str
    current_state: PaymentState
    amount_credited_cents: int
    currency: str
    transition_history: List[Tuple[PaymentState, float]] = field(default_factory=list)
    version: int = 1

class WPRGCoreEngine:
    """Core idempotent webhook ingestion and state reconciliation engine."""
    
    def __init__(self, webhook_secret: str, max_drift_seconds: int = 300):
        self.webhook_secret = webhook_secret.encode('utf-8')
        self.max_drift_seconds = max_drift_seconds
        self._lock = threading.RLock()
        
        # Idempotency cache: event_id -> (timestamp, status, response)
        self._idempotency_store: Dict[str, Dict[str, Any]] = {}
        
        # Core accounting ledger: order_id -> ReconciliationLedgerEntry
        self._ledger: Dict[str, ReconciliationLedgerEntry] = {}
        
        # Out-of-order staging queue: order_id -> List[WebhookEvent]
        self._staging_buffer: Dict[str, List[WebhookEvent]] = {}
        
        # Dead Letter Queue (DLQ): List of failed events with retry metadata
        self.dead_letter_queue: List[Dict[str, Any]] = []

    def verify_signature(self, raw_body: bytes, signature_header: str, timestamp_header: str) -> Tuple[bool, str]:
        """Constant-time HMAC-SHA256 signature and timestamp replay validation."""
        if not signature_header or not timestamp_header:
            return False, "Missing signature or timestamp header"
        
        try:
            event_time = float(timestamp_header)
        except ValueError:
            return False, "Malformed timestamp header"
            
        now = time.time()
        if abs(now - event_time) > self.max_drift_seconds:
            return False, f"Timestamp drift exceeds tolerance ({abs(now - event_time):.1f}s > {self.max_drift_seconds}s)"
            
        # Construct signing payload: timestamp.raw_body (RFC standard / Stripe / Razorpay format)
        payload_to_sign = f"{timestamp_header}.".encode('utf-8') + raw_body
        expected_sig = hmac.new(self.webhook_secret, payload_to_sign, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature_header):
            return False, "Cryptographic signature mismatch"
            
        return True, "Signature verified"

    def process_incoming_webhook(self, raw_body: bytes, signature: str, timestamp_str: str, 
                                 simulated_downstream_failure: bool = False, max_retries: int = 3) -> Dict[str, Any]:
        """Synchronous ingestion gate: Verifies, checks idempotency latch, routes to ledger."""
        t_start = time.perf_counter()
        
        # 1. Cryptographic Authentication & Replay Defense
        is_valid, reason = self.verify_signature(raw_body, signature, timestamp_str)
        if not is_valid:
            latency_ms = (time.perf_counter() - t_start) * 1000
            return {
                "status_code": 401 if "signature" in reason.lower() else 400,
                "status": "REJECTED",
                "error": reason,
                "latency_ms": latency_ms
            }

        try:
            data = json.loads(raw_body.decode('utf-8'))
            event = WebhookEvent(
                event_id=data["event_id"],
                order_id=data["order_id"],
                target_state=PaymentState[data["state"]],
                amount_cents=data["amount_cents"],
                currency=data["currency"],
                timestamp=float(timestamp_str),
                payload=data,
                signature=signature
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t_start) * 1000
            return {
                "status_code": 422,
                "status": "UNPROCESSABLE_ENTITY",
                "error": f"Invalid payload schema: {str(e)}",
                "latency_ms": latency_ms
            }

        # 2. Strict Distributed Idempotency Latch (Atomic Lock)
        with self._lock:
            if event.event_id in self._idempotency_store:
                cached = self._idempotency_store[event.event_id]
                latency_ms = (time.perf_counter() - t_start) * 1000
                return {
                    "status_code": 200,
                    "status": "IDEMPOTENT_HIT",
                    "message": "Duplicate event suppressed. Previous resolution returned.",
                    "previous_resolution": cached,
                    "double_credit_prevented": True,
                    "latency_ms": latency_ms
                }
            
            # Acquire lock
            self._idempotency_store[event.event_id] = {
                "timestamp": time.time(),
                "status": "PROCESSING",
                "order_id": event.order_id
            }

        # 3. Downstream Execution & Fault Tolerance
        if simulated_downstream_failure:
            with self._lock:
                self.dead_letter_queue.append({
                    "event": event,
                    "attempts": max_retries,
                    "reason": "Simulated downstream target unavailable",
                    "quarantined_at": time.time()
                })
                self._idempotency_store[event.event_id]["status"] = "DEAD_LETTER_QUARANTINED"
            latency_ms = (time.perf_counter() - t_start) * 1000
            return {
                "status_code": 202,
                "status": "ROUTED_TO_DLQ",
                "message": "Downstream failure caught. Quarantined in DLQ for backoff replay.",
                "latency_ms": latency_ms
            }

        # 4. State Machine Transition & Out-of-Order Recovery
        with self._lock:
            res = self._apply_state_transition(event)
            self._idempotency_store[event.event_id]["status"] = "SETTLED"
            self._idempotency_store[event.event_id]["result"] = res
            
        latency_ms = (time.perf_counter() - t_start) * 1000
        return {
            "status_code": 200,
            "status": "PROCESSED",
            "resolution": res,
            "latency_ms": latency_ms
        }

    def _apply_state_transition(self, event: WebhookEvent) -> Dict[str, Any]:
        """Applies monotonic state update or stages out-of-order events."""
        order_id = event.order_id
        
        # New order initialization
        if order_id not in self._ledger:
            if event.target_state == PaymentState.INITIATED:
                entry = ReconciliationLedgerEntry(
                    order_id=order_id,
                    current_state=PaymentState.INITIATED,
                    amount_credited_cents=0,
                    currency=event.currency,
                    transition_history=[(PaymentState.INITIATED, time.time())]
                )
                self._ledger[order_id] = entry
                self._drain_staging_buffer(order_id)
                return {"order_id": order_id, "state": "INITIATED", "credited": 0}
            else:
                # Out-of-order arrival (e.g. CAPTURED arrived before INITIATED)
                if order_id not in self._staging_buffer:
                    self._staging_buffer[order_id] = []
                self._staging_buffer[order_id].append(event)
                return {
                    "order_id": order_id,
                    "state": "STAGED_OUT_OF_ORDER",
                    "target_state": event.target_state.value,
                    "note": "Buffered until initial order state manifests"
                }

        entry = self._ledger[order_id]
        current = entry.current_state
        target = event.target_state

        # Check valid forward progression
        if target in VALID_TRANSITIONS.get(current, set()):
            entry.current_state = target
            entry.version += 1
            entry.transition_history.append((target, time.time()))
            
            # Settlement / credit event
            if target == PaymentState.SETTLED:
                entry.amount_credited_cents = event.amount_cents
            elif target == PaymentState.REFUNDED:
                entry.amount_credited_cents = 0

            # Drain any subsequent buffered events
            self._drain_staging_buffer(order_id)
            return {
                "order_id": order_id,
                "state": target.value,
                "credited_cents": entry.amount_credited_cents,
                "version": entry.version
            }
        else:
            # Invalid backwards or illegal skip
            if order_id not in self._staging_buffer:
                self._staging_buffer[order_id] = []
            self._staging_buffer[order_id].append(event)
            return {
                "order_id": order_id,
                "state": current.value,
                "buffered_out_of_order": target.value,
                "note": f"Cannot transition directly from {current.value} to {target.value}. Staged in buffer."
            }

    def _drain_staging_buffer(self, order_id: str):
        """Recursively checks if buffered out-of-order events can now be executed."""
        if order_id not in self._staging_buffer or not self._staging_buffer[order_id]:
            return
            
        buffer = self._staging_buffer[order_id]
        remaining = []
        for pending_event in buffer:
            entry = self._ledger.get(order_id)
            if entry and pending_event.target_state in VALID_TRANSITIONS.get(entry.current_state, set()):
                entry.current_state = pending_event.target_state
                entry.version += 1
                entry.transition_history.append((pending_event.target_state, time.time()))
                if pending_event.target_state == PaymentState.SETTLED:
                    entry.amount_credited_cents = pending_event.amount_cents
                elif pending_event.target_state == PaymentState.REFUNDED:
                    entry.amount_credited_cents = 0
            else:
                remaining.append(pending_event)
        self._staging_buffer[order_id] = remaining

    def get_ledger_state(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._ledger.get(order_id)
            if not entry:
                return None
            return {
                "order_id": entry.order_id,
                "current_state": entry.current_state.value,
                "amount_credited_cents": entry.amount_credited_cents,
                "currency": entry.currency,
                "version": entry.version,
                "history": [(s.value, t) for s, t in entry.transition_history]
            }
