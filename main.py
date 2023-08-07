from concurrent.futures import ProcessPoolExecutor

import asyncio
import discord
import requests
import os
import waitress

from flask import Flask, request
from log import logger

import handlers

required_env = [
    "DISCORD_TOKEN", "VERIFY_ENDPOINT", "NOTIFICATIONS_USER_ID", "RECEIVER_PORTFOLIO_ID"
]
notification_handlers = {
    "chat.messages.created": handlers.handle_messages_created
}
client = discord.Client(intents=discord.Intents.all())
notification_user: discord.User


def validate_webhook_request(req):
    if req.method != "POST":
        return False

    body = req.get_json(force=True)
    return all(map(lambda key: body.get(key) is not None, ["type", "verify_token"]))


def run_api():
    api = Flask(__name__)

    @api.route("/webhook", methods=["POST"])
    async def webhook_route():
        if validate_webhook_request(request):
            body = request.get_json(force=True)
            verify_token = body["verify_token"]
            r = requests.get(f"{os.environ['VERIFY_ENDPOINT']}?code={verify_token}")
            r = r.json()

            if not r["valid"]:
                logger.error(f"Received request was not valid in portfolio")
                return "Unauthorized", 401

            handler = notification_handlers.get(body["type"])
            if handler is not None:
                global notification_user
                await handler(notification_user, body)
                return "Accepted", 200
            else:
                return f"Type {body['type']} does not have handler in the bot", 400

        else:
            logger.error(f"Received invalid request! ({request.method} {request.path})")

        return "Invalid request", 400

    port = int(os.environ.get("API_PORT") or "1234")
    logger.info(f"Starting API on {port}")
    waitress.serve(api, host="0.0.0.0", port=port)


def run_bot():
    @client.event
    async def on_ready():
        global notification_user
        notification_user_id = int(os.environ["NOTIFICATIONS_USER_ID"])
        notification_user = await client.fetch_user(notification_user_id)
        if notification_user is None:
            logger.error(f"User with ID {notification_user_id} not fetched!")
            exit(1)

        logger.info(f"Bot is running as {client.user.name}")

    logger.info("Starting bot...")

    client.run(token=os.environ['DISCORD_TOKEN'])


if __name__ == '__main__':
    m_env = list(filter(lambda req_env: os.environ.get(req_env) is None, required_env))
    if len(m_env) > 0:
        logger.error(f"Missing environment variables: {', '.join(m_env)}")
        exit(1)

    executor = ProcessPoolExecutor(2)
    loop = asyncio.new_event_loop()
    loop.run_in_executor(executor, run_bot)
    loop.run_in_executor(executor, run_api)

    loop.run_forever()
