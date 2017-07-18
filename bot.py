#!/usr/bin/env python3

import logging
import argparse
import json
import threading
import requests
import sseclient
from telegram import Bot
from telegram.ext import Updater, CommandHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

updater = None
chats = set()
chats_lock = threading.Lock()


def sender(url, template):
    resp = requests.get(url, stream=True)
    client = sseclient.SSEClient(resp)
    for event in client.events():
        event = json.loads(event.data)
        with chats_lock:
            ids = set(chats)
        for chat_id in ids:
            updater.bot.send_message(chat_id, template.format(e=event))


def start(bot, update):
    update.message.reply_text(
        'This bot sends you an SSE (server-sent events) stream.')
    chats.add(update.message.chat_id)


def stop(bot, update):
    update.message.reply_text('Stopping stream.')
    chats.remove(updater.bot.chat_id)


def help(bot, update):
    update.message.reply_text(
        'Type /start to start and /stop to stop.')


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def main():
    global args, updater

    parser = argparse.ArgumentParser(description='SSE Telegram Bot')

    parser.add_argument(
        '--token-file', '-t', default='token.txt',
        help='The file from which the Telegram bot token is read. '
        'Defaults to token.txt in the current directory.')
    parser.add_argument(
        '--template-file', '-T', default='template.txt',
        help='The file from which the message template is read. '
        'Defaults to template.txt in the current directory.')
    parser.add_argument(
        'url', metavar='URL',
        help='The URL from which to read the SSE stream.')

    args = parser.parse_args()

    try:
        with open(args.token_file) as f:
            token = f.read().strip()
    except FileNotFoundError:
        logger.error('Token file not found: {}'.format(args.token_file))
        exit(1)
    except PermisionError:
        logger.error('Permission denied reading token file: {}'
                     .format(args.token_file))
        exit(1)

    try:
        with open(args.template_file) as f:
            template = f.read().strip()
    except FileNotFoundError:
        logger.error('Template file not found: {}'.format(args.template_file))
        exit(1)
    except PermisionError:
        logger.error('Permission denied reading template file: {}'
                     .format(args.template_file))
        exit(1)

    # Create an updater
    updater = Updater(token=token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('stop', stop))
    dp.add_handler(CommandHandler('help', help))

    # log all errors
    dp.add_error_handler(error)

    # launch sender thread
    sender_thread = threading.Thread(target=sender, args=(args.url, template))
    sender_thread.start()

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    try:
        logger.info('Bot started.')
        updater.idle()
        logger.info('Bot stopped.')
    finally:
        print('Stopping sender thread.')
        sender_thread.terminate()


if __name__ == '__main__':
    main()
