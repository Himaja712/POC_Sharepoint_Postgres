import json
import os
import pandas as pd
import time 
import datetime
import mysql.connector
import requests
from azure.identity import ClientSecretCredential
from config import client_id, client_secret, tenant_id, site_hostname, site_path, list_name, host, user, password, database, query, graph_api
import logging

logging.basicConfig(
    level=logging.INFO,  # show INFO from your app
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# disable azure-sdk verbose logs
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

# Fetch employees from MySQL
def get_mysql_data():
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()
        df = pd.DataFrame(rows, columns=columns)

        # Convert datetimes to strings
        for col in df.select_dtypes(include=["datetime64[ns]"]).columns:
            df[col] = df[col].astype(str)

        return df.to_dict(orient="records")
    except Exception as e:
        logger.error("MySQL error: %s", e)
        return []
    

def get_sp_data(site_id, list_id, headers):
    url = f"{graph_api}/{site_id}/lists/{list_id}/items?expand=fields"
    all_items = {}

    while url:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            logger.error("Error fetching SP data: %s %s", resp.status_code, resp.text)
            break

        data = resp.json()
        for item in data.get("value", []):
            emp_id = str(item["fields"].get("EmployeeCode")).strip()
            if emp_id:
                all_items[emp_id] = {
                    "id": item["id"],
                    "fields": item["fields"]
                }

        url = data.get("@odata.nextLink")  # Continue if there are more items

    return all_items


# Insert/Update/Delete employees in SharePoint list via Graph API
def upload_to_sharepoint(data):
    # Authenticate
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    token = credential.get_token("https://graph.microsoft.com/.default")
    headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}

    # Get Site ID
    site_url = f"{graph_api}{site_hostname}:{site_path}"
    site = requests.get(site_url, headers=headers).json()
    site_id = site["id"]

    # Get List ID
    list_url = f"{graph_api}{site_id}/lists/{list_name}"
    list_info = requests.get(list_url, headers=headers).json()
    list_id = list_info["id"]

    sp_data = get_sp_data(site_id, list_id, headers)

    # Build set of DB EmployeeIDs
    db_emp_ids = set()
    for row in data:
        emp_id = str(row.get("EmployeeCode", ""))  
        if emp_id:
            db_emp_ids.add(emp_id)
    added, updated, deleted, skipped = 0, 0, 0, 0

    for row in data:
        emp_id = str(row.get("EmployeeCode", ""))

        if not emp_id:
            skipped += 1
            continue  

        db_emp_ids.add(emp_id)

        with open(os.path.join(os.path.dirname(__file__), "payload_mapping.json")) as f:
            field_map = json.load(f)

        payload = {}

        for sp_field, db_field in field_map.items():
            # Handle placeholders like "{FirstName} {LastName}"
            if "{" in db_field and "}" in db_field:
                try:
                    payload[sp_field] = db_field.format(**row)
                except KeyError:
                    payload[sp_field] = ""
            else:
                payload[sp_field] = str(row.get(db_field, "")) or ""


        if emp_id in sp_data:
            # Compare fields with SharePoint
            existing_fields = sp_data[emp_id]["fields"]
            needs_update = False
            diff_log = []

            for field, new_val in payload.items():
                old_val = str(existing_fields.get(field, "") or "").strip()
                new_val = str(new_val or "").strip()
                if old_val != new_val:
                    needs_update = True
                    diff_log.append(f"{field}: '{old_val}' → '{new_val}'")

            if needs_update:
                item_id = sp_data[emp_id]["id"]
                update_url = f"{graph_api}/{site_id}/lists/{list_id}/items/{item_id}/fields"
                resp = requests.patch(update_url, headers=headers, json=payload)
                if resp.status_code in (200, 204):
                    updated += 1
                    logger.info(f"Updated EmployeeID {emp_id}: " + "; ".join(diff_log))
                else:
                    logger.error("Update error: %s %s", resp.status_code, resp.text)
            else:
                skipped += 1
                #print(f"Skipped EmployeeID {emp_id} (no changes)")
        else:
            # Insert new record
            insert_url = f"{graph_api}/{site_id}/lists/{list_id}/items"
            resp = requests.post(insert_url, headers=headers, json={"fields": payload})
            if resp.status_code == 201:
                added += 1
                logger.info(f"Inserted new EmployeeID {emp_id}")
                sp_data = get_sp_data(site_id, list_id, headers)
            else:
                logger.error("Insert error: %s %s", resp.status_code, resp.text)

    # Step 4: Delete SP items not in DB
    for emp_id, item in sp_data.items():
        if emp_id not in db_emp_ids:
            item_id = item["id"]
            delete_url = f"{graph_api}/{site_id}/lists/{list_id}/items/{item_id}"
            resp = requests.delete(delete_url, headers=headers)
            if resp.status_code in (200, 204):
                deleted += 1
                logger.info(f"Deleted EmployeeID {emp_id}")
                sp_data = get_sp_data(site_id, list_id, headers)
            else:
                logger.error("Delete error: %s %s", resp.status_code, resp.text)

    logger.info(f"{added} added, {updated} updated, {deleted} deleted, {skipped} skipped.")


# Schedular to trigger daily
def run_sync_job():
    logger.info(f"[SYNC] Triggered at {datetime.datetime.now()}")
    data = get_mysql_data()
    if data:
        upload_to_sharepoint(data)
    else:
        logger.info("No data fetched.")

if __name__ == "__main__":
    while True:
        try:
            run_sync_job()
        except Exception as e:
            logger.error(f"Error in sync job: {e}")
        time.sleep(24 * 60 * 60)

