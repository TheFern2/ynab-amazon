import requests
import json

class YNAB:
    BASE_URL = "https://api.ynab.com/v1"
    
    def __init__(self, bearer_token):
        self.bearer_token = bearer_token
        self.headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json'
        }
    
    def get_transactions(self, budget_id, since_date=None):
        """Get transactions for a specific budget"""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        params = {}
        if since_date:
            params['since_date'] = since_date
        
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()
    
    def create_transactions(self, budget_id, payload):
        """Update transactions for a specific budget"""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        response = requests.post(url, headers=self.headers, data=json.dumps(payload))
        return response.json()

    def patch_transactions(self, budget_id, payload):
        """Update transactions for a specific budget"""
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        response = requests.patch(url, headers=self.headers, data=json.dumps(payload))
        return response.status_code, response.json()
