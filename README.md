# Google Analytics 4 + Search Console → Google Sheets Data Pipeline

## Overview

### Objective

This project automates the monthly collection of key web analytics metrics from **Google Analytics 4 (GA4)** and **Google Search Console**, then writes them cleanly into a **Google Sheet**.

It was designed for reliable, repeatable monthly reporting so that stakeholders can review performance without manual data exports or copy-paste work.

### What the pipeline does every month

1. Calculates the previous calendar month (or a month you specify).
2. Fetches core metrics from Google Analytics 4:
   - Active users
   - New users
   - Event count
   - Average engagement time (formatted as `mm:ss`)
   - Engaged sessions by channel (Organic Social, Direct, Organic Search, Referral)
   - Users who triggered selected custom events (`user_spent_2_minutes`, `bli_medlem_klick`)
3. Fetches aggregate metrics from Google Search Console:
   - Clicks
   - Impressions
   - Click-through rate (CTR)
   - Average position
4. Checks whether a row for that month already exists in the target Google Sheet (to avoid duplicates).
5. If the sheet is empty, automatically creates a formatted header row (bold + frozen).
6. Appends a new data row and formats the CTR column as a percentage.
7. Logs everything and can optionally notify you (Slack / email) if something fails.

### Tools & technologies

| Tool / Library                        | Purpose                                      |
|---------------------------------------|----------------------------------------------|
| Python 3.10+                          | Core language                                |
| Google Analytics Data API (v1beta)    | Fetch GA4 metrics                            |
| Google Search Console API             | Fetch search performance metrics             |
| Google Sheets API                     | Write and format data                        |
| Service Account (OAuth 2.0)           | Secure, non-interactive authentication       |
| python-dotenv                         | Load configuration from `.env` file          |
| requests                              | Optional Slack notifications                 |

### Project outcomes

