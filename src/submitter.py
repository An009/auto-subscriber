from playwright.sync_api import Page
from .logger import logger

def fill_email(page: Page, selector: str, email: str, timeout: int = 10000) -> bool:
    try:
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.fill(email)
        return True
    except Exception as e:
        logger.error(f"Failed to fill email using locator: {e}", exc_info=True)
        # Fallback to evaluate
        try:
            logger.info("Trying fallback evaluate for filling email.")
            page.evaluate(f"""(sel, val) => {{
                const el = document.querySelector(sel);
                if (el) {{
                    el.value = val;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}""", selector, email)
            return True
        except Exception as fallback_e:
            logger.error(f"Fallback evaluate failed: {fallback_e}", exc_info=True)
            return False

def submit_form(page: Page, selector: str) -> bool:
    try:
        # Try finding submit button inside the form containing the input
        form_locator = page.locator(selector).locator("xpath=ancestor::form").first
        if form_locator.count() > 0:
            submit_btn = form_locator.locator('button[type="submit"], input[type="submit"]').first
            if submit_btn.count() > 0:
                submit_btn.click(timeout=10000)
                return True
            else:
                # Click nearest button
                btn = form_locator.locator('button').first
                if btn.count() > 0:
                    btn.click(timeout=10000)
                    return True
                else:
                    # JS submit
                    form_locator.evaluate("form => form.submit()")
                    return True
        else:
            # Press enter in the input
            page.locator(selector).first.press("Enter", timeout=10000)
            return True
    except Exception as e:
        logger.error(f"Failed to submit form: {e}", exc_info=True)
        return False
