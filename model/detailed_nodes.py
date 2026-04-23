import dotenv
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
import os
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, BaseMessage
from typing import TypedDict, Annotated
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from db.vector_db import embedModel, vectorDb

dotenv.load_dotenv()

api_li = eval(os.getenv('GROQ_API_KEY'))

llm_li = []
llm_ind = 0
for api in api_li:
    print(api)
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


class enhanced_detailed_query_structure(BaseModel):
    queries: list[str] = Field(description='A list of 5 optimized search queries for web search')


def detailed_query_generator(state: AppState):
    usr_msg = state['usr_msg'][-1].content

    system_prompt = """You are an expert search query generator.

                    Your job is to convert a user question into 5 high-quality internet search queries.

                    Rules:
                    1. Generate 5 queries strictly
                    2. Queries must be specific and keyword-rich
                    3. Include variations (different angles of same question)
                    4. Avoid repetition or vague wording
                    5. Keep queries short and search-engine friendly
                    6. save queries in queries attribute
                    """

    human_prompt = f"User query: {usr_msg}"

    structured_llm = get_llm(state['llm_ind']).with_structured_output(enhanced_detailed_query_structure)
    state['llm_ind'] += 1
    state['llm_ind'] %= 3

    response = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    # Optional cleanup
    detailed_queries = list(set(response.queries))  # remove duplicates

    print("detailed_queries", detailed_queries)
    return {'detailed_queries': detailed_queries}


def detailed_relevant_info(state: AppState):
    detailed_queries = state['detailed_queries']
    usr_msg_embed = embedModel.generateEncoding(detailed_queries)
    detailed_retrieved_info, citation = vectorDb.get_contexts(usr_msg_embed, 5, 0.1, state['user'])
    if not isinstance(detailed_retrieved_info, list):
        detailed_retrieved_info = [detailed_retrieved_info]
    return {'detailed_retrieved_info': detailed_retrieved_info, "citation": citation}


def detailed_web_info(state: AppState):
    detailed_queries = state['detailed_queries']
    detailed_retrieved_info = []
    for detailed_query in detailed_queries:
        web_search = DuckDuckGoSearchRun()
        detailed_retrieved_info.append(web_search.invoke(detailed_query))
    return {'detailed_retrieved_info': detailed_retrieved_info}


def detailed_merge_context(state: AppState):
    detailed_retrieved_info = state.get('detailed_retrieved_info')
    return {'detailed_retrieved_info': detailed_retrieved_info}


class detailed_subheader_length_schema(BaseModel):
    headers: list[str] = Field(
        description='A list of 6 to 8 sub-headers derived from topic.This headers are for sub-sections of the topic.')
    length: list[int] = Field(description='A list of length of sub-sections of the topic.')


def detailed_subHeader_length_generation(state: AppState):
    topic = state['usr_msg'][-1].content
    print("Topic:", topic)
    prompt = '''You are an expert content planner.

                Your task is to break a given topic into well-structured sub-sections.

                topic : {topic}

                Instructions:

                1. Generate 6 to 8 meaningful and logically ordered sub-headers based on the topic.
                2. Each sub-header should represent a clear sub-section of the topic.
                3. Ensure full coverage of the topic without repetition.
                4. Keep headers short, precise, and descriptive.

                Length Rules:

                5. For each sub-header, assign an estimated length (in number of words) required to explain that section.
                6. Length should be realistic and proportional to importance.
                7. Keep lengths between 80 and 200 words per section.
                8. The number of lengths MUST exactly match the number of headers.

                Output Format (STRICT):

                Return ONLY valid JSON in this format:
                {{
                  "headers": ["header1", "header2", "..."],
                  "length": [120, 150, ...]
                }}

                Do NOT include any explanation, text, or formatting outside JSON.
                    '''.format(topic=topic)
    llm_structured_output = get_llm(state['llm_ind']).with_structured_output((detailed_subheader_length_schema))
    state['llm_ind'] += 1
    state['llm_ind'] %= 3
    output = llm_structured_output.invoke(prompt)
    return {'detailed_subHeader': output.headers, 'detailed_subHeader_length': output.length}