- Fully automated monthly reporting with zero manual data collection.
- Duplicate-safe (skips writing if the month already exists).
- Dry-run mode for safe testing.
- Clean, maintainable multi-file codebase that is easy to extend.
- Optional failure notifications so problems are noticed quickly.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Google Cloud setup (one-time)](#2-google-cloud-setup-one-time)
   - 2.1 Create a Google Cloud project
   - 2.2 Enable required APIs
   - 2.3 Create a service account
   - 2.4 Create and download a JSON key
   - 2.5 Grant permissions in Google Analytics 4
   - 2.6 Share the Google Sheet with the service account
   - 2.7 Grant permissions in Google Search Console
3. [Local project setup](#3-local-project-setup)
   - 3.1 Download / clone the project
   - 3.2 Create a virtual environment
   - 3.3 Install dependencies
   - 3.4 Configure the `.env` file
4. [Running the pipeline](#4-running-the-pipeline)
   - 4.1 Normal run (previous month)
   - 4.2 Dry-run (preview only)
   - 4.3 Specific month
5. [Understanding the Google Sheet output](#5-understanding-the-google-sheet-output)
6. [Scheduling the pipeline (recommended)](#6-scheduling-the-pipeline-recommended)
   - 6.1 Windows Task Scheduler
   - 6.2 Linux / macOS cron
   - 6.3 GitHub Actions (optional)
7. [Project structure explained](#7-project-structure-explained)
8. [How to extend the pipeline](#8-how-to-extend-the-pipeline)
9. [Troubleshooting](#9-troubleshooting)
10. [Security notes](#10-security-notes)

---

## 1. Prerequisites

Before you begin, make sure you have:

- A Google account with access to:
  - The Google Analytics 4 property you want to report on
  - The Google Search Console property (website)
  - The destination Google Sheet (or permission to create one)
- Python 3.10 or newer installed on the machine that will run the script
- Basic ability to open a terminal / command prompt

---

## 2. Google Cloud setup (one-time)

These steps only need to be done once. After that, the same service account can be reused every month.

### 2.1 Create a Google Cloud project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown at the top → **New Project**.
3. Give it a clear name, for example: `GA4-Sheets-Reporter`.
4. Click **Create**.
5. Make sure the new project is selected in the top bar.

### 2.2 Enable required APIs

1. In the left menu go to **APIs & Services → Library**.
2. Search for and enable each of the following:
   - **Google Analytics Data API**
   - **Google Sheets API**
   - **Google Search Console API** (sometimes listed as “Search Console API”)

You can also enable them directly via these links (while the correct project is selected):

- [Google Analytics Data API](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com)
- [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
- [Google Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)

### 2.3 Create a service account

1. Go to **IAM & Admin → Service Accounts**.
2. Click **+ Create Service Account**.
3. Name it something clear, e.g. `ga4-sheets-reporter`.
4. Optionally add a description.
5. Click **Create and Continue**.
6. You can skip granting project-level roles for now (we will grant access at the resource level).
7. Click **Done**.

### 2.4 Create and download a JSON key

1. On the Service Accounts page, click the service account you just created.
2. Go to the **Keys** tab.
3. Click **Add Key → Create new key**.
4. Choose **JSON** and click **Create**.
5. A JSON file will download automatically.  
   **Store this file safely.** Treat it like a password.
6. Rename it if you like (e.g. `service-account.json`) and note the full path where you save it.

> **Note:** Some organizations have a policy that disables service-account key creation. If you see an error, an administrator needs to temporarily allow key creation or provide you with a key.

### 2.5 Grant permissions in Google Analytics 4

1. Open [Google Analytics](https://analytics.google.com/).
2. Select the correct property.
3. Go to **Admin** (gear icon at the bottom left).
4. In the **Property** column, click **Property access management**.
5. Click the **+** button → **Add users**.
6. Paste the **service account email** (it looks like `ga4-sheets-reporter@your-project.iam.gserviceaccount.com`).
7. Give it the role **Viewer** (read-only is enough).
8. Uncheck “Notify new users by email” if you prefer.
9. Click **Add**.

### 2.6 Share the Google Sheet with the service account

1. Open (or create) the Google Sheet that will receive the data.
2. Click the **Share** button.
3. Paste the same service account email.
4. Give it **Editor** access (needed so the script can write and format cells).
5. Uncheck “Notify people” if desired.
6. Click **Share** / **Send**.

Also note the **Spreadsheet ID** — it is the long string in the URL between `/d/` and `/edit`:

```
https://docs.google.com/spreadsheets/d/1ABc-dEFGhI-Jkl34--mNoPQ/edit
                                         ↑ this part is the SHEET_ID
```

### 2.7 Grant permissions in Google Search Console

1. Open [Google Search Console](https://search.google.com/search-console).
2. Select the correct property (your website).
3. Go to **Settings → Users and permissions**.
4. Click **Add user**.
5. Paste the service account email.
6. Choose permission level **Full** (or at least the level that allows reading search analytics data).
7. Click **Add**.

---

## 3. Local project setup

### 3.1 Download / clone the project

If you received a zip file:

```bash
unzip ga4_sheets_reporter.zip
cd ga4_sheets_reporter
```

If you are using Git:

```bash
git clone <repository-url>
cd ga4_sheets_reporter
```

### 3.2 Create a virtual environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

You should now see `(.venv)` in your terminal prompt.

### 3.3 Install dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `google-analytics-data`
- `google-api-python-client`
- `google-auth`
- `python-dotenv`
- `requests`

### 3.4 Configure the `.env` file

1. Copy the example file:

```bash
cp .env.example .env
```

2. Open `.env` in any text editor and fill in the real values:

```env
# ---------------------------------------------------------------------------
# Required
# ---------------------------------------------------------------------------
SERVICE_ACCOUNT_FILE=/absolute/path/to/your-service-account.json
SHEET_ID=1ABc-dEFGhI-Jkl34--mNoPQ
SHEET_NAME=2024
GA4_PROPERTY_ID=properties/123456789
SITE_URL=https://www.ideellmarknadsforing.se/

# ---------------------------------------------------------------------------
# Optional
# ---------------------------------------------------------------------------
LOG_FILE=data_integration.log

# Slack notification on failure (leave empty to disable)
SLACK_WEBHOOK_URL=

# Email notification on failure (leave empty to disable)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFY_EMAIL_TO=
```

**Important notes:**

- `SERVICE_ACCOUNT_FILE` must be the **full absolute path** to the JSON key you downloaded earlier.
- `GA4_PROPERTY_ID` must start with `properties/` followed by the numeric ID (you can find it in GA4 Admin → Property Settings).
- `SITE_URL` must match exactly the URL registered in Search Console (including `https://` and the trailing slash if that is how it is registered).
- Never commit the real `.env` file or the JSON key to Git (they are already listed in `.gitignore`).

---

## 4. Running the pipeline

Make sure your virtual environment is activated and you are inside the project folder.

### 4.1 Normal run (previous calendar month)

```bash
python main.py
```

This will:

- Calculate the previous month
- Fetch data from GA4 and Search Console
- Check for an existing row for that month
- Write a new row (or skip if it already exists)
- Log the result

### 4.2 Dry-run (preview only – recommended first time)

```bash
python main.py --dry-run
```

This fetches the data and prints exactly what would be written to the sheet, but **does not modify the sheet**. Perfect for testing.

### 4.3 Specific month

```bash
python main.py --month 2025-03
python main.py --month 2025-03 --dry-run
```

Useful for back-filling a missing month or re-processing historical data.

---

## 5. Understanding the Google Sheet output

When the sheet is empty, the script automatically writes this header row (bold + frozen):

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Month | Users | New Users | Events | Avg Engagement (mm:ss) | Eng. Sessions – Organic Social | Eng. Sessions – Direct | Eng. Sessions – Organic Search | Eng. Sessions – Referral | Users – spent ≥2 min | Users – Bli medlem click | GSC Clicks | GSC Impressions | GSC CTR | GSC Avg Position |

Each subsequent monthly run appends one row with the corresponding values.  
The **CTR** column (N) is automatically formatted as a percentage with one decimal place (e.g. `3.2%`).

---

## 6. Scheduling the pipeline (recommended)

### 6.1 Windows Task Scheduler

1. Open **Task Scheduler**.
2. Click **Create Basic Task**.
3. Name it e.g. `Monthly GA4 Sheets Report`.
4. Trigger: **Monthly** → choose day 2 or 3 of the month (gives Google a day to finalize data).
5. Action: **Start a program**.
6. Program/script: full path to your Python executable inside the virtual environment, for example:
   ```
   C:\Users\YourName\projects\ga4_sheets_reporter\.venv\Scripts\python.exe
   ```
7. Add arguments: `main.py`
8. Start in (optional but recommended): the full path to the project folder.
9. Finish and test by right-clicking the task → **Run**.

### 6.2 Linux / macOS cron

Edit the crontab:

```bash
crontab -e
```

Add a line (runs at 06:00 on the 2nd of every month):

```cron
0 6 2 * * cd /full/path/to/ga4_sheets_reporter && /full/path/to/ga4_sheets_reporter/.venv/bin/python main.py >> /full/path/to/ga4_sheets_reporter/cron.log 2>&1
```

### 6.3 GitHub Actions (optional)

You can also run the pipeline from GitHub Actions using a scheduled workflow and store the service-account JSON as a repository secret. Contact the developer if you want this set up.

---

## 7. Project structure explained

```
ga4_sheets_reporter/
├── main.py                 # Entry point + CLI + orchestration
├── config.py               # Loads .env and holds constants (channels, events, headers)
├── models.py               # Simple data classes (GA4Data, SearchConsoleData)
├── auth.py                 # Loads the service-account credentials
├── ga4.py                  # All Google Analytics 4 API logic
├── search_console.py       # All Search Console API logic
├── sheets.py               # Reading, writing and formatting the Google Sheet
├── utils.py                # Date helpers, retry decorator, notifications
├── requirements.txt        # Python dependencies
├── .env.example            # Template for configuration
├── .gitignore
└── README.md               # This file
```

This separation makes the code easier to maintain, test, and extend.

---

## 8. How to extend the pipeline

### Change tracked channels or custom events

Edit the lists in `config.py`:

```python
CHANNELS = [
    "Organic Social",
    "Direct",
    "Organic Search",
    "Referral",
]

CUSTOM_EVENTS = [
    "user_spent_2_minutes",
    "bli_medlem_klick",
]
```

Also update the `HEADERS` list in the same file so the sheet columns stay correct, and update the `build_row()` function in `main.py` if necessary.

### Add more metrics

1. Add the metric to the appropriate request in `ga4.py` or `search_console.py`.
2. Store it in the corresponding data class (`models.py`).
3. Add a header in `config.py`.
4. Include the value in `build_row()` inside `main.py`.

### Enable failure notifications

Fill in either (or both) of these sections in `.env`:

- `SLACK_WEBHOOK_URL` – a Slack incoming webhook URL
- SMTP settings + `NOTIFY_EMAIL_TO` – for email alerts

---

## 9. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| `Configuration errors: SERVICE_ACCOUNT_FILE not found` | Wrong path in `.env` | Use the full absolute path to the JSON key |
| `403 Permission denied` on GA4 | Service account not added to the GA4 property | Re-check step 2.5 |
| `403` or empty data from Search Console | Service account not added, or wrong `SITE_URL` | Re-check step 2.7 and the exact URL format |
| `Sheet 'XXXX' not found` | Wrong `SHEET_NAME` in `.env` | Check the exact tab name in the spreadsheet |
| Month is skipped | Row for that month already exists | Delete the existing row if you want to re-write it |
| CTR appears as a decimal instead of % | Formatting step failed | Re-run; the script applies percent formatting automatically |
| Script works in dry-run but fails when writing | Sheet not shared with Editor rights | Re-check step 2.6 |

Logs are written both to the console and to the file defined by `LOG_FILE` (default: `data_integration.log`). Always check the log when something goes wrong.

---

## 10. Security notes

- The service-account JSON key grants access to your analytics and spreadsheet data. Keep it private.
- Never commit `.env` or the JSON key to version control.
- Prefer giving the service account the **minimum** permissions needed (Viewer on GA4, Editor only on the specific Sheet, appropriate level on Search Console).
- Rotate the key periodically if your security policy requires it.

---

## Support

If you run into problems during setup or later monthly runs, contact the person who delivered this pipeline and include:

1. The exact command you ran
2. The full error message / log excerpt
3. Confirmation that the service account has the correct permissions

---

*This pipeline is designed to be reliable, transparent, and easy to maintain so your team can focus on insights instead of manual data collection.*
