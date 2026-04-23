# SeekInfo – Intelligent Agentic Search & Knowledge System

## Overview

SeekInfo isn’t your average chatbot. It’s an AI-powered knowledge engine that juggles user data (PDFs, text files, even pasted snippets), real-time web search, and strong reasoning with memory built in. The system figures out the best way to answer your question—sometimes it taps into its own knowledge, sometimes it pulls info from your docs, fires up a web search, or even builds out a deep-dive, multi-step report. This isn’t about chatting. It’s about smart, dynamic decision-making from end to end.

---

# Core Architecture

High-level, here’s how things move:

User → UI → Flask Backend → Agent Graph → LLM & Tools → Reply (with Sources)

---

# Frontend (index.html)

## What the Frontend Does

**1. Chat Interface**
- Shows messages from you and the bot.
- Manages multiple conversations.
- Stylish, animated, scrollable chat.

**2. Interaction Modes**
- Choose how you want answers:
  - Normal Answer
  - Quick Summary
  - Detailed Report
- These choices control how the backend processes your question.

**3. File Upload**
- Drop in PDFs or TXT files.
- Upload flow is slick: files go to `/upload`, backend does background processing, frontend checks on progress, and you see clear “processing” or “ready” statuses.

**4. Custom Text**
- Paste in any text—treats it like another document for searching.

**5. Chat Threads**
- Start a new chat (`/new_chat`), load existing ones, or pull up the message history. It’s all there.

**6. Citations**
- Every bot answer includes clickable source “chips.”
- Click for a detailed popup showing the source file, page, and the exact quote the answer came from.
- You always know exactly where info came from.

**7. Authentication**
- Supports both basic email/password and Google sign-in.
- JWT tokens stored securely in cookies.
- Backend tracks your session.

---

# Backend (app.py)

## What Happens Behind the Scenes

**1. Session & Auth**
- Flask sessions and cookie-based JWTs.
- Endpoint `/check_auth` to confirm you’re logged in.

**2. Chat System**
| Endpoint    | What It Does           |
|-------------|-----------------------|
| `/new_chat` | Start new conversation|
| `/get_thread` | See all chats       |
| `/get_chat`  | Load messages        |

**3. Upload Pipeline**
- Handles uploads step by step:
  1. Checks & saves file, uniquely per user.
  2. Processes it in the background (async, so app stays fast).
  3. Adds chunks to vector DB for search.
  4. Keeps upload progress updated for the frontend.

**4. Query Processing**
- Main endpoint is `/generate`:
  - Give it your question, the answer mode, and which thread you’re in.
  - It returns the answer and the matching citations.

**5. Logout Cleanup**
- On logout, it wipes your session, file uploads, and any vector data tied to you. Nothing lingers.

---

# Agentic System (Agentic.py)

This is the real brain, built on LangGraph’s StateGraph.

## Node Highlights

- **Memory Handling:** Preps short-term and long-term memory, compresses chat history for context-aware replies.
- **Search & Retrieval:** Pulls relevant info from your uploaded docs.
- **Web Decisions:** Smartly figures out if web data is needed. If so, crafts a better query and gets it.
- **Final Answer:** Merges all sources, gives a clear response.

### Detailed Report Pipeline
When you select “Detailed Report,” the system runs an elaborate, multi-stage process:
- Generates sub-questions and queries
- Gathers details from docs and the web as needed
- Organizes into sections
- Wraps up everything into a structured, multi-section report

---

# Decision Logic (Why It's Smart)

Step 1: Checks which answer mode you picked. If you asked for a report, it launches the full pipeline. Otherwise, it goes to a classic QA path.

Step 2: Decides if fresh web data is needed. If so, fetches and blends it in. If not, sticks with internal sources.

Step 3: Answers your question, always including citations.

---

# Memory Design

- **Short-Term Memory (STM):** Remembers recent chat so answers keep the conversation’s flow.
- **Long-Term Memory (LTM):** Stores background knowledge and preferences for each user.

---

# Vector Database

- Chunks and embeds every document for fast semantic search.
- When you search, it grabs the most relevant chunks and plugs them into the answer.

---

# Database Layer

- User DB: email, password, token.
- Chat DB: threads, users, names.
- LTM DB: user-specific long-term memory.

---

# Citation System

- Each answer links directly to its sources: file name, page, and the precise snippet quoted.
- Frontend turns these into clickable chips so you can always trace what the bot says.

---

# Example Workflows

**1. Simple Question:**  
You ask, “What is AI?”  
- System checks recent chat, long-term user info, and stored docs.  
- Generates answer — no web needed.

**2. File-Based Question:**  
“Summarize my uploaded file.”  
- Searches and extracts info directly from your document.

**3. Real-Time Need:**  
“Latest news on AI.”  
- Bot detects the need for up-to-date info, searches the web, adds sources, builds the answer.

**4. Detailed Report:**  
You ask for a deep dive — the system orchestrates a multi-step report with sections and sources.

---

# Security

- Sessions use JWTs in secure cookies.
- Each user’s data and files stay totally isolated.
- When you log out, all your data and session info vanish — no leftovers.

---

# Limitations

- There’s no rate limiting yet.
- Files over 1MB aren’t supported.
- Only runs on a single server for now.
- No distributed task queue — threads handle async work, which isn’t as scalable.

---

# Looking Ahead

- Plans for a Redis queue to handle scale.
- Streaming answers for a smoother feel.
- Better UI state and multi-user support.
- Smarter, sharper filtering in the vector DB.

---

# Final Thoughts

SeekInfo stands out because it doesn’t just pull from one source. It doesn’t blindly search the web or always fall back on retrieval — it uses smart logic to decide the best move every time you ask something. That’s real agentic intelligence in action.

---

# Quick Recap

- Hybrid AI with web, memory, and your docs.
- Chatbot that’s actually explainable (great citations).
- Modular agent pipeline, totally context-aware.

And if you’re ready for next steps, let’s do something concrete — mapping out an architecture diagram, tuning the agent graph, or improving RAG logic for tougher scenarios (interviews, anyone?). Just say the word.