import libsql_client

TURSO_URL = "libsql://invigilator-app-lgowda15.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3ODMxODQzNjMsImlkIjoiMDE5ZjJlMTAtYWYwMS03YWZmLWJlOTctYzRhOTExMzdjNjU3Iiwia2lkIjoiUW5iOWR4ajA1bTFwcVhRdEV1ZUR2d0Uwc09lbmM0b0x6Yi11TERHTE5kWSIsInJpZCI6ImU5NDFhMjU5LThmZjEtNDNmNC1iYTRiLWFjZTYyY2QyNTM0ZSJ9.ed38Y8AwJS4IxRtBeR-VHHC9WrOruGjrhcMW6x6KYEnX-R6R0k0aLWuq1iO2jHPa0v-2oFHYwgoyrxFyU-uIDA"

url = TURSO_URL.replace("libsql://", "https://")

try:
    client = libsql_client.create_client_sync(url=url, auth_token=TURSO_TOKEN)
    print("✅ Connection successful")
    
    # Try a simple query
    result = client.execute("SELECT 1")
    print(f"✅ Query successful: {result}")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}")
    print(f"Details: {e}")
    import traceback
    traceback.print_exc()