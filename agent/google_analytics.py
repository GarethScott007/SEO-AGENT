# Already in main; full GSC impl:
from googleapiclient.discovery import build

def get_gsc_queries(site_url, keyfile):
    service = build('searchconsole', 'v1', developerKey=keyfile)  # Use service account
    request = {
        'startDate': (datetime.now() - timedelta(7)).strftime('%Y-%m-%d'),
        'endDate': datetime.now().strftime('%Y-%m-%d'),
        'dimensions': ['query', 'page'],
        'rowLimit': 10
    }
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    return [row['keys'][0] for row in response.get('rows', []) if row['clicks'] > 0]
