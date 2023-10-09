#!/usr/bin/python3

from flask import Flask, request
from linkedin_scraper import Person, actions
from selenium import webdriver
import json
import creds

app = Flask(__name__)

@app.route('/person', methods = ["POST"])
def person():
    print("Checking person...")
    content_type = request.headers.get('Content-Type')
    print(content_type)
    if (content_type == "application/json"):
        data = json.loads(request.data)

        print("LinkedIn profile:", data["linkedin"])

        print("Logging in to LinkedIn...")
        driver = init_selenium()
        actions.login(driver, creds.LINKEDIN_USER, creds.LINKEDIN_PW)
        print("Requesting user page...")
        person = Person(data["linkedin"], driver = driver)
        print("Done")
    return { "name": person.name, "experiences": [ { "name": e.institution_name, "duration": e.duration } for e in person.experiences ] }

def init_selenium():
    op = webdriver.ChromeOptions()
    op.add_argument('headless')
    #op.add_argument('window-size=1024,768')
    #op.add_argument('--no-sandbox')
    return webdriver.Chrome(options=op)

if __name__ == '__main__':
    print("Initializing selenium...")
    print ("Logged in.")
    app.run()
