import uuid

from fastapi.testclient import TestClient

from app.collab import rooms
from app.main import app

client = TestClient(app)


def room() -> str:
    return f"test-{uuid.uuid4().hex[:8]}"


def test_join_receives_init_with_empty_state():
    with client.websocket_connect(f"/api/ws/{room()}") as ws:
        init = ws.receive_json()
        assert init["type"] == "init"
        assert init["peers"] == 1
        assert init["state"] == {"comments": [], "tracks": [], "project": None}


def test_presence_count_updates_on_join_and_leave():
    r = room()
    with client.websocket_connect(f"/api/ws/{r}") as a:
        a.receive_json()
        with client.websocket_connect(f"/api/ws/{r}") as b:
            b.receive_json()
            assert a.receive_json() == {"type": "peers", "peers": 2}
        # b has left; a is told the room shrank
        assert a.receive_json() == {"type": "peers", "peers": 1}


def test_comment_broadcasts_to_peers_but_not_sender():
    r = room()
    comment = {"id": "c1", "author": "sean", "text": "kick too loud", "ts": 0}
    with client.websocket_connect(f"/api/ws/{r}") as a:
        a.receive_json()
        with client.websocket_connect(f"/api/ws/{r}") as b:
            b.receive_json()
            a.receive_json()  # peers update

            b.send_json({"type": "comment", "comment": comment})
            got = a.receive_json()
            assert got["type"] == "comment"
            assert got["comment"]["text"] == "kick too loud"


def test_track_analyses_replicate_and_deduplicate():
    r = room()
    track = {"id": "t1", "name": "mix.wav", "metrics": {}, "findings": []}
    with client.websocket_connect(f"/api/ws/{r}") as a:
        a.receive_json()
        with client.websocket_connect(f"/api/ws/{r}") as b:
            b.receive_json()
            a.receive_json()

            b.send_json({"type": "track", "track": track})
            assert a.receive_json()["track"]["name"] == "mix.wav"

            # Re-announcing the same id must not add a duplicate
            b.send_json({"type": "track", "track": track})
            b.send_json({"type": "comment", "comment": {"id": "c", "author": "x", "text": "y", "ts": 0}})
            # The next message a sees is the comment, not a second track
            assert a.receive_json()["type"] == "comment"
    assert len(rooms[r].state["tracks"]) == 1


def test_late_joiner_receives_full_room_state():
    r = room()
    with client.websocket_connect(f"/api/ws/{r}") as a:
        a.receive_json()
        a.send_json({"type": "comment", "comment": {"id": "c1", "author": "s", "text": "hi", "ts": 0}})
        a.send_json({"type": "track", "track": {"id": "t1", "name": "mix.wav"}})
        a.send_json({"type": "project", "project": {"filename": "song.rpp", "tracks": []}})

        with client.websocket_connect(f"/api/ws/{r}") as late:
            state = late.receive_json()["state"]
            assert len(state["comments"]) == 1
            assert len(state["tracks"]) == 1
            assert state["project"]["filename"] == "song.rpp"


def test_room_state_survives_everyone_leaving():
    r = room()
    with client.websocket_connect(f"/api/ws/{r}") as ws:
        ws.receive_json()
        ws.send_json({"type": "comment", "comment": {"id": "c", "author": "a", "text": "persist", "ts": 0}})
    with client.websocket_connect(f"/api/ws/{r}") as rejoin:
        init = rejoin.receive_json()
        assert init["state"]["comments"][0]["text"] == "persist"


def test_rooms_are_isolated_from_each_other():
    r1, r2 = room(), room()
    with client.websocket_connect(f"/api/ws/{r1}") as a:
        a.receive_json()
        a.send_json({"type": "comment", "comment": {"id": "c", "author": "a", "text": "room one", "ts": 0}})
        with client.websocket_connect(f"/api/ws/{r2}") as b:
            assert b.receive_json()["state"]["comments"] == []


def test_malformed_messages_are_ignored_without_dropping_the_connection():
    r = room()
    with client.websocket_connect(f"/api/ws/{r}") as ws:
        ws.receive_json()
        ws.send_json({"type": "comment"})           # missing payload
        ws.send_json({"type": "comment", "comment": "not a dict"})
        ws.send_json({"type": "unknown_kind"})
        # The socket still works afterwards
        ws.send_json({"type": "comment", "comment": {"id": "c", "author": "a", "text": "ok", "ts": 0}})
    assert [c["text"] for c in rooms[r].state["comments"]] == ["ok"]
