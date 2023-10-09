#!/usr/bin/python3
import asyncio
# -*- coding: utf-8 -*-
import os
import discord
import subprocess
import shlex
import regex
import json
import threading
import urllib.parse
import time
import requests
import creds
from telegramBot import TelegramBot, VerifierCallback

try:
   import cPickle as pickle
except:
   import pickle

ADMIN_CHANNEL_ID = 1142400024374935634
ADMIN_CHANNEL = None

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
client = discord.Client(intents = intents)

CHECK_ORD_VALUE = 9989

pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')

CACHE_FILE = "cache.pkl"
cache = {}

def cache_flush():
    global cache

    # Every minute, flush the cache
    print("Cache flush thread started...")
    while True:
        with open(CACHE_FILE, "wb") as f:
            f.write(pickle.dumps(cache))

        time.sleep(5)

def normalize(s):
    return urllib.parse.unquote(s.replace("\\n", "").replace("\\x", "%")).replace("\\\\\"", "\\\"").replace("\\","")

@client.event
async def on_ready():
    global ADMIN_CHANNEL
    ADMIN_CHANNEL = client.get_channel(ADMIN_CHANNEL_ID)
    print(f"{client.user} has connected")

async def verify_linkedin(user_id):
    resp = requests.post("http://127.0.0.1:5000/person", headers = {"Content-Type": "application/json"}, data = json.dumps({"linkedin": cache[user_id]["linkedin"]}))
    data = resp.json()
    print(data)

    # Add name to cache
    cache[user_id]["name"] = data["name"]

    if len(data["experiences"]) >= 2:
        await ADMIN_CHANNEL.send("Request for approval:\n" +
            "\tName: {NAME}\n".format(NAME = data["name"]) +
            "\tPhone number: {PHONE}\n".format(PHONE = cache[user_id]["phone"]) +
            "\tLinkedIn profile: {URL}\n".format(URL = cache[user_id]["linkedin"]) +
            "\t\tNumber of jobs: {NUM_JOBS}".format(NUM_JOBS = len(data["experiences"])))

@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return

    user = client.get_user(int(payload.user_id))
    channel = await client.create_dm(user)

    if payload.user_id not in cache:
        print("Invalid response from user", payload.user_id)
        await channel.send("Invalid response. Please state your details to begin verification")

        return

    if ord(payload.emoji.name) == CHECK_ORD_VALUE:
        await channel.send("Sending you a Telegram message with CAPTCHA to: {PHONE_NUMBER}. Please reply to me with the response.".format(PHONE_NUMBER = cache[payload.user_id]["phone"]))

        print("Probing LinkedIn for more details...")
        #threading.Thread(target = verify_linkedin, args = (payload.user_id,)).start()
        await verify_linkedin(payload.user_id)
    else:
        del cache[payload.user_id]
        await channel.send("I am sorry. I've probably misunderstood. Please resend personal information data.")

async def run_llama(data):
    # Look inside the message for:
    # 1. LinkedIn link
    # 2. Phone number
    # 3. Name
    # Take the message, send to the model to extract details
    cmd = shlex.split(f"./llamacpp -m models/vicuna-7b-1.1.ggmlv3.q4_0.bin -p \"Respond with a JSON only. The data below contains a full name, a LinkedIn URL and a phone number. " +
        "Parse the data below and return a JSON with the following keys: 'name', 'linkedin', 'phone':\n" +
        data + "\n" +
        "JSON:\"")

    print("Running:", cmd)
    p = subprocess.Popen(cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE)

    try:
        out, err = p.communicate()

        print("Output:", str(out))

        m = pattern.findall(str(out))
    except Exception as e:
        print(e)
        m = []

    return m

phone = regex.compile("(?:972|0?)5[0-9\-]+")
url = regex.compile(r'\b(?:https?):[\w/#~:.?+=&%@!\-.:?\\-]+?(?=[.:?\-]*(?:[^\w/#~:.?+=&%@!\-.:?\-]|$))')
def extract_details(data):
    pn = phone.findall(data)

    if len(pn) == 0:
        return []

    linkedin = url.findall(data)

    if len(linkedin) == 0:
        return []

    if not pn[0].startswith("05"):
        pn = "0" + pn[0]
    else:
        pn = pn[0]

    return [{"phone": pn, "linkedin": linkedin[0], "msg": data}]

@client.event
async def on_message(message):
    global cache

    # Ignore self-sent messages
    if message.author.id == client.user.id:
        return

    # Phase #1 - Receive user information
    if message.author.id not in cache:
        await message.channel.send("Hey there! Thank you for volunteering. I am currently processing your data and will be back with you shortly.")

        #m = await run_llama(message.content.replace(" ", "\n"))
        m = extract_details(message.content.replace(" ", "\n"))

        if (len(m) == 0):
            await message.channel.send("Sorry. Could not parse your request. Please send us your name, phone number and LinkedIn link again in a separated manner")
            return

        #print(normalize(m[0]))
        #data = json.loads(normalize(m[0]))
        data = m[0]

        print(m)

        # Cache the data
        cache[message.author.id] = data

        msg = await message.channel.send("Are these parameters correct?\n" +
            f"Phone number: {data['phone']}\n"
            f"LinkedIn Profile: {data['linkedin']}")

        await msg.add_reaction("\U00002705")
        await msg.add_reaction("\U0000274C")
    else:
        # Phase #3 - Get the CAPTCHA response
        await message.channel.send("Waiting for CAPTHA response...")

def start_telegram_bot():
    EyalVC = VerifierCallback("972542864041", lambda verified: print("Verified"))
    TelegramBot.initialize()
    TelegramBot.register_cb(EyalVC)
    asyncio.run(TelegramBot.start())

def main():
    global cache
    # Reload the cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            cache = pickle.loads(f.read())

    print(cache)

    t = threading.Thread(target = cache_flush)
    t.start()
    client.run(creds.TOKEN)
    # Must be async
    start_telegram_bot()

if __name__ == "__main__":
    main()
