import os
import re
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["*"])  # Allow all for Render

class PhoneLookup:
    def __init__(self):
        self.numverify_key = os.getenv('NUMVERIFY_KEY')
        self.ipquality_key = os.getenv('IPQUALITY_KEY')
    
    def parse_number(self, number):
        """Parse and validate phone number"""
        try:
            parsed = phonenumbers.parse(number)
            if phonenumbers.is_valid_number(parsed):
                return {
                    'valid': True,
                    'formatted': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                    'country': geocoder.description_for_number(parsed, 'en'),
                    'carrier': carrier.name_for_number(parsed, 'en') or 'Unknown',
                    'timezone': timezone.time_zones_for_number(parsed) or [],
                    'national_format': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
                }
            return {'valid': False, 'error': 'Invalid number format'}
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def enrich_numverify(self, number):
        """Numverify API lookup"""
        if not self.numverify_key:
            return {}
        
        try:
            params = {
                'access_key': self.numverify_key,
                'number': number,
                'format': 1
            }
            resp = requests.get('http://apilayer.net/api/validate', params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'line_type': data.get('line_type', 'Unknown'),
                    'carrier': data.get('carrier', 'Unknown'),
                    'location': data.get('location', 'Unknown'),
                    'type': data.get('type', 'Unknown')
                }
        except:
            pass
        return {}
    
    def enrich_ipquality(self, number):
        """IPQualityScore lookup"""
        if not self.ipquality_key:
            return {}
        
        try:
            url = f"https://ipqualityscore.com/api/json/phone/{self.ipquality_key}/{number}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'risk_score': data.get('risk_score', 0),
                    'recent_abuse': data.get('recent_abuse', False),
                    'carrier': data.get('carrier', 'Unknown'),
                    'line_type': data.get('line_type', 'Unknown')
                }
        except:
            pass
        return {}
    
    def social_scan(self, number):
        """Basic social media scan"""
        patterns = {
            'facebook': f"https://www.facebook.com/{number.replace('+', '').replace(' ', '')}",
            'instagram': f"https://www.instagram.com/{number.replace('+', '').replace(' ', '')}/",
            'twitter': f"https://twitter.com/{number.replace('+', '').replace(' ', '')}"
        }
        
        results = {}
        for platform, url in patterns.items():
            results[platform] = {'url': url, 'status': 'check_manually'}
        return results
    
    def calculate_risk(self, phone_data, enriched):
        """Risk assessment"""
        score = 0
        reasons = []
        
        # VOIP check
        if 'voip' in (phone_data.get('carrier', '').lower()):
            score += 2
            reasons.append('VOIP carrier detected')
        
        # IPQuality high risk
        if enriched.get('ipquality', {}).get('risk_score', 0) > 75:
            score += 3
            reasons.append('High fraud risk score')
        
        risk_level = 'LOW' if score < 2 else 'MEDIUM' if score < 4 else 'HIGH'
        
        return {
            'score': score,
            'level': risk_level,
            'reasons': reasons
        }
    
    def lookup(self, number):
        """Complete phone lookup"""
        # Clean number
        clean_number = re.sub(r'[^\d+]', '', number)
        
        # Parse
        phone_data = self.parse_number(clean_number)
        if not phone_data.get('valid'):
            return phone_data
        
        # Enrich
        numverify = self.enrich_numverify(clean_number)
        ipquality = self.enrich_ipquality(clean_number)
        social = self.social_scan(clean_number)
        
        risk = self.calculate_risk(phone_data, {'numverify': numverify, 'ipquality': ipquality})
        
        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'phone': phone_data,
            'enrichment': {
                'numverify': numverify,
                'ipquality': ipquality
            },
            'social_profiles': social,
            'risk_assessment': risk
        }

service = PhoneLookup()

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'PhoneTrace API'})

@app.route('/api/lookup', methods=['POST'])
def lookup():
    try:
        data = request.get_json()
        number = data.get('number')
        
        if not number:
            return jsonify({'error': 'Phone number required'}), 400
        
        result = service.lookup(number)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'PhoneTrace API - POST to /api/lookup'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
