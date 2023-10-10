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

ADMIN_CHANNEL_ID = 1161267132110221382
ADMIN_CHANNEL = None

intents = discord.Intents.default()
intents.reactions = True
intents.members = True
intents.guilds = True
client = discord.Client(intents=intents)

CHECK_ORD_VALUE = 9989
DEL_ORD_VALUE = 10060
EYES_ORD_VALUE = 128064

pattern = regex.compile(r'\{(?:[^{}]|(?R))*\}')

CACHE_FILE = "cache.pkl"
cache = {}

TELEGRAM_LINK = "https://t.me/ILC4Bot"

def cache_flush():
    global cache

    # Every minute, flush the cache
    print("Cache flush thread started...")
    while True:
        with open(CACHE_FILE, "wb") as f:
            f.write(pickle.dumps(cache))

        time.sleep(5)


def normalize(s):
    return urllib.parse.unquote(s.replace("\\n", "").replace("\\x", "%")).replace("\\\\\"", "\\\"").replace("\\", "")


@client.event
async def on_ready():
    global ADMIN_CHANNEL
    ADMIN_CHANNEL = client.get_channel(ADMIN_CHANNEL_ID)
    some_chan = client.get_channel(1160618250703474781)
    try:
        await some_chan.send("Bot test message")
    except Exception as e:
        print(e)
    print(f"{client.user} has connected")

@client.event
async def on_raw_reaction_add(payload):
    if payload.user_id == client.user.id:
        return

    if payload.guild_id is not None:
        return

    print("Reaction:", payload)

    user = client.get_user(int(payload.user_id))
    channel = await client.create_dm(user)

    if payload.user_id not in cache:
        print("Invalid response from user", payload.user_id)
        await channel.send("Hey there, please DM me with your personal details including name, phone number and linkedin profile")

        return

    if ord(payload.emoji.name) == CHECK_ORD_VALUE:
        await channel.send(
            f"Please open this link on telegram, and send your contact details: {TELEGRAM_LINK}")
        # Add CB and register phone number
        phone_number = TelegramBot.normalize_phone_number(cache[payload.user_id]["phone"])

        async def onVerified(verified, name):
            if verified:
                # Add to cache
                cache[payload.user_id]["name"] = name

                final = await ADMIN_CHANNEL.send("Request for approval:\n" + \
                                 "\tUsername: {NAME} Id: {ID}\n".format(NAME = client.get_user(payload.user_id).name, ID = 218702832075931648) + \
                                 "\tName: {NAME}\n".format(NAME=cache[payload.user_id]["name"]) + \
                                 "\tPhone number: {PHONE}\n".format(PHONE=cache[payload.user_id]["phone"]) +    \
                                 "\tLinkedIn profile: {URL}\n".format(URL=cache[payload.user_id]["linkedin"]))
                await final.add_reaction("\U0001F440")

                #threading.Thread(target = verify_linkedin, args = (payload.user_id,)).start()
                #await verify_linkedin(payload.user_id)
                await channel.send("Thank you. We have processed your information and will get back to you shortly.")
            else:
                raise "unable to verify"

        TelegramBot.register_cb(VerifierCallback(phone_number, onVerified))
        print(f"Registered callback for {phone_number}")

    elif ord(payload.emoji.name) == DEL_ORD_VALUE:
        if payload.user_id in cache:
            del cache[payload.user_id]
        await channel.send("I am sorry. I've probably misunderstood. Please resend personal information data.")
    elif ord(payload.emoji.name) == EYES_ORD_VALUE:
        if int(payload.channel_id) == ADMIN_CHANNEL_ID:
            msg = await ADMIN_CHANNEL.fetch_message(int(payload.message_id))
            print("Approved message:", msg)

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
    if message.author.id == client.user.id or str(message.channel.type) != "private":
        return

    # Phase #1 - Receive user information
    if message.author.id not in cache:
        await message.channel.send(
            "Hey there! Thank you for volunteering. I am currently processing your data and will be back with you shortly.")

        m = extract_details(message.content.replace(" ", "\n"))

        if (len(m) == 0):
            await message.channel.send(
                "Sorry. Could not parse your request. Please send us your name, phone number and LinkedIn link again in a separated manner")
            return

        data = m[0]

        # Cache the data
        cache[message.author.id] = data

        msg = await message.channel.send("Are these parameters correct?\n" +
                                         f"Phone number: {data['phone']}\n"
                                         f"LinkedIn Profile: {data['linkedin']}")

        await msg.add_reaction("\U00002705")
        await msg.add_reaction("\U0000274C")
    else:
        # Phase #3 - Get the CAPTCHA response
        await message.channel.send("Please verify your phone number via Telegram...")

def start_telegram_bot():
    TelegramBot.initialize()
    asyncio.run(TelegramBot.start())


def main():
    global cache
    # Reload the cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            cache = pickle.loads(f.read())

    print(cache)

    t = threading.Thread(target=cache_flush)
    t.start()

    # Running discord bot on loop
    loop = asyncio.get_event_loop()
    loop.create_task(client.start(creds.TOKEN))

    # Start telegram bot
    start_telegram_bot()


if __name__ == "__main__":
    main()
