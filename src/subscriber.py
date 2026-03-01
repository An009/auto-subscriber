import threading
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from .logger import logger
from .database import Database
from .detector import detect_form
from .submitter import fill_email, submit_form
from typing import Callable, List

class SubscriberWorker(threading.Thread):
    def __init__(self, urls: List[str], emails: List[str], headless: bool, retries: int, extra_wait: int,
                 progress_callback: Callable, log_callback: Callable, result_callback: Callable):
        super().__init__()
        self.urls = urls
        self.emails = emails
        self.headless = headless
        self.retries = retries
        self.extra_wait = extra_wait
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
            
            total_tasks = len(self.urls) * len(self.emails)
            current_task = 0
            
            for url in self.urls:
                for email in self.emails:
                    self._pause_event.wait()
                    
                    if self._stop_event.is_set():
                        self.log_callback("Worker cancelled.")
                        break
                        
                    current_task += 1
                    self.progress_callback(current_task - 1, total_tasks, url, f"loading ({email})")
                    success = False
                    error_msg = ""
                    
                    for attempt in range(1, self.retries + 1):
                        self._pause_event.wait()
                        if self._stop_event.is_set():
                            break
                            
                        self.log_callback(f"Processing {url} for {email} (Attempt {attempt}/{self.retries})")
                        
                        page = context.new_page()
                        try:
                            page.goto(url, timeout=60000, wait_until="domcontentloaded")
                            
                            if self.extra_wait > 0:
                                self.log_callback(f"[{url}] Waiting extra {self.extra_wait}ms for page ready...")
                                page.wait_for_timeout(self.extra_wait)
                                
                            self.progress_callback(current_task - 1, total_tasks, url, f"detecting ({email})")
                            
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
                                self.progress_callback(current_task - 1, total_tasks, url, f"filling ({email})")
                                # Wait fallback for 10s as requested
                                if fill_email(page, selector, email, timeout=10000):
                                    self.progress_callback(current_task - 1, total_tasks, url, f"submitting ({email})")
                                    if submit_form(page, selector):
                                        page.wait_for_timeout(3000) # Wait for confirmation
                                        status = "SUCCESS"
                                        success = True
                                        self.log_callback(f"[{url}] {status} for {email}")
                                    else:
                                        status = "FAILED_TO_SUBMIT"
                                        error_msg = "Could not submit the form."
                                        self.log_callback(f"[{url}] {status}: {error_msg}")
                                else:
                                    status = "FAILED_TO_FILL_EMAIL"
                                    error_msg = "Element didn't appear within 10s or could not fill the email input."
                                    self.log_callback(f"[{url}] {status}: {error_msg}")
                                    
                        except PlaywrightTimeoutError as e:
                            status = "TIMEOUT"
                            error_msg = f"Page load or element wait timeout: {e}"
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
                            
                if self._stop_event.is_set():
                    break
                    
            browser.close()
            if not self._stop_event.is_set():
                self.progress_callback(total_tasks, total_tasks, "Done", "Finished")

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()
