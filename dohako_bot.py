import discord
import datetime
import io
import aiohttp
import asyncio
import os
import json
import re
import Token
# import _pickle as pickle
import pickle

TOKEN = Token.get_token()
print(TOKEN)
client = discord.Client()
stage = 0
channel_with_action = ''
time_to_send = ''
message_event = None
message_to_send_content = ''
channel_to_send = ''
admin_role = ''
main_dict = {}


def save_settings():
    with open(f'settings\\main_settings.json', 'w') as f:
        print(main_dict)
        json.dump(main_dict, f)


def is_admin(guild_id, user_roles):
    for role in user_roles:
        if role.name in main_dict[guild_id]['admins']:
            return True
    else:
        return False


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    if os.path.isdir('settings') is False:
        os.mkdir('settings')
    if os.path.isfile(f'settings\\main_settings.json') is False:
        with open(f'settings\\main_settings.json', 'w') as f:
            json.dump(main_dict, f)
    else:
        with open(f'settings\\main_settings.json', 'r') as f:
            main_dict.clear()
            main_dict.update(json.load(f))


@client.event
async def on_member_join(member):
    for channel in member.guild.channels:
        if str(channel) == "general":
            await channel.send_message(f"""Welcome to the server {member.mention}""")


@client.event
async def on_message(message):
    global stage, time_to_send, channel_to_send, message_event, message_to_send_content, admin_role
    global channel_with_action, main_dict
    current_guild_id = str(message.guild.id)  # переводим инт в стр для совпадения ключей

    if message.author == client.user:
        return

    # for channel in message.guild.text_channels:
    #     print(channel.id)
    # print(type(client.get_channel(737995441081286699)))
    # await message.channel.send(client.get_channel(737995441081286699))
    # print(message.content)
    # await message.channel.send(message.content)
    # await message.channel.send(f'<#{737995441081286699}>') # способ отправлять вложенные гиперссылки

    if current_guild_id not in main_dict.keys():
        main_dict.update({current_guild_id: {'admins': [], 'events': [], 'edits': []}})
    if message.content.startswith('$hello'):
        await message.channel.send('привет')

    if main_dict[current_guild_id]['admins'] == [] or is_admin(current_guild_id, message.author.roles):
        if message.content.startswith('д?помощь'):
            await message.channel.send('`д?админка ИмяРоли` - назначение админской роли для работы с ботом. \n'
                                       '`д?отложка / д?отсроченное_сообщение / д?отсроченное` - '
                                       'создание отложенного сообщения. \n'
                                       '`д?отложка_инфо` - предоставляет информацию по запланированным событиям.\n'
                                       '`д?отложка_правки` - начало исправления события.\n')
            return
        if message.content == 'д?отложка_инфо':
            await show_info(message)
            return
        if message.content == 'д?отложка_правки':
            await edit_existing_event_phase_1(message)
            return
        if main_dict[current_guild_id]['edits']:
            await edit_existing_event_phase_2(message)
            return
        if message.content.startswith('д?админка'):
            await set_admin_role(message)
            return
        if message.content.startswith('д?отсроченное_сообщение') or message.content.startswith('д?отложка'):
            if await creating_new_event(message) is False:
                return
            return

        if main_dict[current_guild_id]['events']:
            await editing_new_event(message) # TODO добавить проверку ввода
            return


async def msg_at_time_2():
    await client.wait_until_ready()
    while not client.is_closed():
        # тут идет сравнение со строкой...Едва ли правильно, но пока работает, надо подумать
        current_time = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        for guild in main_dict.keys():
            if main_dict[guild]['events']:
                for event in main_dict[guild]['events']:
                    if event[1]['event_time']:
                        if event[1]['event_time'] == current_time:
                            channel = client.get_channel(event[1]['event_channel_id'])
                            channel_2 = client.get_channel(event[1]['action_channel_id'])
                            if event[1]['pic_url']:
                                async with aiohttp.ClientSession() as session:
                                    my_url = event[1]['pic_url']
                                    async with session.get(my_url) as resp:
                                        if resp.status != 200:
                                            await channel.send(event[1]['event_msg'],
                                                               file=discord.File(data, 'cool_image.png'))
                                            await channel_2.send(f'Картинка для события {event[0]}, которое было '
                                                                 f'запланировано на {event[1]["event_time"]} '
                                                                 f'к сожалению была утрачена.')
                                        else:
                                            data = io.BytesIO(await resp.read())
                                            await channel.send(event[1]['event_msg'],file=discord.File(data,
                                                                                                       'cool_image.png'))
                            else:
                                await channel.send(event[1]['event_msg'])
                            print('YEAH!!!!!!!!!!!!!!!!!!!!!!!!!!')
                            await channel_2.send(f'Сообщение {event[0]}, запланированное на {event[1]["event_time"]}, '
                                                 'было успешно отправлено.')
                            main_dict[guild]['events'].remove(event)
                            save_settings()
                        elif event[1]['event_time'] < current_time:
                            main_dict[guild]['events'].remove(event)
                            save_settings()
        await asyncio.sleep(0.2)


