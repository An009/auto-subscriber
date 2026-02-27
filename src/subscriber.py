import threading
from playwright.sync_api import sync_playwright
from .logger import logger
from .database import Database
from .detector import detect_form
from .submitter import fill_email, submit_form
from typing import Callable, List

class SubscriberWorker(threading.Thread):
    def __init__(self, urls: List[str], email: str, headless: bool, retries: int,
                 progress_callback: Callable, log_callback: Callable, result_callback: Callable):
        super().__init__()
        self.urls = urls
        self.email = email
        self.headless = headless
        self.retries = retries
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.result_callback = result_callback
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set() # Set means not paused
        self.db = Database()

    def run(self):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            
            for index, url in enumerate(self.urls):
                self._pause_event.wait()
                
                if self._stop_event.is_set():
                    self.log_callback("Worker cancelled.")
                    break
                    
                self.progress_callback(index, len(self.urls), url, "loading")
                success = False
                error_msg = ""
                
                for attempt in range(1, self.retries + 1):
                    self._pause_event.wait()
                    if self._stop_event.is_set():
                        break
                        
                    self.log_callback(f"Processing {url} (Attempt {attempt}/{self.retries})")
                    
                    page = context.new_page()
                    try:
                        page.goto(url, timeout=60000, wait_until="domcontentloaded")
                        self.progress_callback(index, len(self.urls), url, "detecting")
                        
                        html = page.content()
                        selector = detect_form(html)
                        
                        if not selector:
                            # Try frames
                            frames = page.frames
                            for frame in frames:
                                html = frame.content()
                                selector = detect_form(html)
                                if selector:
                                    break

                        if not selector:
                            status = "NO_FORM_FOUND"
                            error_msg = "Could not detect a subscription form."
                            self.log_callback(f"[{url}] {status}: {error_msg}")
                        else:
                            self.progress_callback(index, len(self.urls), url, "filling")
                            if fill_email(page, selector, self.email):
                                self.progress_callback(index, len(self.urls), url, "submitting")
                                if submit_form(page, selector):
                                    page.wait_for_timeout(3000) # Wait for confirmation
                                    status = "SUCCESS"
                                    success = True
                                    self.log_callback(f"[{url}] {status}")
                                else:
                                    status = "FAILED_TO_SUBMIT"
                                    error_msg = "Could not submit the form."
                                    self.log_callback(f"[{url}] {status}: {error_msg}")
                            else:
                                status = "FAILED_TO_FILL_EMAIL"
                                error_msg = "Could not fill the email input."
                                self.log_callback(f"[{url}] {status}: {error_msg}")
                                
                    except Exception as e:
                        status = "ERROR"
                        error_msg = str(e)
                        self.log_callback(f"[{url}] {status}: {error_msg}")
                        logger.error(f"Error processing {url}: {e}", exc_info=True)
                    finally:
                        page.close()
                        
                    self.db.insert_or_update_job(url, status, attempt, error_msg)
                    self.result_callback(url, status, attempt, error_msg)
                    
                    if success:
                        break
                        
            browser.close()
            if not self._stop_event.is_set():
                self.progress_callback(len(self.urls), len(self.urls), "Done", "Finished")

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()
