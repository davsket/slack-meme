import json
import os
from urllib import unquote_plus, quote
import requests
from pymongo import MongoClient

MONGODB_USER = os.environ.get("MONGODB_USER")
MONGODB_PASS = os.environ.get("MONGODB_PASS")
MONGODB_URI  = "mongodb://%s:%s@ds035664.mlab.com:35664/davsket-shared" % (MONGODB_USER, MONGODB_PASS)

db = MongoClient(MONGODB_URI)["davsket-shared"]
memes_collection = db.memes

shorcuts = {
    "chichico": "https://cldup.com/2imzWDHuva.png",
    "fsjal": "http://i.imgur.com/meePc.jpg"
}


def get_shortcut(name):
    memes = memes_collection.find({"name": name})
    for meme in memes:
        return meme["url"]
    return None

def set_shortcut(name, url, description):
    memes = memes_collection.find({"name": name})
    for meme in memes:
        meme.update({
            "url": url,
            "description": description
        })
        return meme
    meme = memes_collection.insert_one({
        "name": name,
        "url": url,
        "description": description
    })
    return meme

class Memegen:

    def __init__(self):
        self.BASE_URL = "http://memegen.link"

    def get_templates(self):
        response = requests.get(self.BASE_URL + "/templates").json()

        data = []

        for key, value in response.items():
            name = value.replace(self.BASE_URL + "/templates/", "")
            sample = value.replace("/templates", "") + "/your-text/goes-here.jpg"
            description = key
            is_shortcut = False
            data.append((name, description, sample, is_shortcut))
        for shortcut in memes_collection.find():
            is_shortcut = True
            name = "shortcut: " + shortcut["name"]
            sample = shortcut["url"]
            description = shortcut["description"] if "description" in shortcut else "Shortcut template"
            data.append((name, description, sample, is_shortcut))

        data.sort(key=lambda tup: tup[0])
        return data

    def list_templates(self):
        templates = self.get_templates()

        help = ""

        for template in templates:
            help += "`{0}` <{2}|{1}> {3}\n".format(template[0], template[1], template[2], "[shortcut]" if template[3] else "" )

        return help

    def list_shortcuts(self):
        templates = [t for t in self.get_templates() if t[3]]

        help = ""

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
        return """
        **Commands**
        `/meme templates` to see valid templates or provide your own as a URL.
        `/meme shortcuts` to see only the available shortcuts.
        `/meme <name>;<top-text>;<bottom-text>` to use that meme
        `/meme create;<name>;<url>;<optional-description>`    to create new memes
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
        params = [x.replace(" ", "_") for x in params]
        params = [quote(x.encode("utf8")) for x in params]

        params += [None] * (3 - len(params))
        return params[0], params[1], params[2]
    else:
        params = [x.strip() for x in params]
        params = [x.replace(" ", "_") for x in params]
        params = [quote(x.encode("utf8")) for x in params]

        params += [None] * (2 - len(params))
        return template, params[0], params[1]
