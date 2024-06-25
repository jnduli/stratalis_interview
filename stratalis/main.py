import aiohttp
import csv
import itertools
import logging
import asyncio
import re
from bs4 import BeautifulSoup
import requests
from dataclasses import dataclass
from typing import List


@dataclass
class CrawlResult:
    region: str
    ville: str
    mayor_name: str
    mayor_link: str


MAIRE_URL = "https://www.mon-maire.fr/maires-regions"


async def crawler(url: str) -> List[CrawlResult]:
    """
    Visit https://www.mon-maire.fr/maires-regions and get all relevant links

    For each link: visit them and get: ...
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.text()
            soup = BeautifulSoup(content, "html.parser")
            regions = soup.find_all("li", class_="list-group-item")
            # FIXME drop this delta
            regions = regions[0:2]
            region_listings = await asyncio.gather(
                *[
                    crawl_regions(session, x.a["href"], x.a.text.strip())
                    for x in regions
                ],
                return_exceptions=True,
            )
            flattened_list = []
            for region_listing in region_listings:
                if isinstance(region_listing, Exception):
                    logging.error(f"Failed to gather for {region_listing}")
                    continue
                flattened_list.extend(region_listing)
            return flattened_list


async def crawl_regions(
    session: aiohttp.ClientSession,
    url: str,
    region_name: str,
    get_pagination: bool = True,
):
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    # if get_pagination:
    #     child_pages = get_all_child_pages(soup)
    #     for child in child_pages:
    #         region_listing(child, region_name, get_pagination=False)
    # Note: page has a listing section
    mayors = soup.find_all("li", class_="list-group-item")
    result = []
    for mayor in mayors:
        ville, a_tag = mayor.contents
        ville = ville.split("-")[0].strip()
        name = a_tag.text.strip()
        href = a_tag["href"]
        result.append(CrawlResult(region_name, ville, name, href))
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


async def extractor(crawl_results: List[CrawlResult]):
    """
    Handle extraction in chunks to prevent IO from bottling processing
    """
    # FIXME: remove this
    crawl_results = crawl_results[0:20]
    iterator = iter(crawl_results)
    async with aiohttp.ClientSession() as session:
        while chunk := list(itertools.islice(iterator, 10)):
            mayors = await asyncio.gather(*[extract_content_from_mayor_page(session, crawl) for crawl in chunk])
            yield mayors


async def extract_content_from_mayor_page(
    session: aiohttp.ClientSession, crawl: CrawlResult
) -> dict:
    # TODO: fix bugs found in this parsing script
    itemprop = lambda x: soup.find(itemprop=x).text.strip()
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
                ).group(1)
                data["Date de prise de fonction"] = date_take_office
                break
        return data


async def runner():
    main_page = "https://www.mon-maire.fr/maires-regions"
    crawl_results = await crawler(main_page)

    with open("/tmp/res.csv", "w") as f:
        field_names = ["Région", "Ville", "Nom du maire", "Date de prise de fonction", "Téléphone", "Email", "Adresse Mairie"]
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        async for extracted_result in extractor(crawl_results):
            writer.writerows(extracted_result)
    print("done")


def main():
    asyncio.run(runner())
    # url = "https://www.mon-maire.fr/maire-de-anse-bertrand-971"
    # data = extract_content_from_mayor_page(url)
    # print(data)


if __name__ == "__main__":
    main()
