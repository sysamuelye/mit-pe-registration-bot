#!/usr/bin/env python3
"""MIT PE registration helper. Python 3.10+ and Playwright required.

Install: python3 -m pip install playwright
         python3 -m playwright install chromium
Test:    python3 mit_pe_bot.py
Run:     caffeinate -i python3 mit_pe_bot.py --arm

Log in manually in the Chromium window this script opens, then press Enter
in Terminal. Default mode only checks the section-list layout. --arm waits
until 2026-10-07 08:00 America/New_York and attempts ONE enrollment.
Keep the Mac awake, connected, and the browser open. Recheck login shortly
before 8 AM. This local browser does not share ChatGPT's login session.

LIMITATION: Q2 and its enrollment controls were unavailable during creation.
Enrollment button names below are conservative candidates, not verified.
Unknown controls, agreements, authentication, ambiguous outcomes, and both
sections being full stop automation. No waitlist signup or repeated submit.
The browser remains open for manual completion after every outcome.
"""

import argparse
from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

HOME = 'https://eduapps.mit.edu/mitpe/student/registration/home'
OPENING = datetime(2026, 10, 7, 8, tzinfo=ZoneInfo('America/New_York'))
CHOICES = [('PE.0612-1', '1:00 PM'), ('PE.0612-2', '2:00 PM')]
BASE = Path(__file__).resolve().parent


@contextmanager
def keep_awake(enabled):
    """Prevent idle sleep while armed; restore the prior Windows state."""
    process = None
    previous = None
    kernel = None
    try:
        if enabled and sys.platform == 'win32':
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.SetThreadExecutionState.argtypes = [wintypes.DWORD]
            kernel.SetThreadExecutionState.restype = wintypes.DWORD
            previous = kernel.SetThreadExecutionState(0x80000001)
            if not previous:
                raise OSError('Could not prevent Windows idle sleep.')
            log('Windows idle-sleep prevention enabled. Keep the lid open.')
        elif enabled and sys.platform == 'darwin':
            process = subprocess.Popen(['caffeinate', '-i', '-w', str(os.getpid())])
            log('macOS idle-sleep prevention enabled. Keep the lid open.')
        yield
    finally:
        if kernel is not None and previous:
            kernel.SetThreadExecutionState(previous)
        if process is not None:
            process.terminate()
            process.wait()