# TODO проверить нужно ли в функциях ниже создавать асинхронность
async def show_info(message):
    if main_dict[str(message.guild.id)]['events']:
        await message.channel.send("Для данного сервера запланированы следующие сообщения")
        for event in main_dict[str(message.guild.id)]['events']:
            await message.channel.send(f'ID запланированного сообщения: `{event[0]}`''\n'
                                       f'Время отправления сообщения: `{event[1]["event_time"]}`.''\n'
                                       'Канал, на который сообщение должно прийти: '
                                       # f'`{client.get_channel(event[1]["event_channel_id"])}`.''\n'
                                       f'<#{event[1]["event_channel_id"]}>.''\n'
                                       'Канал, на котором было запланировано сообщение: '
                                       # f'{client.get_channel(event[1]["action_channel_id"])}`.''\n'
                                       f'<#{event[1]["action_channel_id"]}>.''\n'
                                       f'Текст сообщения: `{event[1]["event_msg"]}`')
    else:
        await message.channel.send("Для данного сервера не имеется запланированных сообщений")


async def edit_existing_event_phase_1(message):
    if main_dict[str(message.guild.id)]['events']:
        creating_edit = f"edit № {datetime.datetime.now().strftime('%d%m%Y %H:%M')}"
        await message.channel.send("Выберете сообщение, которое необходимо отредактировать. \n"
                                   'В ответном сообщение напишите ID события в формате: `event №...` \n'
                                   "`Напишите 'стоп' для завершения редактирования.`")
        for event in main_dict[str(message.guild.id)]['events']:
            await message.channel.send(f'ID запланированного сообщения: `{event[0]}`''\n'
                                       f'Время сообщения: `{event[1]["event_time"]}`.')
        main_dict[str(message.guild.id)]['edits'].append([creating_edit, {'stage': 'choosing_event',
                                                                          'edit_event': None,
                                                                          'edit_channel_id': None,
                                                                          'edit_time': None,
                                                                          'edit_msg': None,
                                                                          'edit_pic_url': None}])
    else:
        await message.channel.send("Для данного сервера не имеется запланированных сообщений")


