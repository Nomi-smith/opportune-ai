import re
from bs4 import BeautifulSoup
from models.opportunity import Opportunity
from intelligence.opportunity_intelligence import extract_opportunity_details


def clean_text(value):
    if not value:
        return value
    text = str(value)
    if '<' in text and '>' in text:
        text = BeautifulSoup(text, 'html.parser').get_text('\n', strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def normalize_opportunity(item: Opportunity) -> Opportunity:
    item.title = clean_text(item.title)
    item.organization = clean_text(item.organization)
    item.description = clean_text(item.description)
    item.country = clean_text(item.country)
    item.city = clean_text(item.city)
    item.source_name = clean_text(item.source_name)
    item.requirements = [clean_text(x) for x in item.requirements if clean_text(x)]
    return extract_opportunity_details(item)


def normalize_results(items):
    return [normalize_opportunity(x) for x in items]
