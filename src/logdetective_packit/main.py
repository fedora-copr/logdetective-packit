from fastapi import FastAPI

app = FastAPI()

@app.post("/analyze")
async def analyze_build(build_info):

    return "NOT IMPLMENTED"

