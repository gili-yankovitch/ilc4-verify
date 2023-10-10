#!/usr/bin/python3

from flask import Flask, request
from bs4 import BeautifulSoup
import regex as re
import requests
import time

from linkedin_scraper import Person, actions
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.firefox.options import Options

import json
import creds

app = Flask(__name__)

user = re.compile("linkedin.com/in/(?P<username>[^\?/]+)")
def linkedin_profile(url):
    m = user.search(url)

    if m is None:
        return None

    resp = requests.get("https://api.scrapingdog.com/linkedin/?api_key={TOKEN}&type=profile&linkId={USER}".format(TOKEN = creds.SCRAPINGDOG_API_KEY,USER = m.group("username")))

    data = resp.json()

    if len(data) == 0:
        return {}

    print(data)

    data = data[0]

    return { "name": data["fullName"], "experiences": data["experience"], "connections": data["connections"] }

@app.route('/person', methods = ["POST"])
def person():
    print("Checking person...")
    content_type = request.headers.get('Content-Type')
    print(content_type)
    if (content_type == "application/json"):
        data = json.loads(request.data)

        print("LinkedIn profile:", data["linkedin"])

        print("Requesting user page...")
        return linkedin_profile(data["linkedin"])

    return {}

if __name__ == '__main__':
    app.run()
