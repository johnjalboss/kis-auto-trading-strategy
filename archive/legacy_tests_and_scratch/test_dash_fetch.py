import requests
from bs4 import BeautifulSoup

s = requests.Session()
s.post('http://localhost:8080/login', data={'password': '0201!'})
r = s.get('http://localhost:8080/')

lines = [line.strip() for line in r.text.split('\n') if 'card-value' in line or 'Total Account' in line or 'Available Buying' in line]
for l in lines:
    print("CARD LINE:", l)
