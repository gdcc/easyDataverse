import asyncio
from typing import List
from urllib.parse import urljoin

import httpx
from dotted_dict import DottedDict


def gather_metadatablock_names(base_url: str):
    """
    Retrieves the names of all metadata blocks from the given base URL.

    Args:
        base_url (str): The base URL of the Dataverse instance.

    Returns:
        list: A list of metadata block names.
    """
    all_blocks_url = urljoin(base_url, "api/metadatablocks")
    with httpx.Client() as client:
        response = client.get(all_blocks_url)
        response.raise_for_status()

        return [block["name"] for block in response.json()["data"]]


async def fetch_metadatablocks(block_names: List[str], base_url: str):
    """
    Fetches metadata blocks for the given block names asynchronously.

    Args:
        block_names (List[str]): A list of block names to fetch metadata for.

    Returns:
        List[dict]: A list of dictionaries containing the metadata for each block.
    """
    async with httpx.AsyncClient() as client:
        tasks = [
            _fetch_metadatablock(
                client,
                block_name,
                base_url,
            )
            for block_name in block_names
        ]
        return await asyncio.gather(*tasks)


async def _fetch_metadatablock(client, block_name, base_url):
    """
    Fetches a metadata block from the Dataverse server.

    Args:
        client (httpx.AsyncClient): The httpx async client.
        block_name (str): The name of the metadata block to fetch.
        base_url (str): The base URL of the Dataverse server.

    Returns:
        dict: The JSON response containing the metadata block.
    """
    response = await client.get(urljoin(base_url, f"api/metadatablocks/{block_name}"))
    response.raise_for_status()
    return DottedDict(response.json())
