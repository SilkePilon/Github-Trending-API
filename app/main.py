"""Github-Trending-API
===================
API serving data about trending github repositories/developers.
"""
# Copyright (c) 2021, Niklas Tiede.
# All rights reserved. Distributed under the MIT License.
import asyncio
from typing import Any
from typing import Dict
from typing import List
from typing import Union

from fastapi import FastAPI, HTTPException, Request
import uvicorn

from app.allowed_parameters import AllowedDateRanges
from app.allowed_parameters import AllowedProgrammingLanguages
from app.allowed_parameters import AllowedSpokenLanguages
from app.scraping import filter_articles
from app.scraping import get_request
from app.scraping import make_soup
from app.scraping import scraping_developers
from app.scraping import scraping_repositories

app = FastAPI()


# DOMAIN_NAME = "https://gh-trending-api.herokuapp.com"


@app.get("/")
def help_routes() -> Dict[str, str]:
    """ API endpoints and documentation. """
    return {
        "repositories": "/repositories",
        "developers": "/developers",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/repositories")
async def trending_repositories(
    request: Request,
    since: AllowedDateRanges = None,
    spoken_language_code: AllowedSpokenLanguages = None,
) -> Union[List[Any], str]:
    """Returns data about trending repositories (all programming
    languages, cannot be specified on this endpoint).
    """
    payload = {"since": "daily"}
    if since:
        payload["since"] = since.value
    if spoken_language_code:
        payload["spoken_language_code"] = spoken_language_code.value

    url = "https://github.com/trending"
    sem = asyncio.Semaphore()
    async with sem:
        raw_html = await get_request(url, compress=True, params=payload)

    if raw_html is None:
        print(f"Error in {request.url.path}: get_request returned None, indicating a connection error to GitHub.")
        raise HTTPException(status_code=502, detail="Failed to fetch data from GitHub. The external service may be temporarily unavailable or blocking requests.")
    if not raw_html.strip():
        print(f"Error in {request.url.path}: get_request returned empty content from GitHub.")
        raise HTTPException(status_code=502, detail="Received empty response from GitHub. The page structure might have changed, no data is available, or the request was blocked.")

    try:
        articles_html = filter_articles(raw_html)
        if not articles_html.strip(): # If filter_articles returns empty
            print(f"Warning in {request.url.path}: filter_articles returned empty content. Potentially no <article> tags found.")
        soup = make_soup(articles_html)
        scraped_data = scraping_repositories(soup, since=payload["since"])
        if not scraped_data: # If scraping returns empty list due to no items or all items failed
             print(f"Warning in {request.url.path}: scraping_repositories returned no data. All items might have failed parsing or no items were present.")
        return scraped_data
    except Exception as e:
        import traceback
        print(f"Unhandled error in route {request.url.path} during scraping/processing: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the data.")


@app.get("/repositories/{prog_lang}")
async def trending_repositories_by_progr_language(
    request: Request,
    prog_lang: AllowedProgrammingLanguages,
    since: AllowedDateRanges = None,
    spoken_language_code: AllowedSpokenLanguages = None,
) -> Union[List[Any], str]:
    """Returns data about trending repositories. A specific programming
    language can be added as path parameter to specify search.
    """
    payload = {"since": "daily"}
    if since:
        payload["since"] = since.value
    if spoken_language_code:
        payload["spoken_language_code"] = spoken_language_code.value

    url = f"https://github.com/trending/{prog_lang}"
    sem = asyncio.Semaphore()
    async with sem:
        raw_html = await get_request(url, compress=True, params=payload)

    if raw_html is None:
        print(f"Error in {request.url.path}: get_request returned None, indicating a connection error to GitHub.")
        raise HTTPException(status_code=502, detail="Failed to fetch data from GitHub. The external service may be temporarily unavailable or blocking requests.")
    if not raw_html.strip():
        print(f"Error in {request.url.path}: get_request returned empty content from GitHub.")
        raise HTTPException(status_code=502, detail="Received empty response from GitHub. The page structure might have changed, no data is available, or the request was blocked.")

    try:
        articles_html = filter_articles(raw_html)
        if not articles_html.strip():
            print(f"Warning in {request.url.path}: filter_articles returned empty content. Potentially no <article> tags found for {prog_lang}.")
        soup = make_soup(articles_html)
        scraped_data = scraping_repositories(soup, since=payload["since"])
        if not scraped_data:
             print(f"Warning in {request.url.path}: scraping_repositories returned no data for {prog_lang}. All items might have failed parsing or no items were present.")
        return scraped_data
    except Exception as e:
        import traceback
        print(f"Unhandled error in route {request.url.path} during scraping/processing for {prog_lang}: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the data.")


@app.get("/developers")
async def trending_developers(
    request: Request,
    since: AllowedDateRanges = None,
) -> Union[List[Any], str]:
    """Returns data about trending developers (all programming languages,
    cannot be specified on this endpoint).
    """
    payload = {"since": "daily"}
    if since:
        payload["since"] = since.value

    url = "https://github.com/trending/developers"
    sem = asyncio.Semaphore()
    async with sem:
        raw_html = await get_request(url, compress=True, params=payload)

    if raw_html is None:
        print(f"Error in {request.url.path}: get_request returned None, indicating a connection error to GitHub.")
        raise HTTPException(status_code=502, detail="Failed to fetch data from GitHub. The external service may be temporarily unavailable or blocking requests.")
    if not raw_html.strip():
        print(f"Error in {request.url.path}: get_request returned empty content from GitHub.")
        raise HTTPException(status_code=502, detail="Received empty response from GitHub. The page structure might have changed, no data is available, or the request was blocked.")

    try:
        articles_html = filter_articles(raw_html)
        if not articles_html.strip():
            print(f"Warning in {request.url.path}: filter_articles returned empty content for developers.")
        soup = make_soup(articles_html)
        scraped_data = scraping_developers(soup, since=payload["since"])
        if not scraped_data:
            print(f"Warning in {request.url.path}: scraping_developers returned no data. All items might have failed parsing or no items were present.")
        return scraped_data
    except Exception as e:
        import traceback
        print(f"Unhandled error in route {request.url.path} during scraping/processing developers: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the data.")


@app.get("/developers/{prog_lang}")
async def trending_developers_by_progr_language(
    request: Request,
    prog_lang: AllowedProgrammingLanguages,
    since: AllowedDateRanges = None,
) -> Union[List[Any], str]:
    """Returns data about trending developers. A specific programming
    language can be added as path parameter to specify search.
    """
    payload = {"since": "daily"}
    if since:
        payload["since"] = since.value

    url = f"https://github.com/trending/developers/{prog_lang}"
    sem = asyncio.Semaphore()
    async with sem:
        raw_html = await get_request(url, compress=True, params=payload)

    if raw_html is None:
        print(f"Error in {request.url.path}: get_request returned None, indicating a connection error to GitHub.")
        raise HTTPException(status_code=502, detail="Failed to fetch data from GitHub. The external service may be temporarily unavailable or blocking requests.")
    if not raw_html.strip():
        print(f"Error in {request.url.path}: get_request returned empty content from GitHub.")
        raise HTTPException(status_code=502, detail="Received empty response from GitHub. The page structure might have changed, no data is available, or the request was blocked.")

    try:
        articles_html = filter_articles(raw_html)
        if not articles_html.strip():
            print(f"Warning in {request.url.path}: filter_articles returned empty content for developers/{prog_lang}.")
        soup = make_soup(articles_html)
        scraped_data = scraping_developers(soup, since=payload["since"])
        if not scraped_data:
            print(f"Warning in {request.url.path}: scraping_developers returned no data for developers/{prog_lang}. All items might have failed parsing or no items were present.")
        return scraped_data
    except Exception as e:
        import traceback
        print(f"Unhandled error in route {request.url.path} during scraping/processing developers/{prog_lang}: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An internal server error occurred while processing the data.")


if __name__ == "__main__":
    uvicorn.run(app, port=8000, host="0.0.0.0")
