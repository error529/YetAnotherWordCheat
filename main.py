#   YAWC (Yet Another Word Cheat)
#   Inspired by Qwertz_exe
#   Copyright (C) 2025 @http529
#
#   MIT License

#   Copyright (c) [year] [fullname]

#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:

#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.

#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.

import asyncio
import os
import sys
import re
import pyperclip
import requests
from playwright.async_api import async_playwright, Page



def start_screen():
    print(r'__   __ ___        ______ ')
    print(r'\ \ / // \ \      / / ___|')
    print(r' \ V // _ \ \ /\ / / |    ')
    print(r'  | |/ ___ \ V  V /| |___ ')
    print(r'  |_/_/   \_\_/\_/  \____|')
    print('  YetAnotherWordCheat')
    print(r'  (C) 2025 @http529 ')
    print("\n \n \n \n")


# --- Configuration ---
APP_DIR = os.path.join(os.environ['LOCALAPPDATA'], 'YAWC')
CHROME_PLAYWRIGHT_DIR = os.path.join(APP_DIR, 'playwright_data')
WORD_FILE = os.path.join(APP_DIR, 'words.txt')
URL_FILE = os.path.join(APP_DIR, 'channel.txt')
HAS_RUN = os.path.join(APP_DIR, 'state.txt')
DEFAULT_WORDS_URL = 'https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears.txt'

_playwright = None
_browser = None
word_freq = {}


# --- Helper Functions ---

def get_config(file: str, prompt: str, default: str = None) -> str:
    """Reads config from a file or prompts the user if it doesn't exist."""
    if os.path.isfile(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content
    user_input = input(f'{prompt}[default: {default}] ') or default
    if user_input:
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
    """Starts a persistent Playwright browser session with a dedicated user directory."""
    global _playwright, _browser
    print(f'Starting browser with persistent user data in: {path}')
    os.makedirs(path, exist_ok=True)
    _playwright = await async_playwright().start()
    if os.path.exists(HAS_RUN):
        _browser = await _playwright.chromium.launch_persistent_context(
            user_data_dir=path,
            headless=True,
            args=['--remote-debugging-port=9222']
        )
    else:
        with open(HAS_RUN, 'w') as f:
            f.write('1')
            print('After logging into discord please rerun this program')
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
        game_embeds = await page.locator('.grid__623de').all()
        for embed in reversed(game_embeds):
            content = await embed.text_content()
            if "Word Bomb" in content:
                if match := re.search(r'Letters(.{3})', content):
                    return match.group(1).strip()
    except Exception:
        pass
    return None


def analyze_and_copy_words(words: list[str]):
    """Analyzes the found words, displays the top 8, and copies the shortest of the top 4."""
    if not words:
        print('No words found.')
        return


    print("Top 8 most popular words:")
    for i, word in enumerate(words[:8]):
        print(f'{i + 1}. {word}')

    top4 = words[:4]

    if top4:
        shortest_word = min(top4, key=len)
        pyperclip.copy(shortest_word)
        print(f'Copied {shortest_word} clipboard.')
    else:
        print('\nLess than 4 words were found, so no word was copied.')


# --- Main Execution ---

async def main():
    """Main function to set up and run the bot."""
    print('Hello World')
    start_screen()
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
                analyze_and_copy_words(words)
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

