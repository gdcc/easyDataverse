from fastapi import FastAPI

from pyDaRUS.metadatablocks.astrophysics import Astrophysics
from pyDaRUS.metadatablocks.citation import Citation
from pyDaRUS.metadatablocks.journal import Journal
from pyDaRUS.metadatablocks.socialscience import Socialscience
from pyDaRUS.metadatablocks.codeMeta import CodeMeta
from pyDaRUS.metadatablocks.biomedical import Biomedical
from pyDaRUS.metadatablocks.geospatial import Geospatial
from pyDaRUS.metadatablocks.archive import Archive
from pyDaRUS.metadatablocks.privacy import Privacy

app = FastAPI(title="pyDaRUS", version="1.0", redoc_url="/")
@app.post(
    "/create/astrophysics",
    summary="Create Astrophysics block",
    description="Creates a Dataverse compatible JSON file for the Astrophysics schema",
    tags=["Metadatablocks"]
)
async def create_astrophysics(astrophysics: Astrophysics):
    return astrophysics.dataverse_dict()

@app.post(
    "/create/citation",
    summary="Create Citation block",
    description="Creates a Dataverse compatible JSON file for the Citation schema",
    tags=["Metadatablocks"]
)
async def create_citation(citation: Citation):
    return citation.dataverse_dict()

@app.post(
    "/create/journal",
    summary="Create Journal block",
    description="Creates a Dataverse compatible JSON file for the Journal schema",
    tags=["Metadatablocks"]
)
async def create_journal(journal: Journal):
    return journal.dataverse_dict()

@app.post(
    "/create/socialscience",
    summary="Create Socialscience block",
    description="Creates a Dataverse compatible JSON file for the Socialscience schema",
    tags=["Metadatablocks"]
)
async def create_socialscience(socialscience: Socialscience):
    return socialscience.dataverse_dict()

@app.post(
    "/create/codemeta",
    summary="Create CodeMeta block",
    description="Creates a Dataverse compatible JSON file for the CodeMeta schema",
    tags=["Metadatablocks"]
)
async def create_codemeta(codemeta: CodeMeta):
    return codemeta.dataverse_dict()

@app.post(
    "/create/biomedical",
    summary="Create Biomedical block",
    description="Creates a Dataverse compatible JSON file for the Biomedical schema",
    tags=["Metadatablocks"]
)
async def create_biomedical(biomedical: Biomedical):
    return biomedical.dataverse_dict()

@app.post(
    "/create/geospatial",
    summary="Create Geospatial block",
    description="Creates a Dataverse compatible JSON file for the Geospatial schema",
    tags=["Metadatablocks"]
)
async def create_geospatial(geospatial: Geospatial):
    return geospatial.dataverse_dict()

@app.post(
    "/create/archive",
    summary="Create Archive block",
    description="Creates a Dataverse compatible JSON file for the Archive schema",
    tags=["Metadatablocks"]
)
async def create_archive(archive: Archive):
    return archive.dataverse_dict()

@app.post(
    "/create/privacy",
    summary="Create Privacy block",
    description="Creates a Dataverse compatible JSON file for the Privacy schema",
    tags=["Metadatablocks"]
)
async def create_privacy(privacy: Privacy):
    return privacy.dataverse_dict()