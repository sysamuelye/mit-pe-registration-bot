#!/usr/bin/env python3
"""Reusable MIT PE registration helper for macOS and Windows.
Edit config.json each registration period. Default mode only checks the page.
Use --arm to wait for the configured opening; --arm --now starts immediately.
Login manually in the opened browser. Enrollment and waitlist controls remain
unverified on the live site; unfamiliar forms stop for manual completion.
"""

import argparse
import json
from decimal import Decimal
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
BASE = Path(__file__).resolve().parent
SETTINGS = None
OPENING = None


def load_config(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    zone = ZoneInfo(cfg['timezone'])
    naive = datetime.fromisoformat(cfg['opens_at'])
    if naive.tzinfo is not None:
        raise ValueError('opens_at must be local time without a UTC offset; use timezone.')
    opening = naive.replace(tzinfo=zone)
    if not isinstance(cfg['term'], str) or not cfg['term'].strip():
        raise ValueError('term is required, e.g. Q2 Fall 2026.')
    choices = cfg['choices']
    if not isinstance(choices, list) or not choices:
        raise ValueError('Add at least one choice.')
    ids = set()
    for choice in choices:
        for key in ('section', 'title', 'days', 'time', 'detail_schedule', 'max_fee'):
            if key not in choice:
                raise ValueError(f'Missing choice field: {key}')
        if not re.fullmatch(r'PE\.\d+-\d+', choice['section']) or choice['section'] in ids:
            raise ValueError('Section IDs must be valid and unique.')
        ids.add(choice['section'])
        if any(not isinstance(choice[k], str) or not choice[k].strip()
               for k in ('title', 'days', 'time', 'detail_schedule')):
            raise ValueError('Title and schedule fields must be nonempty strings.')
        fee = Decimal(str(choice['max_fee']))
        if not fee.is_finite() or fee < 0:
            raise ValueError('max_fee must be finite and nonnegative.')
    if type(cfg.get('waitlist_first_choice', False)) is not bool:
        raise ValueError('waitlist_first_choice must be true or false.')
    return cfg, opening



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
    stamp = datetime.now(OPENING.tzinfo) if OPENING else datetime.now().astimezone()
    print(stamp.strftime('%H:%M:%S'), message, flush=True)


def signed_in(page):
    if urlsplit(page.url).hostname != 'eduapps.mit.edu':
        return False
    return bool(re.search(r'\bWelcome\s+\S+', page.locator('body').inner_text()))


def correct_term(page):
    # Use the title, never an upcoming-term notice in the page body.
    return page.title().startswith(SETTINGS['term'] + ' Physical Education')


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


def attempt(page, choice, waitlist=False):
    section, clock = choice['section'], choice['time']
    link = page.get_by_role('link', name=section, exact=True)
    row = page.get_by_role('row').filter(has=link)
    if link.count() != 1 or row.count() != 1:
        raise RuntimeError(f'Cannot uniquely identify {section}.')
    cells = [x.strip() for x in row.locator('td').all_text_contents()]
    if len(cells) != 9 or cells[0] != section or cells[3] != choice['days'] or cells[4] != clock:
        raise RuntimeError(f'Unexpected section layout or schedule for {section}.')
    if cells[2] != choice['title']:
        raise RuntimeError('Course title mismatch.')
    if not cells[6].isdigit():
        raise RuntimeError('Cannot read available openings.')
    if int(cells[6]) == 0 and not waitlist:
        log(f'{section} is full; trying the next choice.')
        return False
    link.click()
    page.get_by_role('heading', name=f'Course Section {section}', exact=True).wait_for()
    guard(page)
    if not correct_term(page):
        raise RuntimeError('Wrong quarter on section detail page.')
    details = fields(page)
    if details.get('Section ID') != section or details.get('Course Title') != choice['title']:
        raise RuntimeError('Course detail mismatch.')
    schedule = details.get('Schedule', '')
    if choice['detail_schedule'] not in schedule:
        raise RuntimeError('Detail schedule mismatch.')
    fee = details.get('Fee')
    if not fee or not re.fullmatch(r'\$[\d,]+\.\d{2}', fee) or Decimal(fee.replace('$', '').replace(',', '')) > Decimal(str(choice['max_fee'])):
        raise RuntimeError(f'Unexpected fee {fee!r}; complete manually.')
    # Do not accept legal agreements or select unexamined inputs.
    controls = page.locator('input:not([type="hidden"]):not([type="submit"]):not([type="button"]), select, textarea')
    if any(control.is_visible() for control in controls.all()):
        raise RuntimeError('A form needs input; complete manually.')
    names = ('Register', 'Register for this Section', 'Register for Course', 'Add Course', 'Add Section')
    if waitlist and int(cells[6]) == 0:
        names += ('Join Waitlist', 'Join Wait List', 'Add to Waitlist', 'Add to Wait List', 'Waitlist')
    candidates = []
    for role in ('button', 'link'):
        for name in names:
            for control in page.get_by_role(role, name=name, exact=True).all():
                if control.is_visible() and control.is_enabled():
                    candidates.append(control)
    if len(candidates) != 1:
        raise RuntimeError('Enrollment control is unfamiliar or unavailable; complete manually.')
    if re.search(r'by (?:clicking|registering)|I agree|terms and conditions|accept.*waiver', page.locator('body').inner_text(), re.I):
        raise RuntimeError('Agreement requires your review; complete manually.')
    log(f'Attempting {section} ({clock}), fee {fee}, waitlist allowed: {waitlist}. Submitting once.')
    candidates[0].click(no_wait_after=True)
    # A JS confirmation is left to the user. Never submit a second time.
    page.wait_for_timeout(1000)
    guard(page)
    if not correct_term(page):
        raise RuntimeError('Submission outcome is unknown; check browser before further action.')
    # Home status provides authoritative enrollment, not the section capacity.
    page.goto(HOME, wait_until='domcontentloaded')
    guard(page)
    status = fields(page)
    if (correct_term(page) and status.get('Section ID') == section
            and re.fullmatch(r'Registered(?:\s*:?\s*)', status.get('Status', ''), re.I)):
        log(f'CONFIRMED: enrolled in {section}.')
        return True
    if (waitlist and correct_term(page) and status.get('Section ID') == section
            and re.fullmatch(r'Waitlist position\s*:\s*\d+', status.get('Status', ''), re.I)):
        log(f'CONFIRMED: {section}, {status["Status"]}.')
        return True
    raise RuntimeError('Enrollment/waitlist not confirmed. Check the browser; no further submit will occur.')


def main():
    global SETTINGS, OPENING
    print('MIT PE bot v5 - configurable courses and waitlist fallback', flush=True)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--arm', action='store_true', help='Actually attempt registration at opening time')
    parser.add_argument('--config', type=Path, default=BASE / 'config.json')
    parser.add_argument('--now', action='store_true', help='With --arm, attempt immediately instead of waiting')
    args = parser.parse_args()
    if args.now and not args.arm:
        parser.error('--now requires --arm')
    try:
        SETTINGS, OPENING = load_config(args.config)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    log('Target term: ' + SETTINGS['term'])
    for i, choice in enumerate(SETTINGS['choices'], 1):
        log(f'{i}. {choice["section"]}: {choice["title"]}, {choice["days"]} {choice["time"]}, max fee ${choice["max_fee"]}')
    log('First-choice waitlist fallback: ' + str(SETTINGS.get('waitlist_first_choice', False)))
    if args.arm and not args.now and datetime.now(OPENING.tzinfo) > OPENING:
        parser.error('Opening time has passed. Check config or use --arm --now explicitly.')
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
                log('ARMED for ' + ('immediate attempt' if args.now else OPENING.isoformat()))
                log('Keep this window open. Recheck login shortly before the opening time.')
                while not args.now and (remaining := (OPENING - datetime.now(OPENING.tzinfo)).total_seconds()) > 0:
                    page.wait_for_timeout(min(remaining, 1) * 1000)
                deadline = time.monotonic() + 120
                while True:
                    page.goto(HOME, wait_until='domcontentloaded')
                    guard(page)
                    existing = fields(page)
                    if correct_term(page) and existing.get('Status'):
                        raise RuntimeError('Target term already has a registration or waitlist entry; check manually.')
                    open_list(page)
                    guard(page)
                    if correct_term(page):
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Target term has not appeared within two minutes. Complete manually.')
                    page.wait_for_timeout(2000)
                for choice in SETTINGS['choices']:
                    if attempt(page, choice):
                        break
                else:
                    if SETTINGS.get('waitlist_first_choice', False):
                        log('All choices full. Trying the first choice with waitlist allowed.')
                        page.goto(HOME, wait_until='domcontentloaded')
                        guard(page)
                        if not correct_term(page) or fields(page).get('Status'):
                            raise RuntimeError('Term changed or registration exists; check manually.')
                        open_list(page)
                        attempt(page, SETTINGS['choices'][0], waitlist=True)
                    else:
                        log('All choices full. Waitlist fallback disabled.')
        except Exception as exc:
            log(f'STOPPED: {exc}')
            print('\a', end='', flush=True)
        finally:
            input('Browser stays open for review/manual registration. Enter to close it: ')
            context.close()


if __name__ == '__main__':
    main()
