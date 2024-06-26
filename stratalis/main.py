import argparse
import asyncio
import csv
import logging
import time
from typing import Optional

from stratalis import crawl, extract

MAIRE_URL = "https://www.mon-maire.fr/maires-regions"


def set_up_logger(level: str, log_file: Optional[str] = None):
    logging.basicConfig(filename=log_file, encoding="utf-8", level=level)


async def runner(output_file: str, query_limits: Optional[int] = None):
    start = time.monotonic()
    logging.info("Started processing")
    crawl_results = await crawl.crawler(MAIRE_URL, query_limits)
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
        async for extracted_result in extract.extractor(crawl_results, query_limits):
            writer.writerow(extracted_result)
            count += 1

    end = time.monotonic()
    logging.info(f"Completed processing, written {count} rows. Took {end - start} seconds.")


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
