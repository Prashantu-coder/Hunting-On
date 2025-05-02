from google.oauth2 import service_account
import googleapiclient.discovery

# Manually load credentials
creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
service = googleapiclient.discovery.build("sheets", "v4", credentials=creds)

# Try accessing the spreadsheet (replace with your actual Sheet ID)
sheet_id = "1_pmG2oMSEk8VciNm2uqcshyvPPZBbjf-oKV59chgT1w"
sheet = service.spreadsheets().values().get(spreadsheetId=sheet_id, range="Daily Price").execute()
print(sheet)
