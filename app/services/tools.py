# TOOLS = {
#     "leave_summary": {
#         "endpoint": "/api/leave/summary",
#         "method": "GET"
#     }
# }

TOOLS = {
    "leave_summary": {
        "endpoint": "/Hrms/mobile/leave/get/leavesummary",
        "method": "GET",
        "requires": ["employee_id"]
    }
}