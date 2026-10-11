import codecs
import json


def encode_event(event: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\nid: {data['run_id']}:{data['seq']}\ndata: {payload}\n\n"


class SSEDecoder:
    """Small test/client decoder that accepts arbitrary UTF-8 transport chunks."""

    def __init__(self):
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.buffer = ""

    def feed(self, chunk: bytes) -> list[dict]:
        self.buffer += self.decoder.decode(chunk)
        self.buffer = self.buffer.replace("\r\n", "\n")
        events = []
        while "\n\n" in self.buffer:
            frame, self.buffer = self.buffer.split("\n\n", 1)
            fields = {}
            data = []
            for line in frame.splitlines():
                key, separator, value = line.partition(":")
                if separator and key in {"event", "id", "data"}:
                    if key == "data":
                        data.append(value.removeprefix(" "))
                    else:
                        fields[key] = value.strip()
            if data:
                fields["data"] = json.loads("\n".join(data))
                events.append(fields)
        return events
