tenant_id = "842e4e0e-1c63-4147-b5bc-2b8baed2f998"
client_id = "c5507ed5-6034-4b81-98e5-cd6a417ba598"
client_secret = "o7v8Q~MLy0v0qIS05M.oDEbDmO3tNx789cRtpcCo"

# SharePoint Path connection
site_hostname = "nicesoftwaresolutions1.sharepoint.com"
site_path = "/" 
list_name="NestEmployeeList"
# list_name="TestEmployeeList"

# Database Connection
host="localhost"
user="root"
password="training@123"
database="northwind"

# Graph API connection
graph_api="https://graph.microsoft.com/v1.0/sites/"

# Query/view to fetch data 
query = "select * from employees WHERE employeestatus = 'Active' and FirstName not like '%Con%'"
