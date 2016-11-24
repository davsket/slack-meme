from flask import Flask, request
from models import Memegen, Slack, parse_text_into_params, image_exists, get_shortcut, set_shortcut

app = Flask(__name__)
app.config['DEBUG'] = True


@app.route("/")
def meme():
    if not request.args:
        message = """
        Welcome to Slack Meme!
        Check me out on <a href="https://github.com/nicolewhite/slack-meme">GitHub</a>.
        """

        return message

    memegen = Memegen()
    slack = Slack()

    token = request.args["token"]
    text = request.args["text"]
    channel_id = request.args["channel_id"]
    user_id = request.args["user_id"]

    print "HERE begin"
    print text[:9]
    
    if token != slack.SLASH_COMMAND_TOKEN:
        return "Unauthorized."

    if text.strip() == "":
        return memegen.error()

    if text[:9] == "templates":
        return memegen.list_templates()

    if text[:9] == "search":
        print "HERE on search"
        name = parse_text_into_params(text)[0]
        print name
        return memegen.search_templates(name)

    if text[:9] == "shortcuts":
        return memegen.list_shortcuts()
    
    if text[:6] == "create":
        name, url, description = parse_text_into_params(text)
        if name and url:
            set_shortcut(name, url, description)
            return "Success! Now you can use it with: `/meme %s;<top>;<bottom>`" % (name)
        else:
            return "You need to pass name and url at least to create a shortcut: `/meme create;<name>;<url>;<description>`"

    template, top, bottom = parse_text_into_params(text)
    templates_not_shortcuts = [t[0] for t in memegen.get_templates() if not t[3]]
    
    if template in templates_not_shortcuts:
        meme_url = memegen.build_url(template, top, bottom)
    elif get_shortcut(template):
        meme_url = memegen.build_url("custom", top, bottom, get_shortcut(template))
        print meme_url
    elif image_exists(template):
        print template
        meme_url = memegen.build_url("custom", top, bottom, template)
        print meme_url
    else:
        return memegen.error()

    payload = {"channel": channel_id}
    user = slack.find_user_info(user_id)
    payload.update(user)

    attachments = [{"image_url": meme_url, "fallback": "Oops. Something went wrong."}]
    payload.update({"attachments": attachments})

    try:
        slack.post_meme_to_webhook(payload)
    except Exception as e:
        return e

    return "Success!", 200
