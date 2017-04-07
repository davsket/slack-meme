import json
import os
import re
from urllib import unquote_plus, quote
import requests
from pymongo import MongoClient

MONGODB_URI  = os.environ.get("MONGODB_URI")
DB_NAME  = os.environ.get("DB_NAME")
DB_COLLECTION  = os.environ.get("DB_COLLECTION")

db = MongoClient(MONGODB_URI)[DB_NAME]
memes_collection = db[DB_COLLECTION]

def get_shortcut(name):
    memes = memes_collection.find({"name": name})
    for meme in memes:
        return meme["url"]
    return None

def set_shortcut(name, url, description):
    memes = memes_collection.find({"name": name})
    if memes.count() > 0:
        memes_collection.update_one(
        { "name": name },
        {
            "$set": {
                "url": url,
                "description": description
            }
        })
    else:
        memes_collection.insert_one({
            "name": name,
            "url": url,
            "description": description
        })

class Memegen:

    def __init__(self):
        self.BASE_URL = "https://memegen.link"

    def get_templates(self):
        response = requests.get(self.BASE_URL + "/templates").json()

        data = []

        for key, value in response.items():
            name = value.replace(self.BASE_URL + "/api/templates/", "").encode('ascii', 'ignore')
            sample = value.replace("/api/templates", "") + "/your-text/goes-here.jpg"
            description = key.encode('ascii', 'ignore')
            is_shortcut = False
            data.append((name, description, sample, is_shortcut))

        for shortcut in memes_collection.find():
            is_shortcut = True
            name = shortcut["name"]
            sample = shortcut["url"]
            description = shortcut["description"] if ("description" in shortcut) and shortcut["description"] else "Shortcut template"
            data.append((name, description, sample, is_shortcut))

        data.sort(key=lambda tup: tup[0])
        return data

    def list_templates(self):
        templates = self.get_templates()

        help = "*Available Templates & Shortcuts*\n"

        for template in templates:
            help += "`{0}` <{2}|{1}> {3}\n".format(template[0], template[1], template[2], "[shortcut]" if template[3] else "" )

        return help

    def search_templates(self, search):
        templates = self.get_templates()

        results = ""
        count = 0

        for template in templates:
            name, description, sample, is_shortcut = template
            if re.search(search, name, re.IGNORECASE) or re.search(search, description, re.IGNORECASE):
                results += "`{0}` <{2}|{1}> {3}\n".format(name, description, sample, "[shortcut]" if is_shortcut else "" )
                count += 1

        if count == 0:
            return "*No Matches For: `%s`* :julians:\n" % search

        help = "*%d Match%s For: `%s`*\n" % (count, "es" if count > 1 else "", search)

        return help + results

    def list_shortcuts(self):
        templates = [t for t in self.get_templates() if t[3]]

        help = "*Available Shortcuts*\n"

        for template in templates:
            help += "`{0}` <{2}|{1}> {3}\n".format(template[0], template[1], template[2], "[shortcut]" if template[3] else "" )

        return help

    def build_url(self, template, top, bottom, alt=None):
        path = "/{0}/{1}/{2}.jpg".format(template, top or '_', bottom or '_')

        if alt:
            path += "?alt={}".format(alt)

        url = self.BASE_URL + path

        return url

    def error(self):
        return """ *Monoku's Slack Memmes* :monoku:
Available commands:
>>>
*1. To List Templates:* `/meme templates` to list all the valid templates.
*2. To List Shortcuts:* `/meme shortcuts` to list only the customized ones.
*3. To Generate a Meme:* `/meme <name>;<top-text>;<bottom-text>`
     Example: `/meme aag;;aliens` will use the akward aliens guy meme with "aliens" text on the bottom
*4. To Use an Image as a Meme:* `/meme <image-url>;<top-text>;<bottom-text>` to use an image as a meme :snoop_dancing:
     Example: `/meme https://cldup.com/keFjCIj7li.png;;oie` wi use that image and place the "oie" at the bottom
*5. To Create a new Shorcut:* `/meme create;<name>;<url>;<optional-description>` shortcuts are memes that you can reuse with the name :magic:
*6. To Search:* `/meme search;<text>` to search for memes with that text on name or description :fiesta_parrot:
   `/meme search;alone` will show all the memes which name or description include alone
        """

def image_exists(path):
    if path.split("://")[0] not in ["http", "https"]:
        return False

    r = requests.head(path)
    return r.status_code == requests.codes.ok


class Slack:

    def __init__(self):
        self.BASE_URL = "https://slack.com/api"
        self.API_TOKEN = os.environ.get("SLACK_API_TOKEN")
        self.WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL").strip()
        self.SLASH_COMMAND_TOKEN = os.environ.get("SLACK_SLASH_COMMAND_TOKEN")

    def find_user_info(self, user_id):
        url = self.BASE_URL + "/users.info?token={0}&user={1}".format(self.API_TOKEN, user_id)
        response = requests.get(url)

        user = response.json()["user"]
        username = user["name"]
        icon_url = user["profile"]["image_48"]

        return {"username": username, "icon_url": icon_url}

    def post_meme_to_webhook(self, payload):
        requests.post(self.WEBHOOK_URL, data=json.dumps(payload))


def parse_text_into_params(text):
    text = unquote_plus(text).strip()
    text = text[:-1] if text[-1] == ";" else text

    params = text.split(";")

    template = params[0].strip()
    del params[0]

    if template == "create":
        params = [x.strip() for x in params]
        if params[0]:
            params[0] = quote(params[0].replace(" ", "-"))
        params = [x.encode("utf8") for x in params]
        if params[1]:
            params[1] = unquote_plus(params[1])
        params += [None] * (3 - len(params))
        return params[0], params[1], params[2]
    else:
        params = [x.strip() for x in params]
        params = [x.replace(" ", "-") for x in params]
        params = [quote(x.encode("utf8")) for x in params]

        params += [None] * (2 - len(params))
        return template, params[0], params[1]
