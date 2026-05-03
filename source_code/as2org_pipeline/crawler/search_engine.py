from ddgs import DDGS
import logging
import time
QUERY_RATE_LIMIT_SEC = 1.0

def search_key_word(org_name: str, keyword_list: list[str]) -> dict[str, list[str]]:
    logging.info(f'Searching company with keyword: {org_name}')
    queries = [f'{org_name} {keyword}'.strip() for keyword in keyword_list]
    result_url: dict[str, list[str]] = {}
    for query in queries:
        logging.info(f'Searching for: {query}')
        if 'Wikipedia' in query:
            num_results = 1
        else:
            num_results = 4
        time.sleep(QUERY_RATE_LIMIT_SEC)
        links = _search(query, num_results)
        if 'Wikipedia' in query and links:
            if 'wikipedia' not in links[0].lower():
                logging.warning(f"The link returned for query '{query}' does not contain 'Wikipedia'.")
                links = []
        logging.info(f"Found {len(links)} links for '{query}'")
        result_url[query] = links
    return result_url

def _search(query: str, num_results: int, retries: int=2, backoff: float=1.0) -> list[str]:
    attempt = 0
    while attempt < retries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num_results))
                if not results:
                    raise Exception('Empty response or failed backend.')
                return [item.get('href', '') for item in results if item.get('href')]
        except Exception as e:
            attempt += 1
            logging.warning(f"[Attempt {attempt}] DuckDuckGo error for '{query}': {e}")
            if attempt < retries:
                time.sleep(backoff * 2 ** (attempt - 1))
            else:
                logging.error(f"Giving up on query '{query}' after {retries} attempts.")
    return []
