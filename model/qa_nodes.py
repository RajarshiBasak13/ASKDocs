from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
import dotenv
import os
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, BaseMessage
from typing import TypedDict, Annotated
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from db.vector_db import embedModel, vectorDb
from db.db import User_LTM_db

dotenv.load_dotenv()

api_li = eval(os.getenv('GROQ_API_KEY'))
llm_li = []
llm_ind = 0
for api in api_li:
    llm = ChatGroq(model='llama-3.3-70b-versatile', api_key=api)
    llm_li.append(llm)


def get_llm(ind):
    return llm_li[ind]


class AppState(TypedDict):
    user: str
    usr_msg: Annotated[list[BaseMessage], add_messages]
    llm_ind: int
    citation: list
    chat_subject: str

    is_detailed: bool
    detailed_retrieved_info: Annotated[list[str], add]
    detailed_queries: list[str]
    detailed_subHeader: list[str]
    detailed_subHeader_length: list[int]
    detailed_subSection: list[str]

    retrieved_info: Annotated[list[str], add]
    citation_info: list[str]
    is_relevant_info: list[bool]
    is_webdata_needed: bool
    query: str
    filtered_stm: str
    filtered_ltm: str
    answer: str


def check_detailed(state: AppState):
    if state['is_detailed']:
        return 'detailed'
    else:
        return 'qa'


class check_webdata_schema(BaseModel):
    is_webdata_needed: bool = Field(
        description=" Return True if answering the query requires up-to-date, real-time, or external information from the internet. Else return False."
    )


def is_greeting(text: str):
    text = text.lower().strip()

    greetings = [
        "hi", "hello", "hey", "hii",
        "hello i am", "hi i am", "hey i am",
        "nice to meet you"
    ]

    return any(text.startswith(g) for g in greetings)


def decide_webdata_needed(state: AppState):
    usr_msg = state['usr_msg'][-1].content
    # Rule-based overrides
    if is_greeting(usr_msg):
        return {'is_webdata_needed': False}

    system_prompt = """You are a decision-making assistant.

                        Your job is to decide whether answering a user query requires internet search.

                        Follow these strict rules:

                        1. Return True if:
                        - Query needs recent, real-time, or updated information (news, prices, current events, APIs, versions)
                        - Query depends on external or dynamic data (live systems, websites, latest tools)

                        2. Return False if:
                        - Query is based on general knowledge (math, coding, theory, definitions)
                        - Query can be answered using standard LLM knowledge
                        - Query can be answered with in-memory context
                        - Query is a greeting, introduction, or casual conversation
                          (e.g., "hello", "hi", "hey", "hello I am...", "nice to meet you")
                        
                        IMPORTANT:
                        If the message is conversational and does NOT require factual lookup, return False.
                        
                        Return ONLY valid JSON in this format:
                        {
                        "is_webdata_needed": bool
                        }
                        Do NOT include explanation.
                        Do NOT include extra fields.
                                                """

    human_prompt = f"User query: {usr_msg}"

    prompt = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]

    structured_llm = get_llm(state['llm_ind']).with_structured_output(check_webdata_schema)
    a = state['llm_ind'] + 1
    a = a % 3
    output = structured_llm.invoke(state['usr_msg'] + prompt)
    if "is_webdata_needed" not in output:
        return {'is_webdata_needed': True}

    return {'is_webdata_needed': output['is_webdata_needed'], 'llm_ind': a}


def is_webdata_needed(state: AppState):
    if state['is_webdata_needed']:
        return "yes"
    else:
        return 'no'


class chat_summery_structure(BaseModel):
    chat_subject: str = Field(description='A optimized summery of user asked questions')


def chat_summery(state: AppState):
    usr_msg = [i for i in state['usr_msg'] if isinstance(i, HumanMessage)]

    system_prompt = """Analyze the user’s previous message and create a concise chat title (max 5–7 words).
                        The title should capture the core topic and purpose.
                        Use simple words.
                        Do not include punctuation like quotes or emojis.
                        Do not add explanations.
                        Output only the title.
                    """

    structured_llm = get_llm(state['llm_ind']).with_structured_output(chat_summery_structure)
    a = state['llm_ind'] + 1
    a = a % 3

    response = structured_llm.invoke(usr_msg+[
        SystemMessage(content=system_prompt)
    ])

    # Optional cleanup
    chat_subject = response.chat_subject  # remove duplicates

    print("chat_subject", chat_subject)
    return {'chat_subject': chat_subject, 'llm_ind': a}


class enhanced_query_structure(BaseModel):
    query: str = Field(description='A optimized search query for web search')


def enhanced_query(state: AppState):
    usr_msg = state['usr_msg'][-1].content

    system_prompt = """You are an expert search query generator.

                    Your job is to convert a user question into a high-quality internet search query.

                    Rules:
                    1. Generate 1 query only strictly
                    2. Query must be specific and keyword-rich
                    3. Include variation (different angle of same question)
                    4. Avoid repetition or vague wording
                    5. Keep query short and search-engine friendly
                    6. save query in query attribute
                    7. Dont change anything if User query is close to greetings, wishes.
                    """

    human_prompt = f"User query: {usr_msg}"

    structured_llm = get_llm(state['llm_ind']).with_structured_output(enhanced_query_structure)
    a = state['llm_ind'] + 1
    a = a % 3

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    # Optional cleanup
    query = response.query  # remove duplicates

    print("enhanced_query", query)
    return {'query': query, 'llm_ind': a}


