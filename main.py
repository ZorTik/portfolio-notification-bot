import os

import discord
import requests
from quart import Quart, request

import handlers
from log import logger

required_env = [
    "DISCORD_TOKEN", "VERIFY_ENDPOINT", "NOTIFICATIONS_USER_ID", "RECEIVER_PORTFOLIO_ID"
]
notification_handlers = {
    "chat.messages.created": handlers.handle_messages_created
}
client: discord.Client
api: Quart = Quart(__name__)


async def validate_webhook_request(req):
    if req.method != "POST":
        return False

    body = await req.get_json(force=True)
    return all(map(lambda key: body.get(key) is not None, ["type", "verify_token"]))


@api.route("/webhook", methods=["POST"])
async def webhook_route():
    if await validate_webhook_request(request):
        body = await request.get_json(force=True)
        verify_token = body["verify_token"]
        r = requests.get(f"{os.environ['VERIFY_ENDPOINT']}?code={verify_token}")
        r = r.json()

        if not r["valid"]:
            logger.error(f"Received request was not valid in portfolio")
            return "Unauthorized", 401

        handler = notification_handlers.get(body["type"])
        if handler is not None:
            user_id = int(os.environ["NOTIFICATIONS_USER_ID"])
            notifications_user = client.get_user(user_id)
            if notifications_user is None:
                notifications_user = await client.fetch_user(user_id)

            await handler(notifications_user, body)
            return "Accepted", 200
        else:
            return f"Type {body['type']} does not have handler in the bot", 400

    else:
        logger.error(f"Received invalid request! ({request.method} {request.path})")

    return "Invalid request", 400


def run():
    global client

    client = discord.Client(intents=discord.Intents.all())

    @client.event
    async def on_ready():
        notification_user_id = int(os.environ["NOTIFICATIONS_USER_ID"])
        if await client.fetch_user(notification_user_id) is None:
            logger.error(f"User with ID {notification_user_id} not fetched!")
            exit(1)

        logger.info(f"Bot is running as {client.user.name}")
        client.loop.create_task(api.run_task(host="0.0.0.0", port=port))

    logger.info("Starting client")
    port = int(os.environ.get("API_PORT") or "1234")
    client.run(token=os.environ['DISCORD_TOKEN'])


if __name__ == '__main__':
    m_env = list(filter(lambda req_env: os.environ.get(req_env) is None, required_env))
    if len(m_env) > 0:
        logger.error(f"Missing environment variables: {', '.join(m_env)}")
        exit(1)

    run()
