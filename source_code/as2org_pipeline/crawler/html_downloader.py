from __future__ import annotations
from typing import Optional
import logging
import gc
import time
import trafilatura
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
DEFAULT_GOTO_TIMEOUT_MS = 40000
DEFAULT_STATE_TIMEOUT_MS = 20000
CONTEXT_RESTART_THRESHOLD = 500
MAX_RETRIES = 2
CRAWL_RATE_LIMIT_SEC = 1.0
DEFAULT_HEADERS = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8', 'Accept-Language': 'en-GB,en-NZ;q=0.9,en-AU;q=0.8,en;q=0.7,en-US;q=0.6', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

class HtmlDownloader:

    def __init__(self, total_num_of_work):
        self._pw = sync_playwright().start()
        self._browser = self._pw.firefox.launch(headless=True)
        self._context = self._browser.new_context(extra_http_headers=DEFAULT_HEADERS)
        self._crawl_counter = 0
        self._success_counter = 0
        self._start_time = time.time()
        self._total = total_num_of_work

    def _restart_context(self):
        try:
            self._context.close()
        except Exception:
            pass
        try:
            self._browser.close()
        except Exception:
            pass
        self._browser = self._pw.firefox.launch(headless=True)
        self._context = self._browser.new_context(extra_http_headers=DEFAULT_HEADERS)
        elapsed = time.time() - self._start_time
        if self._crawl_counter > 0:
            succeed_rate = self._success_counter / self._crawl_counter * 100
            avg_time = elapsed / self._crawl_counter
            if self._total:
                remaining = self._total - self._crawl_counter
                eta = avg_time * remaining
                eta_str = f', ETA: {eta / 60:.1f} min'
            else:
                eta_str = ''
            logging.warning(f'One batch finished — total: {self._crawl_counter}, success: {self._success_counter}, rate: {succeed_rate:.2f}%, elapsed: {elapsed:.1f}s, avg: {avg_time:.2f}s/page{eta_str}')
        self._crawl_counter = 0
        self._success_counter = 0
        self._start_time = time.time()
        gc.collect()

    def _scrape_once(self, url: str) -> Optional[str]:
        page = None
        try:
            page = self._context.new_page()
            page.goto(url, timeout=DEFAULT_GOTO_TIMEOUT_MS)
            page.wait_for_load_state('domcontentloaded', timeout=DEFAULT_STATE_TIMEOUT_MS)
            page.wait_for_selector('body', timeout=5000)
            html = page.content()
            content = trafilatura.extract(html, output_format='xml')
            if content:
                self._success_counter += 1
            return content
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def crawl_webpage(self, url: str) -> Optional[str]:
        if self._crawl_counter >= CONTEXT_RESTART_THRESHOLD:
            self._restart_context()
        time.sleep(CRAWL_RATE_LIMIT_SEC)
        self._crawl_counter += 1
        for attempt in range(MAX_RETRIES):
            try:
                return self._scrape_once(url)
            except PlaywrightTimeoutError:
                logging.warning('Timeout scraping %s (attempt %d)', url, attempt + 1)
            except Exception as e:
                logging.warning('Error scraping %s (attempt %d): %s', url, attempt + 1, e)
        logging.warning('Failed to scrape %s after %d attempts', url, MAX_RETRIES)
        return None

    def close(self) -> None:
        for obj in [self._context, self._browser, self._pw]:
            try:
                obj.close() if hasattr(obj, 'close') else obj.stop()
            except Exception:
                pass
