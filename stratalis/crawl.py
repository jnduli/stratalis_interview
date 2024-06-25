import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class CrawlResult:
    region: str
    ville: str
    mayor_name: str
    mayor_link: str


async def crawler(url: str, query_limits: Optional[int] = None) -> List[CrawlResult]:
    """
    Visit url and get a list of all mayor pages for parallel processing
    """
    connector = aiohttp.TCPConnector(limit=50, force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url) as resp:
            content = await resp.text()
            soup = BeautifulSoup(content, "html.parser")
            regions = soup.find_all("li", class_="list-group-item")
            region_listings = await asyncio.gather(
                *[
                    crawl_regions(session, x.a["href"], x.a.text.strip())
                    for x in regions
                ],
                return_exceptions=True,
            )
            flattened_list: List[CrawlResult] = []
            for idx, region_listing in enumerate(region_listings):
                if isinstance(region_listing, Exception):
                    failed_url = regions[idx].a["href"]
                    logging.error(
                        f"Failed to gather crawlers for {failed_url}, error {region_listing}"
                    )
                    continue
                flattened_list.extend(region_listing)
                if query_limits and len(flattened_list) > query_limits:
                    break
            logging.info(f"Found a total of {len(flattened_list)} region listings")
            return flattened_list


async def crawl_regions(
    session: aiohttp.ClientSession,
    url: str,
    region_name: str,
    get_pagination: bool = True,
):
    logging.debug(f"Fetching regional mayor pages for: {url}")
    resp = await session.get(url)
    content = await resp.text()
    soup = BeautifulSoup(content, "html.parser")
    result: List[CrawlResult] = []
    if get_pagination:
        child_pages = get_all_child_pages(soup)[0:2]
        child_listings = await asyncio.gather(
            *[
                crawl_regions(session, child_uri, region_name, get_pagination=False)
                for child_uri in child_pages
            ],
            return_exceptions=True,
        )
        for idx, child in enumerate(child_listings):
            if isinstance(child, Exception):
                logging.error(
                    f"Failed to load content for {child_pages[idx]}, error: {child}"
                )
                continue
            result.extend(child)
    mayors = soup.find_all("li", class_="list-group-item")
    for mayor in mayors:
        ville, a_tag = mayor.contents
        ville = ville.split("-")[0].strip()
        name = a_tag.text.strip()
        href = a_tag["href"]
        result.append(CrawlResult(region_name, ville, name, href))
    logging.debug(f"Completed fetching regional mayor pages for: {url}")
    return result


def get_all_child_pages(soup):
    """We've already loaded the parent page, so if children exist, generate list for all of them"""
    page_numbers = soup.find_all("a", class_="page-numbers")
    if not page_numbers:
        return []
    max_page_no = 2
    link_with_2 = ""
    for page in page_numbers:
        try:
            no = int(page.text)
        except ValueError:  # Suivant
            continue
        if no == 2:
            link_with_2 = page["href"]
        max_page_no = max(max_page_no, no)
    child_pages = []
    for i in range(2, max_page_no + 1):
        child_pages.append(link_with_2.replace("2", f"{i}"))
    return child_pages
