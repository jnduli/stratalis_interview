MAIRE_URL = "https://www.mon-maire.fr/maires-regions"
import re
from bs4 import BeautifulSoup
import requests


def extract_content_from_mayor_page(url: str):
    # TODO: fix bugs found in this parsing script
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, "html.parser")
    email = soup.find(itemprop="email").text.strip()
    itemprop = lambda x: soup.find(itemprop=x).text.strip()
    data = {
        "email": email,
        "telephone": soup.find(itemprop="telephone").text.strip(),
        "address": f"{itemprop('name')}, {itemprop('streetAddress')}, {itemprop('postalCode')} {itemprop('addressLocality')}",
    }
    for paragraph in soup.find_all("p"):
        if "Il a pris ses fonctions en tant que maire le" in paragraph.text:
            date_take_office = re.match(
                r".*Il a pris ses fonctions en tant que maire le (\d{2}/\d{2}/\d{4}).*",
                paragraph.text,
                re.DOTALL,
            ).group(1)
            data["date_take_office"] = date_take_office
            break
    return data


def main():
    url = "https://www.mon-maire.fr/maire-de-anse-bertrand-971"
    data = extract_content_from_mayor_page(url)
    print(data)


if __name__ == "__main__":
    main()
