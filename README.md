# American Corner Mtaani — WhatsApp Volunteer Management Bot

An intelligent, zero-cost task allocation and volunteer tracking bot designed for **American Corner Mtaani (KNLS Mtaani Community Hub)** under the U.S. Embassy Nairobi Public Diplomacy Section.

---

##  The Core Philosophy: Zero-Friction Task Assignment

Previous volunteer management systems (custom mobile apps, Notion pages, standalone websites) suffered from **adoption drop-off**. Volunteers do not want to install extra apps or remember extra credentials. 

This solution meets volunteers and the coordinator where they already communicate every day: **WhatsApp**.

Instead of interacting awkwardly with a bot, the Coordinator speaks **directly to the volunteer** in natural team language in the group chat:
> *"@task @Faith could you please inspect the Makerbot 3D printer wiring by tomorrow 3pm?"*  
> *"@Brian @task please organize the chess tables for Barbah Games this Saturday at 10am"*

The bot silently listens in the group, activates when `@task` is mentioned, and handles the rest:
1. **Dissects the Message (Gemini 2.5 Flash / Resilient Heuristic Engine)**: Extracts the assignee, actionable task, deadline, and priority.
2. **Fuzzy Identity Resolution**: Matches `@Faith` or `Brian` against the pre-seeded American Corner Mtaani volunteer directory (`Faith Wanjiru` $\rightarrow$ `+254712573126`).
3. **Private WhatsApp DM**: Dispatches a private, formatted WhatsApp message to the assigned volunteer with 1-touch numeric actions (`1` to Accept, `2` if Unavailable, `Done` when finished).
4. **Group Decorum**: Sends a single, clean receipt to the group (`📌 Task #TSK-1001 logged for @Faith Wanjiru. Details sent via DM.`) keeping the group chat tidy.
5. **Real-Time Coordinator Dashboard**: Syncs automatically to SQLite and **Google Sheets** for effortless reporting.

---

##  Quick Start (Running the Demo)

### 1. Install Dependencies
```bash
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```
*(By default, `WHATSAPP_PROVIDER="mock"` is enabled, allowing team members to run and test everything immediately without needing a WhatsApp instance.)*

### 3. Launch the Server
```bash
python run.py
```
Or with uvicorn:
```bash
uvicorn app.main:app --port 8000 --reload
```

### 2. Open the Interactive Fail-Safe Web Simulator
Navigate in your browser to:
 **`http://localhost:8000/`**

The Web Simulator provides a side-by-side view:
- **Left Panel (Group Chat)**: Type coordinator messages or click one of the quick test scenario chips.
- **Center Panel (Operations Dashboard & Sheets Mirror)**: Watch the task ledger, KPI counters, and parsed JSON update in real time.
- **Right Panel (Volunteer Phone)**: See the private WhatsApp DM arrive on the volunteer's phone, click `1️⃣ Accept` or `🎉 Mark Done`, and see the state machine transition live!

---

## Automated Test Suite

Run the end-to-end automated tests with:
```bash
python -m unittest tests/test_flow.py
```

---

## Configuration (`.env`)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TASK_TRIGGER_TAG` | Trigger tag for the bot | `@task` |
| `GEMINI_API_KEY` | Google Gemini API Key | *(Optional; includes offline heuristic fallback)* |
| `WHATSAPP_PROVIDER` | `mock` (for simulator/testing) or `green_api` (for live WhatsApp) | `mock` |
| `GREEN_API_INSTANCE_ID` | Green API Developer Instance ID | `""` |
| `GREEN_API_TOKEN` | Green API Developer Token | `""` |
| `ENABLE_SHEETS_SYNC` | Enable live Google Sheets updates | `false` |
| `GOOGLE_SHEET_ID` | Target Google Sheet spreadsheet ID | `""` |

---