def log(message):
    print(datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M:%S'), message, flush=True)


def signed_in(page):
    if urlsplit(page.url).hostname != 'eduapps.mit.edu':
        return False
    return bool(re.search(r'\bWelcome\s+\S+', page.locator('body').inner_text()))


def quarter_is_q2(page):
    # Do not confuse the upcoming Q2 notice on the Q1 home page with Q2.
    return bool(re.match(r'^Q2 Fall 2026 Physical Education', page.title()))


def fields(page):
    result = {}
    for row in page.locator('tr').all():
        cells = row.locator('td').all_text_contents()
        if len(cells) == 2:
            result[cells[0].strip()] = cells[1].strip()
    return result


def open_list(page):
    link = page.get_by_role('link', name=re.compile(r'View Course Sections'))
    if link.count() != 1:
        raise RuntimeError('Cannot identify the course-section link; complete manually.')
    link.click()
    page.locator('table#section').wait_for()


def guard(page):
    if not signed_in(page):
        raise RuntimeError('Login expired or a login step is required. Complete it manually.')
    text = page.locator('body').inner_text()
    if re.search(r'verify you are human|unusual traffic|automated traffic|captcha|access denied|checking your browser', text, re.I):
        raise RuntimeError('Site verification or access block; complete manually. No retries.')


def attempt(page, section, clock):
    link = page.get_by_role('link', name=section, exact=True)
    row = page.get_by_role('row').filter(has=link)
    if link.count() != 1 or row.count() != 1:
        raise RuntimeError(f'Cannot uniquely identify {section}.')
    cells = [x.strip() for x in row.locator('td').all_text_contents()]
    if len(cells) != 9 or cells[0] != section or cells[3] != 'MW' or cells[4] != clock:
        raise RuntimeError(f'Unexpected section layout or schedule for {section}.')
    if 'Skate, Beginner' not in cells[2]:
        raise RuntimeError('Course title mismatch.')
    if not cells[6].isdigit():
        raise RuntimeError('Cannot read available openings.')
    if int(cells[6]) == 0:
        log(f'{section} is full; trying the next choice.')
        return False
    link.click()
    page.get_by_role('heading', name=f'Course Section {section}', exact=True).wait_for()
    guard(page)
    if not quarter_is_q2(page):
        raise RuntimeError('Wrong quarter on section detail page.')
    details = fields(page)
    if details.get('Section ID') != section or details.get('Course Title') != 'Skate, Beginner':
        raise RuntimeError('Course detail mismatch.')
    schedule = details.get('Schedule', '')
    if f'Mon, Wed {clock}' not in schedule:
        raise RuntimeError('Detail schedule mismatch.')
    fee = details.get('Fee')
    if fee != '$20.00':
        raise RuntimeError(f'Unexpected fee {fee!r}; complete manually.')
    # Do not accept legal agreements or select unexamined inputs.
    controls = page.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea')
    if any(control.is_visible() for control in controls.all()):
        raise RuntimeError('A form needs input; complete manually.')
    candidates = []
    for role in ('button', 'link'):
        for name in ('Register', 'Register for this Section', 'Register for Course', 'Add Course', 'Add Section'):
            for control in page.get_by_role(role, name=name, exact=True).all():
                if control.is_visible() and control.is_enabled():
                    candidates.append(control)
    if len(candidates) != 1:
        raise RuntimeError('Enrollment control is unfamiliar or unavailable; complete manually.')
    if re.search(r'by (?:clicking|registering)|I agree|terms and conditions|accept.*waiver', page.locator('body').inner_text(), re.I):
        raise RuntimeError('Agreement requires your review; complete manually.')
    log(f'Attempting {section} ({clock}), $20 fee. Submitting once.')
    candidates[0].click(no_wait_after=True)
    # A JS confirmation is left to the user. Never submit a second time.
    page.wait_for_timeout(1000)
    guard(page)
    if page.get_by_role('heading', name=re.compile(r'^Q2 Fall 2026')).count() == 0:
        raise RuntimeError('Submission outcome is unknown; check browser before further action.')
    # Home status provides authoritative enrollment, not the section capacity.
    page.goto(HOME, wait_until='domcontentloaded')
    guard(page)
    status = fields(page)
    if (quarter_is_q2(page) and status.get('Section ID') == section
            and re.fullmatch(r'Registered(?:\s*:?\s*)', status.get('Status', ''), re.I)):
        log(f'CONFIRMED: enrolled in {section}.')
        return True
    raise RuntimeError('Enrollment not confirmed. Check the browser; no further submit will occur.')


def main():
    print('MIT PE bot v4 - macOS and Windows', flush=True)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--arm', action='store_true', help='Actually attempt registration at opening time')
    args = parser.parse_args()
    if args.arm and datetime.now(OPENING.tzinfo) > OPENING:
        parser.error('Opening time has passed. This dated script will not run late.')
    from playwright.sync_api import sync_playwright
    with keep_awake(args.arm), sync_playwright() as pw:
        profile = BASE / 'mit-pe-local-profile'
        profile.mkdir(mode=0o700, exist_ok=True)
        context = pw.chromium.launch_persistent_context(str(profile), headless=False)
        context.set_default_timeout(6000)
        context.set_default_navigation_timeout(20000)
        page = context.pages[0] if context.pages else context.new_page()
        page.on('dialog', lambda dialog: log('Browser confirmation needs your manual response.'))
        try:
            page.goto(HOME, wait_until='domcontentloaded')
            input('Log in manually in this Chromium window. Then press Enter here: ')
            # input() blocks synchronous Playwright's event dispatch. Process
            # pending redirects/popups before reading cached Page.url values.
            page.wait_for_timeout(500)
            # Authentication can finish in a different browser tab.
            for candidate in context.pages:
                if not candidate.is_closed() and signed_in(candidate):
                    page = candidate
                    break
            if not signed_in(page):
                page.goto(HOME, wait_until='domcontentloaded')
                page.wait_for_timeout(500)
            if not signed_in(page):
                log('Current page: ' + urlsplit(page.url).hostname + urlsplit(page.url).path)
            guard(page)
            open_list(page)
            log('Verified: signed in and section-list table found.')
            if not args.arm:
                log('DRY RUN complete. No enrollment attempted. Re-run with --arm when ready.')
            else:
                log(f'ARMED for {OPENING.isoformat()}; first PE.0612-1, then PE.0612-2.')
                log('Keep this window open. Login may expire; check it again around 7:55 AM.')
                while (remaining := (OPENING - datetime.now(OPENING.tzinfo)).total_seconds()) > 0:
                    page.wait_for_timeout(min(remaining, 1) * 1000)
                deadline = time.monotonic() + 120
                while True:
                    page.goto(HOME, wait_until='domcontentloaded')
                    guard(page)
                    existing = fields(page)
                    if quarter_is_q2(page) and existing.get('Status'):
                        raise RuntimeError('Q2 already has a registration or waitlist entry; check manually.')
                    open_list(page)
                    guard(page)
                    if quarter_is_q2(page):
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Q2 has not appeared within two minutes. Complete manually.')
                    page.wait_for_timeout(2000)
                for section, clock in CHOICES:
                    if attempt(page, section, clock):
                        break
                else:
                    log('Both choices full. No waitlist enrollment attempted.')
        except Exception as exc:
            log(f'STOPPED: {exc}')
            print('\a', end='', flush=True)
        finally:
            input('Browser stays open for review/manual registration. Enter to close it: ')
            context.close()


if __name__ == '__main__':
    main()