class detailed_section_schema(BaseModel):
    sections: list[str] = Field(
        description='A list of detailed section for each sub-header of the topic with approximately specified header length.')


def detailed_section_generation(state: AppState):
    topic = state['usr_msg'][-1].content
    detailed_subHeader = state['detailed_subHeader']
    detailed_subHeader_length = state['detailed_subHeader_length']
    prompt = '''
                You are an expert content writer.

                Your task is to generate detailed section content based on given sub-headers and their respective lengths.

                Inputs:
                - Topic: {topic}
                - Sub-headers: {detailed_subHeader}
                - Lengths (in words): {detailed_subHeader_length}

                Instructions:

                1. Generate one section for each sub-header.
                2. Each section must correspond exactly to its sub-header.
                3. The number of sections MUST match the number of sub-headers.
                4. Each section should be approximately the specified length (±20 words is acceptable).
                5. Content should be clear, informative, and well-structured.
                6. Do NOT repeat content across sections.
                7. Maintain logical flow and coherence across all sections.
                8. Do NOT include section titles inside the content (only body text).
                9. Do NOT include numbering, bullets, or markdown.
                10. Keep language simple and readable.

                Output Format (STRICT):

                Return ONLY valid JSON in this format:
                {{
                    "sections": [
                        "section content 1",
                        "section content 2",
                        "section content 3"
                    ]
                }}

                Do NOT include any explanation or text outside JSON.'''.format(topic=topic,
                                                                               detailed_subHeader=detailed_subHeader,
                                                                               detailed_subHeader_length=detailed_subHeader_length)
    llm_with_schema = get_llm(state['llm_ind']).with_structured_output(detailed_section_schema)
    state['llm_ind'] += 1
    state['llm_ind'] %= 3
    output = llm_with_schema.invoke(prompt)
    print("******3333333***************", output)

    return {"detailed_subSection": output.sections}


class detailed_merge_finalize_schema(BaseModel):
    detailed_answer: str = Field(
        description='A very detailed and structured report based on sub section body and topic')


def detailed_merge_finalize(state: AppState):
    topic = state['usr_msg'][-1].content
    detailed_subSection = state['detailed_subSection']

    prompt = '''You are an expert report writer.

            Your task is to generate a complete, well-structured, and detailed report using the provided topic and section contents.

            Inputs:
            - Topic: {topic}
            - Section Contents: {detailed_subSection}

            Instructions:

            1. Combine all sections into a single coherent report.
            2. Maintain logical flow and smooth transitions between sections.
            3. Do NOT remove or ignore any section content.
            4. Improve clarity, readability, and structure where needed.
            5. Avoid repetition across sections.
            6. Ensure the report is comprehensive and well-organized.

            Structure Rules:

            7. Start with a clear introduction based on the topic.
            8. Organize the report into sections using appropriate headings.
            9. Each section should be clearly separated and easy to read.
            10. End with a concise conclusion summarizing key points.

            Formatting Rules (STRICT):

            11. Return the output strictly in HTML format.
            12. Use <h2> for section headings.
            13. Use <p> for paragraphs.
            14. Use <ul> and <li> for lists where appropriate.
            15. Do NOT use markdown (**, -, #, etc.).
            16. Wrap the entire output inside a single <div>.
            17. Do NOT include any explanation outside HTML.

            Output Format:

            {{
              "detailed_answer": "<div>...full HTML report...</div>"
            }}
            '''.format(topic=topic, detailed_subSection=detailed_subSection)
    llm_with_structured_output = get_llm(state['llm_ind']).with_structured_output(
        detailed_merge_finalize_schema)
    state['llm_ind'] += 1
    state['llm_ind'] %= 3
    output = llm_with_structured_output.invoke(prompt)
    return {'usr_msg': [AIMessage(content=output.detailed_answer)]}