from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/items/")
def create_item(item_name: str):
    return {"item_name": item_name}


@app.put("/items/{item_id}")
def update_item(item_id: int, item_name: str):
    return {"item_id": item_id, "item_name": item_name}

