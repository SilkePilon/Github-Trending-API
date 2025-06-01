"""Scraping
===================
Functions to scrape repository/developer data (HTML -> list of dicts).
"""
# Copyright (c) 2021, Niklas Tiede.
# All rights reserved. Distributed under the MIT License.
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import aiohttp
import bs4


async def get_request(
    *args: str,
    **kwargs: Dict[str, str],
) -> Union[str, None]:
    """Asynchronous GET request with aiohttp."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(*args, **kwargs, headers=headers) as resp:
                return await resp.text()
    except aiohttp.ClientConnectorError as cce:
        print(f"AIOHTTP ClientConnectorError: {cce}")
        return None


def filter_articles(raw_html: str) -> str:
    """Filters HTML out, which is not enclosed by article-tags.
    Beautifulsoup is inaccurate and slow when applied on a larger
    HTML string, this filtration fixes this.
    """
    raw_html_lst = raw_html.split("\n")

    # count number of article tags within the document (varies from 0 to 50):
    article_tags_count = 0
    tag = "article"
    for line in raw_html_lst:
        if tag in line:
            article_tags_count += 1

    # copy HTML enclosed by first and last article-tag:
    articles_arrays, is_article = [], False
    for line in raw_html_lst:
        if tag in line:
            article_tags_count -= 1
            is_article = True
        if is_article:
            articles_arrays.append(line)
        if not article_tags_count:
            is_article = False
    return "".join(articles_arrays)


def make_soup(articles_html: str) -> bs4.element.ResultSet:
    """HTML enclosed by article-tags is converted into a
    soup for further data extraction.
    """
    soup = bs4.BeautifulSoup(articles_html, "lxml")
    return soup.find_all("article", class_="Box-row")


def scraping_repositories(
    matches: bs4.element.ResultSet,
    since: str,
) -> List[Dict[Any, Any]]:
    """Data about all trending repositories are extracted."""
    trending_repositories = []
    for rank, match in enumerate(matches):
        description = None
        rel_url = None
        repo_url = None
        repository_name = None
        username = None
        language = None
        lang_color = None
        raw_total_stars = None
        total_stars = None
        raw_forks = None
        forks = None
        raw_stars_since = None
        stars_since = None
        built_by = []  # Default to empty list

        try:
            # description
            if match.p:
                description = match.p.get_text(strip=True)
            else:
                description = None

            # relative url
            rel_url = match.h1.a["href"]

            # absolute url:
            repo_url = "https://github.com" + rel_url

            # name of repo
            repository_name = rel_url.split("/")[-1]

            # author (username):
            username = rel_url.split("/")[-2]

            # language and color
            progr_language = match.find("span", itemprop="programmingLanguage")
            if progr_language:
                language = progr_language.get_text(strip=True)
                lang_color_tag = match.find("span", class_="repo-language-color")
                lang_color = lang_color_tag["style"].split()[-1]
            else:
                lang_color, language = None, None

            stars_built_section = match.div.findNextSibling("div")

            # total stars:
            if stars_built_section.a:
                raw_total_stars_tag = stars_built_section.a
                if raw_total_stars_tag: # check if tag exists
                    raw_total_stars = raw_total_stars_tag.get_text(strip=True)
                    if "," in raw_total_stars:
                        raw_total_stars = raw_total_stars.replace(",", "")
            if raw_total_stars: # check if it has a value
                total_stars: Optional[int]
                try:
                    total_stars = int(raw_total_stars)
                except ValueError as missing_number:
                    print(missing_number) # Keep existing error print for this specific conversion
            else:
                total_stars = None

            # forks
            raw_forks_tag = stars_built_section.a.findNextSibling("a") if stars_built_section.a else None
            if raw_forks_tag: # check if tag exists
                raw_forks = raw_forks_tag.get_text(strip=True)
                if "," in raw_forks:
                    raw_forks = raw_forks.replace(",", "")
            if raw_forks: # check if it has a value
                forks: Optional[int]
                try:
                    forks = int(raw_forks)
                except ValueError as missing_number:
                    print(missing_number) # Keep existing error print for this specific conversion
            else:
                forks = None

            # stars in period
            stars_since_tag = stars_built_section.find(
                    "span", class_="d-inline-block float-sm-right",
            )
            if stars_since_tag: # check if tag exists
                raw_stars_since = (
                    stars_since_tag.get_text(strip=True)
                    .split()[0]
                )
                if "," in raw_stars_since:
                    raw_stars_since = raw_stars_since.replace(",", "")
            if raw_stars_since: # check if it has a value
                stars_since: Optional[int]
                try:
                    stars_since = int(raw_stars_since)
                except ValueError as missing_number:
                    print(missing_number) # Keep existing error print for this specific conversion
            else:
                stars_since = None

            # builtby
            built_section = stars_built_section.find(
                "span",
                class_="d-inline-block mr-3",
            )
            if built_section:
                contributors = built_section.find_all("a") # Use built_section directly
                # built_by is already initialized to []
                for contributor in contributors:
                    contr_data = {}
                    contr_data["username"] = contributor["href"].strip("/")
                    contr_data["url"] = "https://github.com" + contributor["href"]
                    contr_data["avatar"] = contributor.img["src"]
                    built_by.append(dict(contr_data))

            repositories = {
                "rank": rank + 1,
                "username": username,
                "repositoryName": repository_name,
                "url": repo_url,
                "description": description,
                "language": language,
                "languageColor": lang_color,
                "totalStars": total_stars,
                "forks": forks,
                "starsSince": stars_since,
                "since": since,
                "builtBy": built_by,
            }
            trending_repositories.append(repositories)
        except Exception as e:
            print(f"Error scraping repository item at rank {rank + 1} for URL {repo_url if 'repo_url' in locals() and repo_url else 'unknown'}: {e}")
            # import traceback
            # print(traceback.format_exc())
            continue
    return trending_repositories


def scraping_developers(
    matches: bs4.element.ResultSet,
    since: str,
) -> List[Dict[Any, Any]]:
    """Data about all trending developers are extracted."""
    all_trending_developers = []
    for rank, match in enumerate(matches):
        rel_url = None
        dev_url = None
        username = None
        name = None
        avatar = None
        repo_description = None
        repo_name = None
        repo_url = None # For the popular repository

        try:
            # relative url of developer
            # Ensure match.div and match.div.a exist before accessing "href"
            if match.div and match.div.a and "href" in match.div.a.attrs:
                rel_url = match.div.a["href"]
            else: # Handle case where expected tags/attributes are missing
                print(f"Error scraping developer item at rank {rank + 1}: Missing div or a tag for rel_url.")
                continue


            # absolute url of developer
            dev_url = "https://github.com" + rel_url

            # username of developer
            username = rel_url.strip("/")

            # developers full name
            name = match.h1.a.get_text(strip=True) if match.h1 and match.h1.a else None

            # avatar url of developer
            avatar = match.img["src"] if match.img and "src" in match.img.attrs else None

            # data about developers popular repo:
            if match.article:
                raw_description_tag = match.article.find(
                    "div",
                    class_="f6 color-text-secondary mt-1",
                )
                repo_description = (
                    raw_description_tag.get_text(
                        strip=True,
                    )
                    if raw_description_tag
                    else None
                )
                pop_repo_tag = match.article.h1.a if match.article.h1 else None
                if pop_repo_tag:
                    repo_name = pop_repo_tag.get_text(strip=True)
                    repo_url = "https://github.com" + pop_repo_tag["href"]
                else:
                    repo_name = None
                    repo_url = None
            else:
                repo_description = None
                repo_name = None
                repo_url = None

            one_developer = {
                "rank": rank + 1,
                "username": username,
                "name": name,
                "url": dev_url,
                "avatar": avatar,
                "since": since,
                "popularRepository": {
                    "repositoryName": repo_name,
                    "description": repo_description,
                    "url": repo_url,
                },
            }
            all_trending_developers.append(one_developer)
        except Exception as e:
            print(f"Error scraping developer item at rank {rank + 1} for URL {dev_url if 'dev_url' in locals() and dev_url else 'unknown'}: {e}")
            # import traceback
            # print(traceback.format_exc())
            continue
    return all_trending_developers
