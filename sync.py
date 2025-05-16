import sys
import requests
from requests.auth import HTTPBasicAuth
from tabulate import tabulate

# ------------------ CONFIG ------------------
KC_URL    = "https://openstack-test-1.rugghiaeassociati.com:9444"
KC_REALM  = "tcp"
KC_CLIENT = "alfresco"
KC_SECRET = "6f70a28f-98cd-41ca-8f2f-368a8797d708"
KC_USER   = "sync_user"
KC_PASS   = "sync_user"

ALF_URL   = "https://openstack-test-1.rugghiaeassociati.com:8081/alfresco/api/-default-/public/alfresco/versions/1"
ALF_ADM   = "admin"
ALF_PWD   = "admin"
# --------------------------------------------

# ——— Keycloak helpers ——————————————————————
def kc_token():
    r = requests.post(
        f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/token",
        data={
            "grant_type":    "password",
            "client_id":     KC_CLIENT,
            "client_secret": KC_SECRET,
            "username":      KC_USER,
            "password":      KC_PASS
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    r.raise_for_status()
    return r.json()["access_token"]

def kc_groups(token):
    r = requests.get(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups",
        headers={"Authorization": f"Bearer {token}"}
    )
    r.raise_for_status()
    return r.json()

def kc_members(token, group_id):
    r = requests.get(
        f"{KC_URL}/admin/realms/{KC_REALM}/groups/{group_id}/members",
        headers={"Authorization": f"Bearer {token}"}
    )
    r.raise_for_status()
    return r.json()

# ——— Alfresco helpers ———————————————————————————
AUTH = HTTPBasicAuth(ALF_ADM, ALF_PWD)

def alf_groups():
    r = requests.get(f"{ALF_URL}/groups", auth=AUTH)
    r.raise_for_status()
    return { e["entry"]["id"] for e in r.json()["list"]["entries"] }

def alf_users():
    r = requests.get(f"{ALF_URL}/people", auth=AUTH)
    r.raise_for_status()
    return { e["entry"]["id"]: e["entry"].get("email","-")
             for e in r.json()["list"]["entries"] }

def alf_create_group(name):
    alf_id = name if name.upper().startswith("GROUP_") else f"GROUP_{name}"
    r = requests.post(
        f"{ALF_URL}/groups",
        json={"id": alf_id, "displayName": name},
        auth=AUTH
    )
    if r.status_code == 409:
        print(f"   · [Info] {alf_id} già esistente")
    elif r.status_code not in (200,201):
        print(f"   · [Errore {r.status_code}] creando {alf_id}: {r.text.splitlines()[0]}")

def alf_delete_group(group_id):
    r = requests.delete(f"{ALF_URL}/groups/{group_id}", auth=AUTH)
    if r.status_code in (200,204):
        print(f"   · [Info] Gruppo {group_id} cancellato in Alfresco")
    else:
        print(f"   · [Errore {r.status_code}] eliminando {group_id}: {r.text.splitlines()[0]}")

def alf_add_member(name, user):
    alf_id = name if name.upper().startswith("GROUP_") else f"GROUP_{name}"
    url = f"{ALF_URL}/groups/{alf_id}/members"
    payload = {"id": user, "memberType": "PERSON"}
    r = requests.post(
        url,
        json=payload,
        auth=AUTH,
        headers={"Content-Type": "application/json"}
    )
    if r.status_code in (200,201):
        return
    if r.status_code == 409:
        print(f"      · [Info] {user} già membro di {alf_id}")
    else:
        print(f"      · [Errore {r.status_code}] aggiungendo {user}: {r.text.splitlines()[0]}")

def alf_create_user(user):
    payload = {
        "id": user["username"],
        "firstName": user.get("firstName", "-"),
        "lastName": user.get("lastName", "-"),
        "email": user.get("email", "-"),
        "password": "Test1234@"
    }
    r = requests.post(f"{ALF_URL}/people", json=payload, auth=AUTH)
    if r.status_code in (200,201):
        print(f"   · [Info] Creato utente {user['username']}")
    elif r.status_code == 409:
        print(f"   · [Info] Utente {user['username']} già esistente")
    else:
        print(f"   · [Errore {r.status_code}] creando {user['username']}: {r.text}")

# ——— Main —————————————————————————————————————
def main():
    try:
        token = kc_token()
    except Exception as e:
        print("❌ Errore ottenimento token Keycloak:", e)
        sys.exit(1)

    kc_list  = kc_groups(token)
    kc_names = { g["name"] for g in kc_list }

    expected_alf = {
        name if name.upper().startswith("GROUP_") else f"GROUP_{name}"
        for name in kc_names
    }

    all_alf = alf_groups()

    skip_prefixes = (
        "GROUP_ALFRESCO_", "GROUP_EMAIL_",
        "GROUP_SITE_", "GROUP_site_",
        "GROUP_DEMO_TEAM", "GROUP_Group_"
    )
    to_remove = [
        g for g in all_alf
        if g.startswith("GROUP_")
           and g not in expected_alf
           and not any(g.startswith(pref) for pref in skip_prefixes)
    ]
    if to_remove:
        print("\n\033[91mRimozione gruppi NON più in Keycloak:\033[0m")
    for g in to_remove:
        alf_delete_group(g)

    ag = alf_groups()
    au = alf_users()

    print("\n\033[94mGruppi Alfresco:\033[0m")
    print(tabulate([[g] for g in sorted(ag)], ["ID"], tablefmt="grid"))
    print("\n\033[94mUtenti Alfresco:\033[0m")
    print(tabulate([[u,e] for u,e in au.items()], ["Username","Email"], tablefmt="grid"))
    print("\n\033[94mGruppi Keycloak:\033[0m")
    print(tabulate([[n] for n in sorted(kc_names)], ["ID"], tablefmt="grid"))
    print()

    # 7) sincronizza creazione e membership
    synced = []
    for grp in kc_list:
        name = grp["name"]
        print(f"[Gruppo] {name}")
        
        if (name if name.upper().startswith("GROUP_") else f"GROUP_{name}") not in ag:
            alf_create_group(name)

        for m in kc_members(token, grp["id"]):
            u = m["username"]

            if u not in au:
                print(f"   · crea utente {u} in Alfresco")
                alf_create_user(m)

            print(f"   · sync {u}")
            alf_add_member(name, u)
            synced.append([u, m.get("email", "-"), m.get("firstName", "-"), m.get("lastName", "-")])

    print("\n\033[92mMembri sincronizzati:\033[0m")
    print(tabulate(synced, ["Username", "Email", "First", "Last"], tablefmt="grid"))

if __name__ == "__main__":
    main()
