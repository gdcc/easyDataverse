import asyncio
from typing import List
from urllib.parse import urljoin

import aiohttp
import requests
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
    response = requests.get(all_blocks_url)
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
    async with aiohttp.ClientSession() as session:
        tasks = [
            _fetch_metadatablock(
                session,
                block_name,
                base_url,
            )
            for block_name in block_names
        ]
        return await asyncio.gather(*tasks)


async def _fetch_metadatablock(session, block_name, base_url):
    """
    Fetches a metadata block from the Dataverse server.

    Args:
        session (aiohttp.ClientSession): The aiohttp client session.
        block_name (str): The name of the metadata block to fetch.
        base_url (str): The base URL of the Dataverse server.

    Returns:
        dict: The JSON response containing the metadata block.
    """
    async with session.get(
        urljoin(base_url, f"api/metadatablocks/{block_name}")
    ) as response:
        response.raise_for_status()
        return DottedDict(await response.json())
