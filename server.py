from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import os
import uvicorn

app = FastAPI()
users_db = {"admin": "123"}
active_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_user = None

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "LOGIN":
                username = message.get("username")
                password = message.get("password")
                if username in users_db and users_db[username] == password:
                    current_user = username
                    active_connections[username] = websocket
                    await websocket.send_text(json.dumps({"type": "AUTH_SUCCESS", "username": username}))
                    await broadcast({"type": "PLAYER_JOINED", "username": username})
                else:
                    await websocket.send_text(json.dumps({"type": "AUTH_ERROR", "message": "Невірний логін або пароль"}))

            elif msg_type == "REGISTER":
                username = message.get("username")
                password = message.get("password")
                if username in users_db:
                    await websocket.send_text(json.dumps({"type": "AUTH_ERROR", "message": "Такий логін вже існує"}))
                else:
                    users_db[username] = password
                    await websocket.send_text(json.dumps({"type": "REG_SUCCESS", "message": "Реєстрація успішна!"}))

            elif current_user:
                # ПЕРЕСИЛАЄМО РУХИ БІТИ ТА ШАЙБИ
                if msg_type in ["MOVE_PADDLE", "GAME_STATE"]:
                    message["username"] = current_user
                    await broadcast(message)
                # ПРАНК
                elif msg_type == "PRANK":
                    target = message.get("target")
                    if target in active_connections:
                        await active_connections[target].send_text(json.dumps({"type": "DO_PRANK"}))

    except WebSocketDisconnect:
        if current_user in active_connections:
            del active_connections[current_user]
            await broadcast({"type": "PLAYER_LEFT", "username": current_user})

async def broadcast(message: dict):
    for connection in active_connections.values():
        try:
            await connection.send_text(json.dumps(message))
        except:
            pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
