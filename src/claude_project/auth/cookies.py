"""Extract sessionKey from Claude.ai via Playwright browser."""

from __future__ import annotations

from claude_project.exceptions import AuthError


async def extract_session_key_browser() -> str:
    """Launch browser to claude.ai, wait for login, extract sessionKey.

    Uses system Chrome so existing sessions are detected automatically.
    If not logged in, the user completes login in the browser window.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise AuthError(
            "Browser login requires playwright. Install with:\n"
            "  pipx inject claude-project playwright && playwright install chromium\n"
            "Or use manual cookie: claude-project auth login --cookie <sessionKey>"
        )

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
            )
        except Exception:
            # Fall back to bundled chromium if system Chrome unavailable
            try:
                browser = await p.chromium.launch(headless=False)
            except Exception as e:
                raise AuthError(
                    f"Could not launch browser: {e}\n"
                    "Run: playwright install chromium"
                )

        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://claude.ai/login")

        # Wait for sessionKey cookie to appear (user logs in or is already logged in)
        # Poll cookies until we find it, with a generous timeout
        import asyncio

        session_key = None
        for _ in range(600):  # 5 minutes max
            cookies = await context.cookies("https://claude.ai")
            for cookie in cookies:
                if cookie["name"] == "sessionKey" and cookie["value"]:
                    session_key = cookie["value"]
                    break
            if session_key:
                break
            await asyncio.sleep(0.5)

        await browser.close()

        if not session_key:
            raise AuthError("Timed out waiting for login. No sessionKey cookie found.")

        return session_key
