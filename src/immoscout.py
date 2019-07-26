#!/user/bin/env python
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import datetime

_TIMEOUT = 10
_BASE_URL = 'https://www.immobilienscout24.de'

def filter_none(dict):
  return { k:v for k,v in dict.items() if v is not None }

class ImmoscoutResult:
  def __init__(self, url):
    self._url = url
    self.soup = get_soup(url)
    self._timestamp = datetime.datetime.utcnow().timestamp()

  def id(self):
    element = self.soup.select_one('.is24-scoutid__content')
    return str(int(self._extract_number(element.text.split('|')[-1])))

  def name(self):
    element = self.soup.select_one('h1#expose-title')
    return element.text

  def url(self):
    return self._url

  def timestamp(self):
    return self._timestamp

  def type(self):
    element = self.soup.select_one('dd.is24qa-typ')
    return element.text if element else None

  def is_rental(self):
    return False if self.soup.select_one('.is24qa-kaufpreis') else True

  def price(self):
    element = self.soup.select_one('.is24qa-kaufpreis')
    if not element:
      element = self.soup.select_one('.is24qa-kaltmiete')
    return float(self._extract_number(element.text))

  def rooms(self):
    element = self.soup.select_one('dd.is24qa-zimmer')
    return float(self._extract_number(element.text))

  def area(self):
    element = self.soup.select_one('dd.is24qa-wohnflaeche-ca')
    return float(self._extract_number(element.text))

  def country(self):
    return "Germany"

  def state(self):
    elements = self.soup.select('.breadcrumb__link')
    return elements[1].text

  def city(self):
    elements = self.soup.select('.breadcrumb__link')
    return elements[2].text

  def district(self):
    elements = self.soup.select('.breadcrumb__link')
    return elements[3].text

  def street(self):
    address_block = self.soup.select_one('.address-block')
    try:
      return address_block.select_one('.block').text.strip(' ,')
    except:
      return None

  def zip(self):
    address_block = self.soup.select_one('.address-block')
    try:
      return address_block.select_one('.zip-region-and-country').text.split()[0]
    except:
      return None

  def address(self):
    return filter_none({
      "country": self.country(),
      "state": self.state(),
      "city": self.city(),
      "zip": self.zip(),
      "district": self.district(),
      "street": self.street()
    })

  def attributes(self):
    elements = self.soup.select('.criteriagroup.boolean-listing > span')
    return [elem.text for elem in elements]

  def json(self):
    return filter_none({
      "id": self.id(),
      "name": self.name(),
      "url": self.url(),
      "timestamp": self.timestamp(),
      "is_rental": self.is_rental(),
      "price": self.price(),
      "area": self.area(),
      "rooms": self.rooms(),
      "address": self.address(),
      "type": self.type(),
      "attributes": self.attributes()
    })

  def _extract_number(self, input):
    return ''.join([x for x in input if (x in '0123456789,.')]).replace('.', '').replace(',', '.')


class ImmoscoutResultList:
  def __init__(self, url):
    self.url = url

  def items(self, limit=9999):
    next_url = self.url
    while next_url:
      soup = get_soup(next_url)
      next_url = self._next_page(soup)
      items = self._page_items(soup)
      for url in items:
        yield ImmoscoutResult(url)
        limit -= 1
        if limit <= 0:
          return

  def _next_page(self, soup):
    element = soup.select_one('a[data-is24-qa="paging_bottom_next"]')
    if not element:
      return False
    return urljoin(_BASE_URL, element['href'])

  def _page_items(self, soup):
    elements = soup.select('.result-list-entry__data a.result-list-entry__brand-title-container')
    return [urljoin(_BASE_URL, elem['href']) for elem in elements]


class Immoscout:
  def __init__(self):
    self.BASE_URL = urljoin(_BASE_URL, "/Suche/S-T")

  def rent(self, state="", city="", quarter=""):
    url = '/'.join(filter(None, [self.BASE_URL, "Wohnung-Miete", state, city, quarter]))
    return ImmoscoutResultList(url)

  def buy(self, state="", city="", quarter=""):
    url = '/'.join(filter(None, [self.BASE_URL, "Wohnung-Kauf", state, city, quarter]))
    return ImmoscoutResultList(url)


def get_soup(url):
  response = requests.get(url)
  if response.status_code != 200:
    raise Exception(f"[Error] Response status code {response.status_code}.")
  return BeautifulSoup(response.text, 'html.parser')


if __name__ == "__main__":
  print("Starting to scrape immoscout..")
  immoscout = Immoscout()
  # results = immoscout.rent('Nordrhein-Westfalen', 'Muenster')
  results = immoscout.buy('Nordrhein-Westfalen', 'Muenster')
  items = [item for item in results.items(10)]
  print(f"Found {len(items)} items.")
  for item in items:
    print(item.json())
