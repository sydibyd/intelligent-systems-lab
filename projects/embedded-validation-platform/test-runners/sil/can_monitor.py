class CANMonitor:
    def __init__(self, timeout_ms=500):
        self.timeout_ms = timeout_ms
        self.last_message_ms = 0

    def receive_message(self, timestamp_ms):
        self.last_message_ms = timestamp_ms

    def communication_lost(self, current_time_ms):
        elapsed = current_time_ms - self.last_message_ms
        return elapsed >= self.timeout_ms