async def edit_existing_event_phase_2(message):
    # TODO добавить проверку канала
    current_event_stage = main_dict[str(message.guild.id)]['edits'][-1][1]['stage']
    if current_event_stage != '' and checking_end(message.content) is False:
        main_dict[str(message.guild.id)]['edits'].pop()
        await message.channel.send('Завершаю исправление события')
        return

    if main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] == 'choosing_event':
        if message.content not in main_dict[str(message.guild.id)]['events'][0]:
            await message.channel.send('Неправильно введен ID запланированного события.')
            return
        await message.channel.send(f'Будем исправлять сообщение с ID: {message.content}''\n')
        main_dict[str(message.guild.id)]['edits'][-1][1]['edit_event'] = message.content
        main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'editing_variants'

    if main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] == 'choosing_editing_data':
        if message.content.lower() not in ['канал', 'время', 'сообщение']:
            await message.channel.send('Неправильно введен ID запланированного события.')
            return
        if message.content.lower() == 'канал':
            await message.channel.send('Введите имя нового канала для отправления')
            main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'edit_target_channel'
            return
        elif message.content.lower() == 'время':
            now = datetime.datetime.now().strftime("%d%m%Y %H:%M")
            await message.channel.send('Введите новое время'
                                       f'*Если что, сегодня* {now}'
                                       '\n`Напишите в ответном сообщении дату в формате '
                                       'DD.MM.YYYY HH:MM:SS`')
            main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'edit_time'
            return
        elif message.content.lower() == 'сообщение':
            await message.channel.send('Введите новое сообщение')
            main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'edit_text'
            return

    if main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] == 'edit_target_channel':
        channel_to_send_name = message.content
        for channel in message.guild.text_channels: # спорный момент с проставлением только text_channels
            if channel.name == channel_to_send_name:
                await message.channel.send(f'Отлично, теперь отправляем на, <#{channel.id}> с id: {str(channel.id)}')
                event_id = main_dict[str(message.guild.id)]['edits'][-1][1]['edit_event']
                for event in main_dict[str(message.guild.id)]['events']:
                    if event_id in event:
                        event_index = main_dict[str(message.guild.id)]['events'].index(event)
                        # сделать какой-нибудь else?...
                main_dict[str(message.guild.id)]['events'][event_index][1].update({'event_channel_id': channel.id})
                break
                # TODO подумать про for else, возможно тут алгоритм неправильный
        else:
            main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = 'attach_channel'
            await message.channel.send('Канал ' + channel_to_send_name + ' не был найден, попробуйте снова')
            return
        await message.channel.send('Введите "стоп" или выберете информацию, которую будем редактировать далее: \n'
                                   '`Канал`, `Время` или `Сообщение`.')
        main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'choosing_editing_data'
        save_settings()
        return
    if main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] == 'edit_time':
        full_date = re.findall(r'\d{2}.\d{2}.\d{4} \d{2}.\d{2}', message.content)
        time_to_send_w_secs = re.findall(r'\d{2}.\d{2}.\d{2}', message.content)
        time_to_send_w_out_secs = re.findall(r'\d{2}.\d{2}', message.content)
        if full_date:
            event_time = full_date[0]
        elif time_to_send_w_secs:
            event_time = f'{datetime.datetime.now().strftime("%d.%m.%Y")} {time_to_send_w_secs[0]}'
        elif time_to_send_w_out_secs:
            event_time = f'{datetime.datetime.now().strftime("%d.%m.%Y")} {time_to_send_w_out_secs[0]}:00'
        else:
            await message.channel.send('Введенное время не распознанно, попробуйте снова')
            return
        await message.channel.send(f'Новое время: {event_time}')
        event_id = main_dict[str(message.guild.id)]['edits'][-1][1]['edit_event']
        for event in main_dict[str(message.guild.id)]['events']:
            if event_id in event:
                event_index = main_dict[str(message.guild.id)]['events'].index(event)
        main_dict[str(message.guild.id)]['events'][event_index][1].update({'event_time': event_time})
        await message.channel.send('Введите "стоп" или выберете информацию, которую будем редактировать далее: \n'
                                   '`Канал`, `Время` или `Сообщение`.')
        main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'choosing_editing_data'
        save_settings()
        return
    if main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] == 'edit_text':
        if 'http' in message.content:
            if message.content[-1] != '.': # проверяем есть ли точка в конце
                message_to_send_content = f'{message.content}.'
            else:
                message_to_send_content = message.content
        else:
            message_to_send_content = message.content

        event_id = main_dict[str(message.guild.id)]['edits'][-1][1]['edit_event']
        for event in main_dict[str(message.guild.id)]['events']:
            if event_id in event:
                event_index = main_dict[str(message.guild.id)]['events'].index(event)
        main_dict[str(message.guild.id)]['events'][event_index][1].update({'event_msg': message_to_send_content})
        await message.channel.send('Новое сообщение сохранено: \n'f'{event_id}')
        await message.channel.send('Введите "стоп" или выберете информацию, которую будем редактировать далее: \n'
                                   '`Канал`, `Время` или `Сообщение`.')
        main_dict[str(message.guild.id)]['edits'][-1][1]['stage'] = 'choosing_editing_data'
        save_settings()
        return


def checking_end(content):
    if content.lower() == 'стоп':
        return False
    return True


async def set_admin_role(message):
    if not main_dict[str(message.guild.id)]['admins']:
        admin_role = message.content[10:]
        for role in message.guild.roles:
            if admin_role == role.name:
                main_dict[str(message.guild.id)]['admins'].append(admin_role)
                await message.channel.send('Роль ' + admin_role + ' теперь администрирует этого бота')
                save_settings()
                return
        else:
            await message.channel.send('Роли нет')
    return


async def creating_new_event(message):
    creating_event = f"event № {datetime.datetime.now().strftime('%d%m%Y %H:%M')}"
    main_dict[str(message.guild.id)]['events'].append([creating_event, {'stage': 'attach_channel',
                                                                        'action_channel_id': message.channel.id,
                                                                        'event_channel_id': None,
                                                                        'event_time': None,
                                                                        'event_msg': None,
                                                                        'pic_url': None}])
    await message.channel.send('Делаем "отсроченное сообщение"!\n'
                               'Выберите канал, где оно будет опубликовано.\n'
                               'Если передумали, напишите "стоп" - создание сообщения будет отменено.\n\n'
                               '`Напишите название текстового канала этого сервера в ответном сообщении`')
    return


