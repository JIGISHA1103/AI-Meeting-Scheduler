from app.services.scheduling_service import schedule_meeting


print("========== PHASE 6 PARTICIPANT TEST ==========")


result = schedule_meeting(
    "Schedule a project meeting with "
    "rahul@gmail.com and priya@gmail.com "
    "on August 11, 2026 at 3 PM for 30 minutes."
)


print("\n========== PHASE 6 TEST RESULT ==========")
print(result)
print("==========================================")