import requests

KEYCLOAK_URL = "http://localhost:8081"
KEYCLOAK_REALM = "test"
KEYCLOAK_CLIENT_ID = "alfresco"
KEYCLOAK_CLIENT_SECRET = "6f70a28f-98cd-41ca-8f2f-368a8797d708"
KEYCLOAK_USERNAME = "f.mayer"
KEYCLOAK_PASSWORD = "Ttclab@2025!"

url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
data = {
    "grant_type": "password",
    "client_id": KEYCLOAK_CLIENT_ID,
    "client_secret": KEYCLOAK_CLIENT_SECRET,
    "username": KEYCLOAK_USERNAME,
    "password": KEYCLOAK_PASSWORD
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

response = requests.post(url, data=data, headers=headers)

print(response.status_code)
print(response.text)
