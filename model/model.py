import os
import dotenv
from model.agentic_ai import answer, thread_chat
from db.vector_db import embedModel, vectorDb
dotenv.load_dotenv()


# load_data()
def get_answer(prompt, user, thread, mode):
    ans, citation = '', ''
    if mode == 'report':
        ans, citation = answer(usr_msg=prompt, user=user, thread=thread, is_detailed=True)
    elif mode == 'summary':
        ans, citation = answer(usr_msg=prompt+". Summerize the answer.", user=user, thread=thread, is_detailed=False)
    elif mode == 'normal':
        ans, citation = answer(usr_msg=prompt, user=user, thread=thread, is_detailed=False)
    return ans, citation

def get_thread_chat(thread):
    return thread_chat(thread)