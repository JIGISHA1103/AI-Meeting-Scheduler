import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google import genai


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Gemini API Key
# --------------------------------------------------

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise Exception(
        "GEMINI_API_KEY not found in .env file"
    )


print("================================")
print("Gemini API Key Loaded Successfully")
print("================================")


# --------------------------------------------------
# Gemini Client
# --------------------------------------------------

client = genai.Client(
    api_key=api_key
)


# --------------------------------------------------
# Parse Meeting Request
# --------------------------------------------------

def parse_meeting_request(user_input: str):

    # --------------------------------------------------
    # Get today's date in Indian Standard Time
    # --------------------------------------------------

    today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%Y-%m-%d")


    # --------------------------------------------------
    # Gemini Prompt
    # --------------------------------------------------

    prompt = f"""
You are an AI Meeting Scheduling Assistant.

Today's date is {today}.
The user's timezone is Asia/Kolkata (IST).

Use today's date to correctly resolve relative dates.

Examples:

- "today" -> today's date
- "tomorrow" -> one day after today's date
- "day after tomorrow" -> two days after today's date
- "next Monday" -> the next Monday after today's date
- "next Friday" -> the next Friday after today's date

Your task is to extract meeting details from the user's request.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanations.

Rules:

1. Identify the meeting intent.
2. Extract the meeting title.
3. Extract all participants.
4. Extract the date.
5. Extract the time.
6. Extract the duration in minutes.


Date and time formatting rules:

- Return date strictly in YYYY-MM-DD format.
- Return time strictly in HH:MM format using the 24-hour clock.
- Resolve relative dates such as "today", "tomorrow",
  "day after tomorrow", and "next Monday" into actual
  calendar dates using today's date provided above.
- Resolve times such as "3 PM", "3:30 PM", and "noon"
  into 24-hour format.
- Use Asia/Kolkata timezone.


Duration rules:

- "30 minutes" -> 30
- "45 minute meeting" -> 45
- "1 hour meeting" -> 60
- "2 hour meeting" -> 120
- "2.5 hours" -> 150
- If duration is not mentioned, return 60.


Meeting title rules:

- If the user specifies a title, use it.
- If the user says "project meeting", use "Project meeting".
- If no title is specified, use "Meeting".


Participant rules:

- Extract every person/email address mentioned as a participant.
- If an email address is provided, return the email address exactly.
- Example:
  "with rahul@gmail.com and priya@gmail.com"
  ->
  ["rahul@gmail.com", "priya@gmail.com"]

- If a person's name is provided without an email address,
  return the person's name.
- Example:
  "with Rahul and Priya"
  ->
  ["Rahul", "Priya"]

- Do not invent email addresses.
- Do not convert names into fake email addresses.
- If no participants are mentioned, return an empty array.

Intent rules:

- For a request to arrange, schedule, book, or create a meeting,
  return "schedule_meeting".


Return JSON in exactly this format:

{{
    "intent": "schedule_meeting",
    "title": "",
    "participants": [],
    "date": "",
    "time": "",
    "duration": 60
}}

User Request:
{user_input}
"""


    # --------------------------------------------------
    # Send request to Gemini
    # --------------------------------------------------

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )


    # --------------------------------------------------
    # Display raw Gemini response
    # --------------------------------------------------

    print("\n========== RAW GEMINI RESPONSE ==========")
    print(response.text)
    print("=========================================\n")


    # --------------------------------------------------
    # Clean Gemini response
    # --------------------------------------------------

    text = response.text.strip()


    # Remove markdown formatting if Gemini adds it

    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()


    # --------------------------------------------------
    # Convert JSON string into Python dictionary
    # --------------------------------------------------

    try:

        result = json.loads(text)

    except json.JSONDecodeError as error:

        print("\n========== JSON PARSING ERROR ==========")
        print(error)
        print("Gemini returned:")
        print(text)
        print("========================================\n")

        raise ValueError(
            "Gemini returned invalid JSON."
        )


    # --------------------------------------------------
    # Validate participants
    # --------------------------------------------------

    if "participants" not in result:
        result["participants"] = []


    if not isinstance(result["participants"], list):
        result["participants"] = []


    # --------------------------------------------------
    # Display parsed meeting
    # --------------------------------------------------

    print("\n========== PARSED MEETING ==========")
    print(result)
    print("====================================\n")


    return result