async def editing_new_event(message):
    # TODO добавить проверку канала
    current_event_stage = main_dict[str(message.guild.id)]['events'][-1][1]['stage']
    if current_event_stage != '' and checking_end(message.content) is False:
        main_dict[str(message.guild.id)]['events'].pop()
        await message.channel.send('Завершаю программирование события')
        return
    if main_dict[str(message.guild.id)]['events'][-1][1]['stage'] == 'attach_channel':  # получаем канал
        channel_to_send_name = message.content
        for channel in message.guild.channels:
            if channel.name == channel_to_send_name:
                now = datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                # TODO найти способ делать ссылку на канал
                await message.channel.send(f'Отлично, значит, <#{channel.id}> с id: {str(channel.id)}'
                                           '\n*Теперь выберите время, когда сообщение будет опубликовано.*\n'
                                           f'*Если что, сегодня* {now}'
                                           '\n`Напишите в ответном сообщении дату в формате '
                                           'DD.MM.YYYY HH:MM:SS`')
                main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = 'attach_date'
                main_dict[str(message.guild.id)]['events'][-1][1].update({'event_channel_id': channel.id})
                return
        else:
            main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = 'attach_channel'
            await message.channel.send('Канал ' + channel_to_send_name + ' не был найден, попробуйте снова')
            return
    elif main_dict[str(message.guild.id)]['events'][-1][1]['stage'] == 'attach_date':  # получаем дату
        # time_to_send = message.content
        full_date = re.findall(r'\d{2}.\d{2}.\d{4} \d{2}.\d{2}', message.content)
        time_to_send_w_secs = re.findall(r'\d{2}.\d{2}.\d{2}', message.content)
        time_to_send_w_out_secs = re.findall(r'\d{2}.\d{2}', message.content)
        if full_date:
            event_time = full_date[0]
        elif time_to_send_w_secs:
            event_time = f'{datetime.datetime.now().strftime("%d.%m.%Y")} {time_to_send_w_secs[0]}'
        elif time_to_send_w_out_secs:
            event_time = f'{datetime.datetime.now().strftime("%d.%m.%Y")} {time_to_send_w_out_secs[0]}:00'
        else:
            await message.channel.send('Введенное время не распознанно, попробуйте снова')
            return
        await message.channel.send(f'Выбранное время: {event_time}'
                                   '\nИ, наконец, введите текст сообщения.'
                                   '`Напишите текст сообщения (тут потом ещё дополню)`')
        main_dict[str(message.guild.id)]['events'][-1][1].update({'event_time': event_time})
        main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = 'attach_text'
        return
    elif main_dict[str(message.guild.id)]['events'][-1][1]['stage'] == 'attach_text':  # получаем текст
        if 'http' in message.content:
            if message.content[-1] != '.': # проверяем есть ли точка в конце
                message_to_send_content = f'{message.content}.'
            else:
                message_to_send_content = message.content
        else:
            message_to_send_content = message.content

        main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = 'attach_image'
        main_dict[str(message.guild.id)]['events'][-1][1].update({'event_msg': message_to_send_content})
        await message.channel.send('Можете добавить картинку!\n'
                                   'Вставьте ссылку на изображение в формате "https://..." или напишите "Нет", '
                                   'если не хотите прикреплять картинку')
        return
    elif main_dict[str(message.guild.id)]['events'][-1][1]['stage'] == 'attach_image':  # получаем картинку
        pic_url = str(message.content)
        if pic_url == '' or pic_url.lower() == 'нет':
            await message.channel.send('Как пожелаете. \nСоздание отсроченного сообщения завершено.')
            main_dict[str(message.guild.id)]['events'][-1][1].update({'pic_url': ''})
        else:
            await message.channel.send('Картинка успешно добавлена!')
            main_dict[str(message.guild.id)]['events'][-1][1].update({'pic_url': pic_url})
            await message.channel.send('Создание отсроченного сообщения завершено.')
        main_dict[str(message.guild.id)]['events'][-1][1]['stage'] = ''
        save_settings()
        return

client.loop.create_task(msg_at_time_2())
client.run(TOKEN)
