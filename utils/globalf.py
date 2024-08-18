import re

def validate_sql_injection(data):
    # Check if data contains SQL injection
    dangerous_keywords = ["exec", "EXEC", "select", "SELECT"]
    if any(keyword in data for keyword in dangerous_keywords):
        return True

    if any(char in data for char in ["'", ";", "--", "/*", "*/", "@", "`", '"']):
        return True

    return False