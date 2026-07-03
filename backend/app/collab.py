"""Real-time collaboration: WebSocket rooms with shared session state.

Rooms are in-memory: joined clients receive the current state (analyses,
project, comments), and every mutation broadcasts to the other members.
Audio itself never syncs — only analysis results and comments — so the
payloads stay small and nothing heavy crosses the wire.
"""

from fastapi import WebSocket, WebSocketDisconnect


class Room:
    def __init__(self) -> None:
        self.clients: set[WebSocket] = set()
        self.state: dict = {"comments": [], "tracks": [], "project": None}


rooms: dict[str, Room] = {}


async def _broadcast(room: Room, payload: dict, exclude: WebSocket | None = None) -> None:
    dead = []
    for client in room.clients:
        if client is exclude:
            continue
        try:
            await client.send_json(payload)
        except Exception:
            dead.append(client)
    for client in dead:
        room.clients.discard(client)


async def handle_session(room_id: str, ws: WebSocket) -> None:
    await ws.accept()
    room = rooms.setdefault(room_id, Room())
    room.clients.add(ws)
    await ws.send_json(
        {"type": "init", "state": room.state, "peers": len(room.clients)}
    )
    await _broadcast(room, {"type": "peers", "peers": len(room.clients)}, exclude=ws)
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "comment" and isinstance(msg.get("comment"), dict):
                room.state["comments"].append(msg["comment"])
                await _broadcast(room, msg, exclude=ws)
            elif kind == "track" and isinstance(msg.get("track"), dict):
                track_id = msg["track"].get("id")
                if not any(t.get("id") == track_id for t in room.state["tracks"]):
                    room.state["tracks"].append(msg["track"])
                    await _broadcast(room, msg, exclude=ws)
            elif kind == "project" and isinstance(msg.get("project"), dict):
                room.state["project"] = msg["project"]
                await _broadcast(room, msg, exclude=ws)
    except WebSocketDisconnect:
        pass
    finally:
        room.clients.discard(ws)
        # State survives everyone leaving so a link keeps working mid-session.
        await _broadcast(room, {"type": "peers", "peers": len(room.clients)})
