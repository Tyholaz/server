from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import os
import uvicorn

app = FastAPI()

# База даних (у пам'яті)
users_db = {
    "admin": "123"  # Логін: admin, Пароль: 123
}

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
                elif not username or not password:
                    await websocket.send_text(json.dumps({"type": "AUTH_ERROR", "message": "Логін та пароль не можуть бути порожніми"}))
                else:
                    users_db[username] = password
                    await websocket.send_text(json.dumps({"type": "REG_SUCCESS", "message": "Реєстрація успішна! Тепер увійдіть."}))

            elif current_user:
                if msg_type == "PRANK":
                    target_user = message.get("target")
                    if target_user in active_connections:
                        await active_connections[target_user].send_text(json.dumps({"type": "DO_PRANK"}))
                elif msg_type == "SCORE":
                    await broadcast({"type": "SCORE_UPDATE", "username": current_user, "score": message["score"]})

    except WebSocketDisconnect:
        if current_user and current_user in active_connections:
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