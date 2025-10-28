1. Azure App Registration: Ensure proper API permissions are granted for Microsoft Graph API and SharePoint:
Microsoft Graph API: Sites.ReadWrite.All, Sites.Selected
SharePoint: Sites.FullControl.All, Sites.ReadWrite.All, Sites.Selected

2. Database Access: Administrator access is required for establishing the database connection.

3. SharePoint List Configuration: The column headers in the SharePoint list must exactly match the database table column names to avoid mapping issues.

4. Importing Excel sheets as SharePoint lists should be avoided. SharePoint automatically assigns different internal names to columns (e.g., field_1, LinkTitle). Additionally, column headers containing special characters lead to altered internal names (e.g., Display Name: Employee Code → Internal Name: Employee_x0020_Code).

5. The default Title column in SharePoint should not be deleted. It can be renamed to align with the corresponding database field name.

6. SharePoint Data Types: Number fields automatically convert 1 → 1.0.
		           DateTime fields must use the ISO 8601 UTC format 2025-08-06 15:59:45 → 2025-08-06T22:59:45Z.
To prevent unwanted updates caused by datatype conversions, use Single line of text for such fields to store values exactly as received.

7. Microsoft Graph API Pagination: The Microsoft Graph API retrieves data in batches typically 20 batches per run, with 10 rows per batch (i.e., 200 rows per request cycle). To handle lists with more than 200 records, the @odata.nextLink property should be used to fetch subsequent batches until all data is retrieved.
