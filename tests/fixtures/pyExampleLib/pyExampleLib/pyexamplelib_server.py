from fastapi import FastAPI

from pyDaRUS.metadatablocks.toyDataset import ToyDataset

app = FastAPI(title="pyDaRUS", version="1.0", redoc_url="/")
@app.post(
    "/create/toydataset",
    summary="Create ToyDataset block",
    description="Creates a Dataverse compatible JSON file for the ToyDataset schema",
    tags=["Metadatablocks"]
)
async def create_toydataset(toydataset: ToyDataset):
    return toydataset.dataverse_dict()