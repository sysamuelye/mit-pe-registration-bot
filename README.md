# MIT PE registration helper

Local browser helper for MIT Q2 Fall 2026 registration on **October 7, 2026, at 8:00 a.m. America/New_York**.

| Priority | Section | Course | Schedule |
| --- | --- | --- | --- |
| First | PE.0612-1 | Skate, Beginner | Monday/Wednesday, 1 p.m. |
| Backup | PE.0612-2 | Skate, Beginner | Monday/Wednesday, 2 p.m. |

The helper checks the quarter, course, schedule, openings, and $20 fee before attempting one enrollment. It tries the backup when the first section is listed as full. If a seat disappears during submission, the outcome is ambiguous, both sections are full, or the form is unfamiliar, it stops for manual review. It does not join waitlists or accept agreements.

## Validation and limitations

The v3 login and section-list dry run succeeded on the user's Mac. Q2 enrollment controls were unavailable during development, so **the final enrollment action has not been tested**. The Windows v4 path has been inspected and syntax checked, but has not been run on Windows. Enrollment is best effort; no seat is guaranteed. Be at the computer around 7:55 a.m. for login or form prompts.

This is a dated helper. Armed mode refuses to start after the opening time. Running before 8 a.m. waits until opening, then checks for Q2 for up to two minutes. Default mode is read-only. Keep your clock synchronized and your internet connected.

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

After login, press Enter and verify that Terminal says `ARMED`. Armed v4 starts `caffeinate` automatically to prevent idle sleep. Leave Terminal and the browser open, the Mac plugged in, and its lid open. Closing the lid can still suspend it.

## Windows

Requires Python 3.10+ with the `py` launcher and a Windows version supported by Playwright. Extract all files from the ZIP before running them.

1. Run `setup_windows.bat` once. It creates a local virtual environment, installs Playwright and the `tzdata` timezone database, and downloads Chromium.
2. Run `test_windows.bat`. Log in manually in the opened browser, complete Duo, and press Enter in the console after reaching the PE homepage. Check for the successful dry-run message.
3. Close the dry run, then run `run_windows.bat`. After login, press Enter and check for `ARMED`.

Armed v4 prevents Windows idle sleep until the script exits. Keep the PC powered, connected, and its lid open. It cannot prevent shutdown, restart, forced sleep, or VM suspension. If using a Windows VM, also keep the host awake.

Equivalent PowerShell commands after setup:

```powershell
.\.venv\Scripts\python.exe mit_pe_bot.py
.\.venv\Scripts\python.exe mit_pe_bot.py --arm
```

## Login and publishing

Login happens locally in a separate browser profile. The script does not collect passwords or Duo codes. The profile folder contains authentication cookies; **do not upload it**. Upload only the source files included in this package. `.gitignore` excludes the profile, virtual environment, and caches for Git-based uploads; it does not protect files manually selected in GitHub's web uploader.

GitHub hosting does not run this bot. Run it locally; do not put MIT credentials or browser profiles into GitHub Actions.

To publish without a Git client, create an empty repository on GitHub, choose **Add file > Upload files**, and upload only these seven package files: `mit_pe_bot.py`, `requirements.txt`, `README.md`, `.gitignore`, `setup_windows.bat`, `test_windows.bat`, and `run_windows.bat`.

## Official references

- [MIT registration information](https://physicaleducationandwellness.mit.edu/registration-information/registration/)
- [MIT registration portal](https://eduapps.mit.edu/mitpe/student/registration/home)
- [Q2 schedule](https://physicaleducationandwellness.mit.edu/wp-content/uploads/Q2-Schedule-To-post-10-5-26.pdf)
- [Playwright Python installation](https://playwright.dev/python/docs/library)

This is an unofficial helper, unaffiliated with MIT.
