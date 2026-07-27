from app.services import http_transport


def test_open_uses_a_fresh_opener_for_each_request(monkeypatch) -> None:
    opened = []

    class FakeOpener:
        def __init__(self, sequence: int) -> None:
            self.sequence = sequence

        def open(self, request, timeout):
            opened.append((self.sequence, request, timeout))
            return f"response-{self.sequence}"

    sequence = 0

    def fake_build_opener():
        nonlocal sequence
        sequence += 1
        return FakeOpener(sequence)

    monkeypatch.setattr(http_transport, "build_opener", fake_build_opener)

    assert http_transport.open_with_current_network_settings("one", 10) == "response-1"
    assert http_transport.open_with_current_network_settings("two", 20) == "response-2"
    assert opened == [(1, "one", 10), (2, "two", 20)]
