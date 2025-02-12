from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from sqlalchemy import text
from datetime import datetime as dt
import pytz
import json
from app.prompts import extract_reservation_time_prompt, extract_cancellation_time_prompt, classification_prompt, app_info_prompts

from app.core.db import engine

load_dotenv()

llm = ChatOpenAI(
    temperature=0.5,
    model_name="gpt-4o",
)

kst = pytz.timezone('Asia/Seoul')
time_kst = dt.now(kst)
current_time = time_kst.strftime('%Y-%m-%d %H:%M:%S')


def extract_time(user_prompt: str, system_prompt) -> str:
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    extract_time_response = generate_llm_response(messages)
    return extract_time_response


def message_classificator(query: str):
    messages = [{"role": "system", "content": classification_prompt}, {"role": "user", "content": query}]
    classificator_response = generate_llm_response(messages)

    return classificator_response


def handle_reservation(user_input: str, user_name: str):
    c_prompt = f"""
        Given that the current time is {current_time}. Determine the reservation_start_time and reservation_end_time from the following room reservation request:

        Message: {user_input}

        Respond only with a valid JSON object string in the format:
        {{"reservation_start_time": "YYYY-MM-DD HH:MM:SS", "reservation_end_time": "YYYY-MM-DD HH:MM:SS"}}

        If the message lacks a clear reservation_start_time, return:
        {{"reservation_start_time": "", "reservation_end_time": ""}}
                    """
    reservation_times_json_object = extract_time(c_prompt, extract_reservation_time_prompt)

    parsed_data = json.loads(reservation_times_json_object)
    if not parsed_data.get("reservation_start_time") or not parsed_data.get("reservation_end_time"):
        raise json.JSONDecodeError("Invalid reservation time", reservation_times_json_object,
                                   0)  # Add required arguments

    query = text(f"""
        SELECT *   
        FROM reservations
        WHERE (
            '{parsed_data['reservation_start_time']}' > reservation_start_time AND  '{parsed_data['reservation_end_time']}' < reservation_end_time
            OR '{parsed_data['reservation_end_time']}' > reservation_start_time AND '{parsed_data['reservation_start_time']}' < reservation_end_time
            OR reservation_start_time > '{parsed_data['reservation_start_time']}' AND reservation_start_time < '{parsed_data['reservation_end_time']}'
            OR reservation_end_time > '{parsed_data['reservation_start_time']}' AND reservation_end_time < '{parsed_data['reservation_end_time']}'
        );
        """
                 )
    with engine.begin() as connection:
        result = connection.execute(query)
        if (result.rowcount == 0):
            query = f"INSERT INTO reservations (reservator_name, reservation_start_time, reservation_end_time) VALUES ('{user_name}', '{parsed_data['reservation_start_time']}', '{parsed_data['reservation_end_time']}');"
            connection.execute(text(query))
            engine.dispose()
            return f"해당 날짜 및 시간({parsed_data['reservation_start_time']} ~ {parsed_data['reservation_end_time']})으로 예약이 성공적으로 완료되었습니다."
        else:
            reservation_info = result.mappings().fetchone()

            return f"해당 날짜 및 시간({parsed_data['reservation_start_time']} ~ {parsed_data['reservation_end_time']})에 객실이 이미 예약되어 있어 예약이 불가능합니다. 해당 객실은 <@{reservation_info['reservator_name']}> 의해 예약되었습니다."


def handle_cancellation(user_input: str, user_name: str):
    prompt = f"""
        Given that the current time is {current_time}, determine the reservation_start_time from the following reservation cancellation request:

        Message: {user_input}

        Respond only with a valid JSON object string in the format:
        {{"reservation_start_time": "YYYY-MM-DD HH:MM:SS"}}

        If the message lacks a clear reservation_start_time, return:
        {{"reservation_start_time": ""}}
    """
    cancel_reservation_time_json_object = extract_time(prompt, extract_cancellation_time_prompt)
    parsed_data = json.loads(cancel_reservation_time_json_object)
    if not parsed_data.get("reservation_start_time"):
        raise json.JSONDecodeError("Invalid reservation time", cancel_reservation_time_json_object, 0)

    query = text(f"""
                        SELECT *   
                        FROM reservations
                        AND reservation_start_time = '{parsed_data['reservation_start_time']}';
                """)

    with engine.begin() as connection:
        result = connection.execute(query)
        if (result.rowcount > 0):
            reservation_info = result.mappings().fetchone()
            if reservation_info['reservator_name'] != user_name:
                return f"허용되지 않습니다. 이 예약은 <@{reservation_info['reservator_name']}>에 의해 이루어진 예약이므로, 본인이 만든 예약만 취소할 수 있습니다."
            query = f"DELETE FROM reservations WHERE reservation_start_time = '{parsed_data['reservation_start_time']}';"
            connection.execute(text(query))
            engine.dispose()
            return f"해당 날짜 및 시간({parsed_data['reservation_start_time']})의 예약이 취소되었습니다."

        return f"해당 시작 날짜 및 시간({parsed_data['reservation_start_time']})의 예약을 찾을 수 없습니다."


def handle_show_reservations():
    query = f"SELECT * FROM reservations WHERE reservation_start_time >= CURRENT_DATE AND reservation_start_time <= CURRENT_DATE + INTERVAL '1 day' * ((7 - EXTRACT(DOW FROM CURRENT_DATE)) + 7) ORDER BY reservation_start_time;"

    with engine.connect() as connection:
        result = connection.execute(text(query))
        reservation = result.mappings().fetchall()
    # Generate the table for today until next week's Sunday

    return reservation


def handle_delete_all_reservations(user_name: str):

    with engine.begin() as connection:
        # Use parameterized queries to prevent SQL injection
        query = text("""
                       DELETE FROM reservations
                       WHERE reservator_name = :user_name;
                   """)

        result = connection.execute(query, {"user_name": user_name})
        engine.dispose()

        if result.rowcount > 0:
            return f"<@{user_name}> 예약이 취소되었습니다."
        else:
            return f"<@{user_name}> 예약 내역이 없습니다."


def handle_show_details(user_input: str):
    messages = [{"role": "system",
                 "content": f"You answer only in korean. You keeps same tone and style as users. You give only examples of how to use this room reservation app. This is infromation about app: '{app_info_prompts}'"}]
    prompt = f"""
                This is user message: '{user_input}. Give examples of how to use this room reservation app.' 
                """
    messages.append({"role": "user", "content": prompt})
    classificator_response = generate_llm_response(messages)

    return classificator_response


def take_action(classificator_response: str, user_input: str, user_name: str):
    try:
        action_code = int(classificator_response)

        if action_code == 2:
            return handle_reservation(user_input, user_name)

        elif action_code == 3:
            return handle_cancellation(user_input, user_name)

        elif action_code == 4:
            return handle_delete_all_reservations(user_name)

        elif action_code == 1:
            return handle_show_reservations()
        else:
            return handle_show_details(user_input)

    except json.JSONDecodeError as e:
        return "예약 날짜 또는 시간이 올바른 형식이 아니거나 인식할 수 없습니다."
    except ValueError:
        return classificator_response


def generate_llm_response(messages):
    response = llm.invoke(messages)
    return response.content


def generate_slack_response(input: str, user_name: str) -> str:
    action = message_classificator(input)
    output = take_action(action, input, user_name)
    return output
