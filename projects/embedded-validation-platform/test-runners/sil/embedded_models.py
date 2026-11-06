class StartupController:
    def initialize(self, voltage, temperature):
        if voltage < 9.0:
            return "ERROR"
        if temperature > 85.0:
            return "ERROR"
        return "READY"


class CANTransmitter:
    def __init__(self):
        self.sent_messages = []

    def send(self, message_id, payload):
        if not 0 <= message_id <= 0x7FF:
            return False

        if len(payload) > 8:
            return False

        self.sent_messages.append({
            "id": message_id,
            "payload": payload
        })

        return True


class SOCModel:
    def calculate(self, remaining_capacity, nominal_capacity):
        if nominal_capacity <= 0:
            raise ValueError("Invalid nominal capacity")

        soc = 100 * remaining_capacity / nominal_capacity

        return max(0, min(100, soc))
