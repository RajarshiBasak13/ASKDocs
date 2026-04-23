# SeekInfo – Intelligent Agentic Search & Knowledge System

## 🚀 Overview

**SeekInfo** is an advanced AI-powered knowledge system that combines:

* 📂 **User-provided data (PDF, TXT, custom text)**
* 🌐 **Web search (on-demand)**
* 🧠 **LLM reasoning with memory (STM + LTM)**
* 🔁 **Agentic workflow (LangGraph-based orchestration)**

The system dynamically decides **how to answer a query**:

* Direct answer (LLM knowledge)
* Retrieval from vector database (RAG)
* Web search augmentation
* Multi-step detailed report generation

This is not a simple chatbot. It is a **decision-making AI pipeline**.

---

# 🧠 Core Architecture

## High-Level Flow

```
User → UI → Flask Backend → Agentic Graph → LLM + Tools → Response + Citations
```

---

# 🖥️ Frontend (index.html)

## Key Responsibilities

### 1. Chat Interface

* Displays user and bot messages
* Supports multiple chat threads
* Scrollable chat container with animation

### 2. Modes of Interaction

User can select:

* `Normal Answer`
* `Quick Summary`
* `Detailed Report`

These directly influence backend agent routing.

---

### 3. File Upload System

Supports:

* `.pdf`
* `.txt`

Flow:

1. User uploads file
2. File sent to `/upload`
3. Backend processes asynchronously
4. UI polls `/upload_status`
5. Shows:

   * ⏳ processing
   * ✅ ready

---

### 4. Custom Text Injection

* User can paste raw text
* Sent to `/add_text`
* Treated like a document in vector DB

---

### 5. Chat Thread System

* `/new_chat` → creates thread
* `/get_thread` → loads history
* `/get_chat` → loads messages

---

### 6. Citation System (Important Feature)

Each bot response:

* Displays **source chips**
* On click → opens popup with:

  * Source name
  * Page number (if exists)
  * Exact chunk used

This gives **true explainability**

---

### 7. Authentication

Supports:

* Email/password login
* Google OAuth

Uses:

* JWT stored in cookie (`auth_token`)
* Session tracking on backend

---

# ⚙️ Backend (app.py)

## Core Components

### 1. Session & Auth

* Uses Flask session + JWT cookies
* `/check_auth` validates user

---

### 2. Chat System

| Endpoint      | Purpose           |
| ------------- | ----------------- |
| `/new_chat`   | Create new thread |
| `/get_thread` | Get all chats     |
| `/get_chat`   | Load chat history |

---

### 3. Upload Pipeline

```
Upload → Save → Async Processing → Vector DB
```

Steps:

1. Validate file
2. Save with user prefix
3. Start thread:

   ```
   load_data(user_id, filename)
   ```
4. Track status in `upload_st`

---

### 4. Query Processing

Main endpoint:

```
POST /generate
```

Input:

```json
{
  "prompt": "...",
  "mode": "normal | summary | report",
  "thread": "thread_id"
}
```

Output:

```json
{
  "answer": "...",
  "citation": [...]
}
```

---

### 5. Logout Cleanup (Important Design)

On logout:

* Deletes user vector data
* Deletes uploaded files
* Clears session

This avoids:

* data leakage
* storage bloat

---

# 🤖 Agentic System (Agentic.py)

This is the **brain of the system**.

Built using **LangGraph StateGraph**.

---

## 🧩 Nodes Overview

### Memory Pipeline

1. `STM_preparation` → Short-term memory prep
2. `chat_summery` → compress chat history
3. `LTM_preparation` → long-term memory integration

---

### Retrieval Pipeline

4. `retrieved_relevant_info` → vector DB search

---

### Web Decision System

5. `decide_webdata_needed`
6. `enhanced_query`
7. `search_web`

---

### Final Answer

8. `final_ans_with_aggregate_context`

---

## 📊 Detailed Mode Pipeline

Triggered when:

```
mode = "report"
```

Flow:

```
detailed_query_generator
    ↓
detailed_relevant_info + detailed_web_info
    ↓
detailed_merge_context
    ↓
detailed_subHeader_length_generation
    ↓
detailed_section_generation
    ↓
detailed_merge_finalize
```

Output:

* Structured report
* Multi-section answer

---

# 🔀 Decision Logic (Very Important)

### Step 1: Mode Check

```
check_detailed:
    if report → detailed pipeline
    else → QA pipeline
```

---

### Step 2: Web Decision

```
decide_webdata_needed → is_webdata_needed
```

If:

* Query needs fresh info → YES
* Otherwise → NO

---

### Step 3: Final Routing

#### Case 1: No Web Needed

```
retrieved_relevant_info → final answer
```

#### Case 2: Web Needed

```
enhanced_query → search_web → merge → final answer
```

---

# 🧠 Memory Design

## Short-Term Memory (STM)

* Recent conversation
* Helps contextual replies

## Long-Term Memory (LTM)

* Stored in DB
* Used for personalization

---

# 📦 Vector Database

Used for:

* Document embeddings
* Semantic search

Flow:

```
Document → Chunk → Embed → Store
Query → Embed → Similarity search → Context
```

---

# 🗂️ Database Layer

## Tables

### User DB

* email
* password
* token

### Chat DB

* thread_id
* user
* chat_name

### LTM DB

* long-term memory storage

---

# 🔍 Citation Mechanism

Each answer returns:

```
[
  {
    source: "file.pdf",
    page: 3,
    chunk: "text..."
  }
]
```

Frontend converts into:

* clickable chips
* popup view

---

# 🧪 Example Workflows

---

## 🧾 Case 1: Simple Question

```
User: "What is AI?"

Flow:
STM → LTM → Retrieval → Final Answer
```

No web used.

---

## 📂 Case 2: File-Based Question

```
User: "Summarize my uploaded file"
```

Flow:

```
Vector DB → Retrieve chunks → Answer
```

---

## 🌐 Case 3: Real-time Question

```
User: "Latest news on AI"
```

Flow:

```
decide_webdata_needed → YES
→ search_web → merge → answer
```

---

## 📊 Case 4: Detailed Report

```
User selects "Detailed Report"
```

Flow:

```
Multi-stage pipeline → structured output
```

---

# 🔒 Security Notes

* JWT stored in HTTP-only cookie
* Session-based user tracking
* File isolation per user
* Data deleted on logout

---

# ⚠️ Limitations

* No rate limiting
* No file size scaling beyond 1MB
* Single-node deployment
* No async queue system (uses threads)

---

# 🚀 Future Improvements

* Add Redis queue for scaling
* Add streaming responses
* Add better UI state management
* Add multi-user concurrency control
* Improve vector DB filtering

---

# 🧠 Final Insight

This system is powerful because it:

* Does **not blindly use RAG**
* Does **not always use web**
* Makes **intelligent decisions dynamically**

That is what makes it **agentic**.

---

# ✅ Summary

SeekInfo is:

✔ Hybrid AI system
✔ Context-aware chatbot
✔ Retrieval + Web + Memory system
✔ Explainable (citations)
✔ Modular agent pipeline

---

If you want, next step we can do:
👉 Draw architecture diagram
👉 Optimize agent graph
👉 Improve RAG decision logic (very important for interviews)

Just tell me.
