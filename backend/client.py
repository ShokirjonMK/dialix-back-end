import socketio
import asyncio

sio = socketio.AsyncClient(
    reconnection=True,
    reconnection_attempts=3,
    reconnection_delay=1,
    reconnection_delay_max=5,
)


async def connect():
    try:
        await sio.connect(
            "ws://localhost:8080/ws/",
            headers={
                "Authorization": "Bearer access_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTA0NzRlMjctMDhiNi00OTU5LTgwMmYtM2MyYmE1OWJkYzE2IiwiZXhwIjoxNzE5OTUwMzg0fQ.J2To7HTpddJmYoX3yeB8Q-Qs2YecEyNAaHE9vJjC-yU"
            },
            socketio_path="/ws/socket.io/",
            transports=["websocket"],
        )
        print("Connected to server")
    except Exception as e:
        print(f"Error occurred while connecting: {str(e)}")


@sio.on("connect")
async def on_connect():
    print("Successfully connected to the server.")
    await sio.emit(
        "query", "Hello, server!"
    )  # Initial message to server after connection


@sio.on("result")
async def on_result(data):
    print("Received result:", data)
    if sio.connected:
        await sio.emit("custom_message", "Hello, server22222222222222222!")


@sio.on("chat")
async def on_chat(data):
    print("Received message:", data)


@sio.on("disconnect")
async def on_disconnect():
    print("Disconnected from server")


async def main():
    await connect()

    try:
        # This loop keeps the client running to listen to events.
        while True:
            await asyncio.sleep(
                1
            )  # This sleep keeps the loop from blocking other tasks.
    except KeyboardInterrupt:
        print("Disconnecting from the server...")
        await sio.disconnect()
        print("Disconnected!")


if __name__ == "__main__":
    asyncio.run(main())
