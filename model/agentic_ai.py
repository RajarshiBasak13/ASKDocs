import sqlite3

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_community.tools import DuckDuckGoSearchRun
import os
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, BaseMessage
from langgraph.graph.message import add_messages
import dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from db.db import User_chat_db
from model.detailed_nodes import *
from model.qa_nodes import *

graph = StateGraph(AppState)

graph.add_node('STM_preparation', STM_preparation)
graph.add_node('chat_summery', chat_summery)
graph.add_node('LTM_preparation', LTM_preparation)
graph.add_node('detailed_query_generator', detailed_query_generator)
graph.add_node('detailed_relevant_info', detailed_relevant_info)
graph.add_node('detailed_web_info', detailed_web_info)
graph.add_node('detailed_merge_context', detailed_merge_context)
graph.add_node('detailed_subHeader_length_generation', detailed_subHeader_length_generation)
graph.add_node('detailed_section_generation', detailed_section_generation)
graph.add_node('detailed_merge_finalize', detailed_merge_finalize)
graph.add_node("decide_webdata_needed", decide_webdata_needed)
graph.add_node('retrieved_relevant_info', retrieved_relevant_info)
graph.add_node('enhanced_query', enhanced_query)
graph.add_node('search_web', search_web)
graph.add_node('final_ans_with_aggregate_context', final_ans_with_aggregate_context)

graph.add_conditional_edges(START, check_detailed, {'qa': 'STM_preparation', 'detailed': 'detailed_query_generator'})

graph.add_edge("detailed_query_generator", "detailed_relevant_info")
graph.add_edge("detailed_query_generator", "detailed_web_info")

graph.add_edge("detailed_relevant_info", "detailed_merge_context")
graph.add_edge("detailed_web_info", "detailed_merge_context")

graph.add_edge("detailed_merge_context", "detailed_subHeader_length_generation")
graph.add_edge("detailed_subHeader_length_generation", "detailed_section_generation")
graph.add_edge("detailed_section_generation", "detailed_merge_finalize")
graph.add_edge("detailed_merge_finalize", END)

graph.add_edge('STM_preparation', 'chat_summery')
graph.add_edge('chat_summery', 'LTM_preparation')
graph.add_edge('LTM_preparation', 'retrieved_relevant_info')

graph.add_edge('LTM_preparation', 'decide_webdata_needed')
graph.add_conditional_edges('decide_webdata_needed', is_webdata_needed,
                            {'yes': 'enhanced_query', 'no': 'final_ans_with_aggregate_context'})
graph.add_edge('enhanced_query', 'search_web')
graph.add_edge(['retrieved_relevant_info','search_web'], 'final_ans_with_aggregate_context')

graph.add_edge('final_ans_with_aggregate_context', END)

conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
checkpoint = SqliteSaver(conn)
workflow = graph.compile(checkpointer=checkpoint)


def answer(user, usr_msg, thread, is_detailed=False):
    global llm_li
    initial_state = {'user': user, 'usr_msg': [HumanMessage(content=usr_msg)], 'llm_ind': 0,
                     'is_detailed': is_detailed}

    config = {"configurable": {"thread_id": thread}}
    workflow.invoke(initial_state, config=config)

    reply = list(workflow.get_state_history(config=config))[0].values

    chat_db = User_chat_db()
    chat_db.update_chatname(thread,reply['chat_subject'])

    return reply['usr_msg'][-1].content, reply['citation']


def thread_chat(thread):
    config = {"configurable": {"thread_id": thread}}
    all_chats = []
    citation = []
    if len(list(workflow.get_state_history(config=config))) > 0:
        for i in list(workflow.get_state_history(config=config)):
            if ('citation' in i.values) and (i.values['citation'] not in citation):
                citation.append(i.values['citation'])
        for i in list(workflow.get_state_history(config=config))[0].values['usr_msg']:
            if isinstance(i,HumanMessage):
                all_chats.append(('user',i.content))
            elif(isinstance(i,AIMessage)):
                all_chats.append(('bot', i.content))
    print("----------------------------------------------------")
    print("citation",citation)
    return all_chats, citation[::-1]

