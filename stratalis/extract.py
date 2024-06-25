import asyncio
import logging
import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

from stratalis.crawl import CrawlResult


async def extractor(
    crawl_results: List[CrawlResult], query_limits: Optional[int] = None
):
    """
    Handle extraction in chunks to prevent IO from bottling processing
    """
    if query_limits:
        crawl_results = crawl_results[0:query_limits]
    connector = aiohttp.TCPConnector(limit=50, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        mayors = await asyncio.gather(
            *[
                extract_content_from_mayor_page(session, crawl)
                for crawl in crawl_results
            ],
            return_exceptions=True,
        )
        for idx, mayor in enumerate(mayors):
            if isinstance(mayor, Exception):
                logging.error(
                    f"Failed to extract mayor info from {crawl_results[idx]}, error: {mayor}"
                )
                continue
            yield mayor


async def extract_content_from_mayor_page(
    session: aiohttp.ClientSession, crawl: CrawlResult
) -> dict:
    # TODO: fix bugs found in this parsing script
    logging.info(f"Extracting content for {crawl.mayor_link}")

    def itemprop(x):
        item = soup.find(itemprop=x)
        if item is None:
            return ""
        return item.text.strip()

    async with session.get(crawl.mayor_link) as resp:
        content = await resp.text()
        soup = BeautifulSoup(content, "html.parser")
        data = {
            "Région": crawl.region,
            "Ville": crawl.ville,
            "Nom du maire": crawl.mayor_name,
            "Téléphone": itemprop("telephone"),
            "Email": itemprop("email"),
            "Adresse Mairie": f"{itemprop('name')}, {itemprop('streetAddress')}, {itemprop('postalCode')} {itemprop('addressLocality')}",
        }
        for paragraph in soup.find_all("p"):
            if "a pris ses fonctions en tant que maire le" in paragraph.text:
                date_take_office = re.match(
                    r".*a pris ses fonctions en tant que maire le (\d{2}/\d{2}/\d{4}).*",
                    paragraph.text,
                    re.DOTALL,
                )
                if date_take_office is None:
                    str_date_take_office = ""
                else:
                    str_date_take_office = date_take_office.group(1)
                data["Date de prise de fonction"] = str_date_take_office
                break
        return data
