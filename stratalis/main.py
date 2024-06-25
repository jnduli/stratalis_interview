import aiohttp
import csv
import logging
import asyncio
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional
import argparse


MAIRE_URL = "https://www.mon-maire.fr/maires-regions"


@dataclass
class CrawlResult:
    region: str
    ville: str
    mayor_name: str
    mayor_link: str


def set_up_logger(level: str, log_file: Optional[str] = None):
    logging.basicConfig(filename=log_file, encoding="utf-8", level=level)


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
    logging.info(f"Fetching regional mayor pages for: {url}")
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
                logging.error(f"Failed to load content for {child_pages[idx]}, error: {child}")
                continue
            result.extend(child)
    mayors = soup.find_all("li", class_="list-group-item")
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
                logging.error(f"Failed to extract mayor info from {crawl_results[idx]}, error: {mayor}")
                continue
            yield mayor


async def extract_content_from_mayor_page(
    session: aiohttp.ClientSession, crawl: CrawlResult
) -> dict:
    # TODO: fix bugs found in this parsing script
    logging.info(f"Extracting content for {crawl.mayor_link}")
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


async def runner(output_file: str, query_limits: Optional[int] = None):
    logging.info("Started processing")
    crawl_results = await crawler(MAIRE_URL, query_limits)
    logging.info(f"Total results to extract: {len(crawl_results)}")
    with open(output_file, "w") as f:
        count = 0
        field_names = [
            "Région",
            "Ville",
            "Nom du maire",
            "Date de prise de fonction",
            "Téléphone",
            "Email",
            "Adresse Mairie",
        ]
        writer = csv.DictWriter(f, fieldnames=field_names)
        writer.writeheader()
        async for extracted_result in extractor(crawl_results, query_limits):
            writer.writerow(extracted_result)
            count += 1
    logging.info(f"Completed processing, written {count} rows")


def main():
    parser = argparse.ArgumentParser("Demo application for Stratalis")
    parser.add_argument("--output-file", required=True, help="File to store results")
    parser.add_argument(
        "--log-file", help="File to store logs to, if not provided, we log to stdout"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="The log level to use, higher numbers means less logs",
        default="DEBUG",
    )
    parser.add_argument(
        "--query-limits",
        type=int,
        help="Limits the number of mayors to get and output to the csv",
    )
    args = parser.parse_args()
    set_up_logger(args.log_level, args.log_file)
    asyncio.run(runner(args.output_file, args.query_limits))


if __name__ == "__main__":
    main()
