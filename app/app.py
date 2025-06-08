from fastapi import FastAPI
app = FastAPI()

@app.get("/")
async def root():
    key = "heyyyy"
    value = 8
    data = {key:value}
    return data