def search_web(state: AppState):
    question = state['query']
    web_search = DuckDuckGoSearchRun()
    return {"retrieved_info": [web_search.invoke(question)]}


def retrieved_relevant_info(state: AppState):
    usr_msg = state['usr_msg'][-1].content
    usr_msg_embed = embedModel.generateEncoding([usr_msg])[0]
    contexts, citation = vectorDb.get_contexts(usr_msg_embed, 5, 0.1, user_id=state['user'])
    citation = [dict(t) for t in {tuple(d.items()) for d in citation}]

    return {'retrieved_info': list(set(contexts)), "citation": citation}


def final_ans_with_aggregate_context(state: AppState):
    LTM_db = User_LTM_db()
    ltm = '\n'.join([i[0] for i in LTM_db.get_user_LTM(state['user'])])
    retrieved_info = ltm + state.get('filtered_stm', '') + "\n\n".join(state['retrieved_info'])
    usr_msg = state['usr_msg'][-1].content

    system_prompt = """You are a helpful AI assistant.

                    Your task is to answer the user’s query using the provided context.

                    Rules:

                    0. Use in-memory context whenever its available.
                    1. Use ONLY the provided context to answer when relevant information is available.
                    2. If the context does NOT contain sufficient information, answer based on your general knowledge without mentioning the context.
                    3. Do NOT say things like "context is insufficient" or refer to the context in your response.
                    4. Keep answers clear, concise, and well-structured.
                    5. Highlight key points when helpful.
                    6. Be direct and relevant to the question.
                    7. If the user input is a simple greeting (e.g., "hi", "hello"), respond briefly and naturally without adding extra information.

                    Formatting Rules (STRICT):

                    6. Return the answer strictly in HTML format.
                    7. Use <p> for paragraphs.
                    8. Use <h3> for section headings.
                    9. Use <ul> and <li> for lists where appropriate.
                    10. Do NOT use markdown (**, -, #, etc.).
                    11. Do NOT include any explanation outside HTML.
                    """

    human_prompt = f"""
                    User Question:
                    {usr_msg}

                    retrieved Context:
                    {retrieved_info}
                    """
    final_prompt = state['usr_msg'] + [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    response = get_llm(state['llm_ind']).invoke(final_prompt).content
    a = state['llm_ind'] + 1
    a = a % 3

    return {'usr_msg': [AIMessage(content=response)], 'llm_ind': a}


class stm_schema(BaseModel):
    filtered_stm: str = Field(description='Summery of previous messages not present already')


def STM_preparation(state: AppState):
    messages = state['usr_msg']
    stm = state.get('filtered_stm', '')

    systemMessage = """You are an expert conversation summarizer.

    Your task is to compress previous messages into a concise memory block.

    Rules:

    1. Keep ONLY important information:
       - user facts (name, preferences, intent)
       - key questions and answers
       - important context needed for future replies

    2. REMOVE:
       - greetings, filler text, small talk
       - repeated or redundant information
       - unnecessary explanations

    3. DO NOT repeat anything in filtered_stm, If repeated already REMOVE it.

    4. Keep the summary as short as possible while preserving meaning.

    5. Maintain clarity and continuity of conversation.

    Output Format (STRICT):
    Return a clean, compact paragraph (no bullet points, no markdown).
    """

    humanMessage = f"""
    Existing Memory:
    {stm}
    """

    final_prompt = state['usr_msg'] + [
        SystemMessage(content=systemMessage),
        HumanMessage(content=humanMessage)
    ]
    filtered_stm = get_llm(state['llm_ind']).with_structured_output(stm_schema).invoke(final_prompt).filtered_stm
    a = state['llm_ind'] + 1
    a = a % 3

    return {'llm_ind': a, 'filtered_stm': stm + ' ' + filtered_stm, 'usr_msg': messages[-1:]}


class ltm_schema(BaseModel):
    filtered_ltm: str = Field(description='Extract useful information from previous messages not present already')


def LTM_preparation(state: AppState):
    messages = state['usr_msg']

    LTM_db = User_LTM_db()
    ltm = '\n'.join([i[0] for i in LTM_db.get_user_LTM(state['user'])])

    systemMessage = """You are an expert memory extraction system.

                    Your task is to extract LONG-TERM USER MEMORY from the conversation.
                    
                    Rules:
                    
                    1. Extract ONLY stable and reusable user information:
                       - name
                       - preferences (likes/dislikes)
                       - goals
                       - profession
                       - important personal facts
                    
                    2. DO NOT extract:
                       - temporary questions
                       - one-time queries
                       - greetings or small talk
                       - assistant responses
                    
                    3. If information already exists in existing_ltm, DO NOT repeat or duplicate it.
                    
                    4. Keep memory concise and meaningful.
                    
                    5. If no useful long-term memory is found, return an empty list.
                    
                    Return a clean, compact paragraph (no bullet points, no markdown).
    """

    humanMessage = f"""
    existing_ltm:
    {ltm}
    """

    final_prompt = state['usr_msg'] + [
        SystemMessage(content=systemMessage),
        HumanMessage(content=humanMessage)
    ]
    filtered_ltm = get_llm(state['llm_ind']).with_structured_output(ltm_schema).invoke(final_prompt).filtered_ltm
    a = state['llm_ind'] + 1
    a = a % 3
    LTM_db.update_LTM(state['user'], filtered_ltm)

    return {'llm_ind': a, 'filtered_ltm': filtered_ltm}
