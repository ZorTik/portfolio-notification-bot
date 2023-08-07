import os
from typing import Dict

import discord
import util


class Payload:
    participants: any
    messages: any


class Notification:
    """ Type checking """
    type: str
    payload: Payload


rate_limits: Dict[str, int]


async def handle_messages_created(notifications_user: discord.User, notification: Notification):
    if os.environ["RECEIVER_PORTFOLIO_ID"] not in notification.payload.participants:
        """ I notify only about chats user is part of """
        return

    notify_messages = list(
        filter(lambda msg: msg.user_id != os.environ["RECEIVER_PORTFOLIO_ID"], notification.payload.messages))

    limit_rate = os.environ.get("LIMIT_RATE") or str(60000 * 60)
    limit_rate = int(limit_rate)
    if notification.type not in rate_limits or rate_limits[notification.type] < util.current_time_millis() - limit_rate:
        rate_limits[notification.type] = util.current_time_millis()
        embed = discord.Embed(
            colour=discord.Colour.green(),
            title="New message(s) in portfolio",
            description="There are new messages in chats you are part of",
        )
        for notify_message in notify_messages:
            embed.add_field(name=notify_message.user_id, value=notify_message.content, inline=False)
            """ TODO: Change name to username, not user_id """

        await notifications_user.send(embed=embed)
