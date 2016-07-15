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
    
    if token != slack.SLASH_COMMAND_TOKEN:
        return "Unauthorized."

    if text.strip() == "":
        return memegen.error()

    if text[:9] == "templates":
        return memegen.list_templates()

    if text[:9] == "shortcuts":
        shortcuts = [t for t in memegen.get_templates() if t[3]]
        return shortcuts
    
    if text[:6] == "create":
        name, url, description = parse_text_into_params(text)
        set_shortcut(name, url, description)
        return "Presto!"

    template, top, bottom = parse_text_into_params(text)

    valid_templates = [x[0] for x in memegen.get_templates()]
    templates_not_shortcuts = [t for t in valid_templates if not t[3]]
    if template in templates_not_shortcuts:
        meme_url = memegen.build_url(template, top, bottom)
    elif get_shortcut(template):
        meme_url = memegen.build_url("custom", top, bottom, get_shortcut(template))
        print meme_url
    elif image_exists(template):
        meme_url = memegen.build_url("custom", top, bottom, template)
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
