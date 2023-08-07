from concurrent.futures import ProcessPoolExecutor

import asyncio
import discord
import requests
import os

from flask import Flask, request

import handlers

required_env = [
    "DISCORD_TOKEN", "VERIFY_ENDPOINT", "NOTIFICATIONS_USER_ID", "RECEIVER_PORTFOLIO_ID"
]
notification_handlers = {
    """ The notification handlers by event type """
    "CHAT_MESSAGES_CREATED": handlers.handle_messages_created
}
client = discord.Client(intents=discord.Intents.all())


def validate_webhook_request(req):
    if req.method != "POST":
        return False
    body = req.get_json(force=True)
    return all(map(lambda key: body[key] is not None, ["type", "verify_token"]))


def run_api():
    api = Flask(__name__)

    @api.route("/webhook", methods=["POST"])
    async def webhook_route():
        if request.method == "POST" and validate_webhook_request(request):
            body = request.get_json(force=True)
            verify_token = body.verify_token
            r = requests.get(f"{os.environ['VERIFY_ENDPOINT']}?code={verify_token}")
            r = r.json()
            if r.valid:
                user_id = int(os.environ["NOTIFICATIONS_USER_ID"])
                user = await client.fetch_user(user_id)
                if r.type in notification_handlers.keys():
                    await notification_handlers[r.type](user, r)
        else:
            return "Invalid request", 400

    port = int(os.environ.get("API_PORT") or "1234")
    print("Starting API...")
    api.run(host="0.0.0.0", port=port)


def run_bot():
    @client.event
    async def on_ready():
        print(f"Bot is running as {client.user.name}")

    print("Starting bot...")

    client.run(token=os.environ['DISCORD_TOKEN'])


if __name__ == '__main__':
    m_env = list(filter(lambda req_env: os.environ.get(req_env) is None, required_env))
    if len(m_env) > 0:
        print(f"Missing environment variables: {', '.join(m_env)}")
        exit(1)

    executor = ProcessPoolExecutor(2)
    loop = asyncio.new_event_loop()
    loop.run_in_executor(executor, run_bot)
    loop.run_in_executor(executor, run_api)

    loop.run_forever()
