import pathlib
from unittest.mock import MagicMock

import aiohttp
import pytest

from stratalis import extract
from stratalis.crawl import CrawlResult


@pytest.mark.asyncio
async def test_download():
    file = pathlib.Path(__file__).parent / "test_data/extract.html"
    with open(file) as f:
        content = f.read()
    mock = aiohttp.ClientSession
    mock.get = MagicMock()
    mock.get.return_value.__aenter__.return_value.status = 200
    mock.get.return_value.__aenter__.return_value.text.return_value = content
    crawlResult = CrawlResult("Africa", "Nairobi", "Doe", "https://example.com")

    async with aiohttp.ClientSession() as session:
        expected = {
            "Région": "Africa",
            "Ville": "Nairobi",
            "Nom du maire": "Doe",
            "Téléphone": "04 77 50 35 12",
            "Email": "mairie-daboen@wanadoo.fr",
            "Adresse Mairie": "Mairie de Aboën, 120 place des Tilleuls, 42380 Aboën",
            "Date de prise de fonction": "25/05/2020",
        }
        res = await extract.extract_content_from_mayor_page(session, crawlResult)
        assert res == expected
