"""Crea en HA el usuario `despensa` (no administrador, solo red local) y saca su token de 10 años.

  ADMIN_TOKEN=... python3 crear_usuario_ha.py [https://homeassistant.jarclab.com]

La contraseña es aleatoria y no se guarda: al usuario solo se le usa por el token,
que sale por la salida estándar para ponerlo en HA_TOKEN de /opt/despensa/.env.
Si el usuario ya existe no toca nada (bórralo antes en Ajustes > Personas > Usuarios).
Necesita aiohttp (el venv de HA lo trae; si no, pip install aiohttp).
"""
import asyncio, os, secrets, sys
import aiohttp
U = (sys.argv[1] if len(sys.argv) > 1 else "https://homeassistant.jarclab.com").rstrip("/")
WS = U.replace("http", "ws", 1) + "/api/websocket"
ADMIN = os.environ["ADMIN_TOKEN"]
async def ws_call(s, token, msgs):
    ws = await s.ws_connect(WS); await ws.receive_json()
    await ws.send_json({"type": "auth", "access_token": token}); assert (await ws.receive_json())["type"] == "auth_ok"
    out = []
    for i, m in enumerate(msgs, 1):
        await ws.send_json({"id": i, **m})
        while True:
            r = await ws.receive_json()
            if r.get("id") == i: out.append(r); break
    await ws.close(); return out
async def main():
    async with aiohttp.ClientSession() as s:
        (usuarios,) = await ws_call(s, ADMIN, [{"type": "config/auth/list"}])
        if any(u["name"] == "despensa" for u in usuarios["result"]):
            print("ya existe el usuario despensa: no toco nada"); return
        pw = secrets.token_urlsafe(24)
        (u,) = await ws_call(s, ADMIN, [{"type": "config/auth/create", "name": "despensa", "group_ids": ["system-users"], "local_only": True}])
        uid = u["result"]["user"]["id"]
        (c,) = await ws_call(s, ADMIN, [{"type": "config/auth_provider/homeassistant/create", "user_id": uid, "username": "despensa", "password": pw}])
        assert c["success"], c
        cid = U + "/"
        async with s.post(U + "/auth/login_flow", json={"client_id": cid, "handler": ["homeassistant", None], "redirect_uri": cid}) as r:
            fid = (await r.json())["flow_id"]
        async with s.post(f"{U}/auth/login_flow/{fid}", json={"client_id": cid, "username": "despensa", "password": pw}) as r:
            code = (await r.json())["result"]
        async with s.post(U + "/auth/token", data={"grant_type": "authorization_code", "code": code, "client_id": cid}) as r:
            acceso = (await r.json())["access_token"]
        (t,) = await ws_call(s, acceso, [{"type": "auth/long_lived_access_token", "client_name": "chatty despensa.py", "lifespan": 3650}])
        print(f"usuario {uid} creado", file=sys.stderr)
        print(t["result"])
asyncio.run(main())
