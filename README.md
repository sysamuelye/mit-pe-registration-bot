# MIT PE registration helper

Reusable local browser helper for MIT PE registration. Edit `config.json` for each registration period. The included configuration targets **Q2 Fall 2026, October 7 at 8 a.m. Boston time**.

| Priority | Section | Course | Schedule |
| --- | --- | --- | --- |
| First | PE.0612-1 | Skate, Beginner | Monday/Wednesday, 1 p.m. |
| Backup | PE.0612-2 | Skate, Beginner | Monday/Wednesday, 2 p.m. |

The helper checks the quarter, course, schedule, openings, and $20 fee before attempting one enrollment. It tries the backup when the first section is listed as full. If a seat disappears during submission, the outcome is ambiguous, both sections are full, or the form is unfamiliar, it stops for manual review. If every configured choice is full, it returns to the first choice and attempts the waitlist. A seat that becomes available there is also acceptable. Set `waitlist_first_choice` to `false` to disable this fallback. It does not accept agreements.

## Validation and limitations

The v3 login and section-list dry run succeeded on the user's Mac. Q2 enrollment controls were unavailable during development, so **the final enrollment action has not been tested**. The Windows path has been inspected and syntax checked, but has not been run on Windows. Enrollment is best effort; no seat is guaranteed. Be at the computer around 7:55 a.m. for login or form prompts.

Armed mode refuses to start after the configured opening time unless you explicitly pass `--arm --now`. Running before opening waits, then checks for the configured term for up to two minutes. Default mode is read-only. Keep your clock synchronized and your internet connected.

## Choose classes and reuse each semester

Edit `config.json` with any plain-text editor. Changes take effect when you restart the bot; they do not affect a currently running process.

- `opens_at`: registration opening in local time, e.g. `2026-12-02T08:00:00`.
- `timezone`: normally `America/New_York`, even if your computer is elsewhere.
- `term`: exact term prefix shown in the registration page title, e.g. `Q2 Fall 2026`. Copy the actual label for IAP or another quarter; do not guess it. The bot checks the page title to avoid enrolling in an old term.
- `choices`: one or more sections in priority order. They can be different classes.
- `waitlist_first_choice`: `true` means try open seats in all choices, then the first choice's waitlist. It never joins a backup's waitlist.

Each choice must specify `section`, exact course `title`, `days` as displayed in the list (such as `MW` or `TR`), `time` as displayed (such as `1:00 PM`), `detail_schedule` as displayed on the detail page (such as `Mon, Wed 1:00 PM`), and `max_fee` in dollars. Copy section IDs from the current term: IDs and schedules can change between quarters.

For example, replace a choice with the following **only after checking these values against the current schedule**:

```json
{
  "section": "PE.0202-2",
  "title": "Swimming, Beginner",
  "days": "MW",
  "time": "1:00 PM",
  "detail_schedule": "Mon, Wed 1:00 PM",
  "max_fee": 20
}
```

To keep separate presets:

```bash
python3 mit_pe_bot.py --config my-classes.json
python3 mit_pe_bot.py --config my-classes.json --arm
```

Default run checks login and the list, and prints the planned choices. It cannot verify next term's section details before the site publishes them. Run the read-only check when the target term becomes visible too.

After opening, an intentional immediate attempt is:

```bash
python3 mit_pe_bot.py --arm --now
```

Do not run multiple armed instances for the same MIT account. Stop an old bot with Ctrl+C before starting a new configuration. If a submit has already occurred, check your registration status before restarting.

Waitlist controls and final submission remain unverified against the live site. A familiar register button on a full section may create a waitlist entry; the bot checks the home status for `Waitlist position : N` before reporting success. Unknown controls, legal agreements, forms requiring input, or ambiguous results stop automation. It never drops an existing registration to pursue another class.

## macOS

Requires Python 3.10+. In Terminal, change into this extracted project folder, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 mit_pe_bot.py
```

Log in manually in the browser opened by the script and complete Duo. Once the PE homepage appears, press Enter in Terminal. A successful dry run prints `Verified: signed in and section-list table found.` Close the test with Enter, then start the timed attempt:

```bash
python3 mit_pe_bot.py --arm
```

After login, press Enter and verify that Terminal says `ARMED`. Armed mode starts `caffeinate` automatically to prevent idle sleep. Leave Terminal and the browser open, the Mac plugged in, and its lid open. Closing the lid can still suspend it.

## Windows

Requires Python 3.10+ with the `py` launcher and a Windows version supported by Playwright. Extract all files from the ZIP before running them.

1. Run `setup_windows.bat` once. It creates a local virtual environment, installs Playwright and the `tzdata` timezone database, and downloads Chromium.
2. Run `test_windows.bat`. Log in manually in the opened browser, complete Duo, and press Enter in the console after reaching the PE homepage. Check for the successful dry-run message.
3. Close the dry run, then run `run_windows.bat`. After login, press Enter and check for `ARMED`.

Armed mode prevents Windows idle sleep until the script exits. Keep the PC powered, connected, and its lid open. It cannot prevent shutdown, restart, forced sleep, or VM suspension. If using a Windows VM, also keep the host awake.

Equivalent PowerShell commands after setup:

```powershell
.\.venv\Scripts\python.exe mit_pe_bot.py
.\.venv\Scripts\python.exe mit_pe_bot.py --arm
```

## Login and publishing

Login happens locally in a separate browser profile. The script does not collect passwords or Duo codes. The profile folder contains authentication cookies; **do not upload it**. Upload only the source files included in this package. `.gitignore` excludes the profile, virtual environment, and caches for Git-based uploads; it does not protect files manually selected in GitHub's web uploader.

GitHub hosting does not run this bot. Run it locally; do not put MIT credentials or browser profiles into GitHub Actions.

To publish without a Git client, create an empty repository on GitHub, choose **Add file > Upload files**, and upload only the source and configuration files: `mit_pe_bot.py`, `config.json`, `requirements.txt`, `README.md`, `.gitignore`, `setup_windows.bat`, `test_windows.bat`, and `run_windows.bat`.

## Official references

- [MIT registration information](https://physicaleducationandwellness.mit.edu/registration-information/registration/)
- [MIT registration portal](https://eduapps.mit.edu/mitpe/student/registration/home)
- [Q2 schedule](https://physicaleducationandwellness.mit.edu/wp-content/uploads/Q2-Schedule-To-post-10-5-26.pdf)
- [Playwright Python installation](https://playwright.dev/python/docs/library)

This is an unofficial helper, unaffiliated with MIT.
