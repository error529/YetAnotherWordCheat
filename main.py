#   YAWC (Yet Another Word Cheat)
#   Inspired by Qwertz_exe
#   Copyright (C) 2025 @http529
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import asyncio
import sys
import re
import pyperclip
import requests
from playwright.async_api import async_playwright, Page

# --- Configuration ---
APP_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'YAWC')
CHROME_PLAYWRIGHT_DIR = os.path.join(APP_DIR, 'playwright_data')
WORD_FILE = os.path.join(APP_DIR, 'words.txt')
URL_FILE = os.path.join(APP_DIR, 'channel.txt')
SESSION_FILE = os.path.join(APP_DIR, 'session.txt')
DEFAULT_WORDS_URL = 'https://raw.githubusercontent.com/first20hours/google-10000-english/refs/heads/master/google-10000-english-usa-no-swears.txt'

_playwright = None
_browser = None


# --- Helper Functions ---

def get_config(file: str, prompt: str, default: str = None) -> str:
    """Reads config from a file or prompts the user if it doesn't exist."""
    if os.path.isfile(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content

    user_input = input(f'{prompt}[default: {default}] ') or default
    if user_input and input('Save for next time? (y/n): ').lower() == 'y':
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(user_input)
    return user_input


def init_words():
    """Downloads the wordlist if it's missing."""
    os.makedirs(APP_DIR, exist_ok=True)
    url = input(f'Wordlist URL? [default: {DEFAULT_WORDS_URL}] ') or DEFAULT_WORDS_URL
    try:
        print(f'Downloading wordlist from {url}...')
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(WORD_FILE, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f'Wordlist saved to {WORD_FILE}')
    except requests.exceptions.RequestException as e:
        print(f'Failed to download wordlist: {e}', file=sys.stderr)
        sys.exit(1)


async def start_browser(path: str):
    """Starts a persistent Playwright browser session without verbose logging."""
    global _playwright, _browser
    _playwright = await async_playwright().start()
    _browser = await _playwright.chromium.launch_persistent_context(
        user_data_dir=path, 
        headless=False, 
        args=['--remote-debugging-port=9222']
    )


async def stop_browser():
    """Closes the browser session quietly."""
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()


def find_words(substring: str) -> list[str]:
    """Finds all words in the wordlist containing the substring."""
    try:
        with open(WORD_FILE, 'r', encoding='utf-8') as f:
            return [word.strip() for word in f if substring.lower() in word.lower()]
    except FileNotFoundError:
        print('Wordlist not found. Please restart to initialize it.', file=sys.stderr)
        return []


async def get_letters(page: Page) -> str | None:
    """Scans for the latest Word Bomb letters and returns them."""
    try:
        for embed in reversed(await page.locator('.grid__623de').all()):
            content = await embed.text_content()
            if "Word Bomb" in content:
                if match := re.search(r'Letters(.{3})', content):
                    return match.group(1).strip()
    except Exception:
        pass
    return None


# --- Main Execution ---

async def main():
    """Main function to set up and run the bot."""
    if not os.path.isfile(WORD_FILE):
        init_words()

    url = get_config(URL_FILE, 'Discord Channel URL: ', 'https://discord.com/app')
    session_dir = CHROME_PLAYWRIGHT_DIR

    if not url or not session_dir:
        print("URL and session path are required to run.", file=sys.stderr)
        sys.exit(1)

    await start_browser(session_dir)
    page = await _browser.new_page()
    last_letters = None

    try:
        print(f'Navigating to Discord channel...')
        await page.goto(url, timeout=60000)
        print("\nMonitoring for new letters. Press Ctrl+C to exit.")

        while True:
            letters = await get_letters(page)
            if letters and letters != last_letters:
                last_letters = letters
                print(f'\nNew letters detected: {last_letters}')
                words = find_words(last_letters)
                if words:
                    pyperclip.copy(min(words, key = len))
                    print(f'Found {len(words)} words. Copied "{words[0]}" to clipboard.')
                    for word in words[1:6]:  
                        print(f'  - {word}')
                else:
                    print(f'No words found for "{last_letters}"')
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print('\nExiting...')
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
    finally:
        await page.close()
        await stop_browser()


if __name__ == '__main__':
    asyncio.run(main())
