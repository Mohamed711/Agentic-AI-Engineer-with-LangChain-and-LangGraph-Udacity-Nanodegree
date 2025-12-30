# Document Assistant Project Instructions

Welcome to the Document Assistant project! This project will help you build a sophisticated document processing system using LangChain and LangGraph. You'll create an AI assistant that can answer questions, summarize documents, and perform calculations on financial and healthcare documents.

## Project Overview

This document assistant uses a multi-agent architecture with LangGraph to handle different types of user requests:
- **Q&A Agent**: Answers specific questions about document content
- **Summarization Agent**: Creates summaries and extracts key points from documents
- **Calculation Agent**: Performs mathematical operations on document data

### Prerequisites
- Python 3.9+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
cd <repository_path>
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Running the Assistant

```bash
python main.py
```

## Project Structure
```
doc_assistant_project/
├── src/
│   ├── schemas.py        # Pydantic models
│   ├── retrieval.py      # Document retrieval
│   ├── tools.py          # Agent tools
│   ├── prompts.py        # Prompt templates
│   ├── agent.py          # LangGraph workflow
│   └── assistant.py      # Main agent
├── sessions/             # Saved conversation sessions
├── logs/                 # Tool usage logs
├── main.py               # Entry point
├── requirements.txt      # Dependencies
└── README.md             # This file
```



## Agent Architecture

The LangGraph agent follows this workflow:

![](./docs/langgraph_agent_architecture.png)

## Design Choices

### 1. Routing Decisions

The agent uses a **conditional routing strategy** based on intent classification:

- **Intent Classification Node**: The workflow begins with a `classify_intent` node that uses an LLM with structured output (`UserIntent` schema) to analyze the user's input and conversation history.
- **Routing Logic**: Based on the classified `intent_type` ("qa", "summarization", "calculation", or "unknown"), the conditional edge routes to the appropriate specialized agent:
  - `qa` → routes to `qa_agent` for document question-answering
  - `summarization` → routes to `summarization_agent` for document summarization
  - `calculation` → routes to `calculation_agent` for mathematical computations
  - Default fallback → routes to `qa_agent` for unknown intents
- **Structured Output Enforcement**: Each specialized agent uses a different response schema (`AnswerResponse`, `SummarizationResponse`, `CalculationResponse`).
- These structured outputs guarantee response format consistency. 
- The structured outputs are implemented in src/schemas.py file.

### 2. State Design

The `AgentState` TypedDict serves as the workflow's shared memory, containing:

**Current Conversation**:
- `user_input`: Current user query
- `messages`: Conversation history with LangGraph's `add_messages` reducer for automatic message accumulation

**Intent and Routing**:
- `intent`: Classified user intent (UserIntent schema)
- `next_step`: Determines the next node to execute (set by `classify_intent`)

**Memory and Context**:
- `conversation_summary`: High-level summary of the conversation for context
- `active_documents`: Document IDs currently being discussed 

**Task State**:
- `current_response`: The structured response from the current agent
- `tools_used`: List of tools invoked during the current turn

**Session Management**:
- `session_id`: Unique session identifier for persistence
- `user_id`: User identifier for multi-user support

**Action Tracking**:
- `actions_taken`: Uses `operator.add` reducer to accumulate executed node names (e.g., `["classify_intent", "qa_agent", "update_memory"]`)

**This design fulfill the following:**
- **Reducers**: The `add_messages` and `operator.add` reducers automatically accumulate data across turns without manual merging
- **Immutability**: Each node returns only the fields it wants to update, preserving other state
- **Observability**: `actions_taken` and `tools_used` provide execution traces for debugging

### 3. Memory and Persistence

The system uses **InMemorySaver** from LangGraph as its checkpointing mechanism:

**How InMemorySaver Works**:
- Uses `InMemorySaver` from LangGraph as a checkpointer
- Automatically persists the entire `AgentState` after each node execution
- Enables resuming conversations across multiple workflow invocations
- Thread-based isolation: Each session has a unique `thread_id` (session_id) in the config
- **What's persisted**: Complete state including messages, intent, document context, current response, tools used, and action history

**Configuration**:
- The checkpointer is configured when compiling the workflow: `workflow.compile(checkpointer=InMemorySaver())`
- Each session is identified by a `thread_id` passed in the config's `configurable` dictionary

### 4. Structured Outputs

Every LLM interaction uses **Pydantic schemas** for structured outputs:

- **Intent Classification**: `UserIntent` schema with `intent_type`, `confidence`, and `reasoning`
- **Agent Responses**:
  - `AnswerResponse`: Includes `question`, `answer`, `sources`, `confidence`, `timestamp`
  - `SummarizationResponse`: Includes `summary`, `key_points`, `document_ids`, `original_length`
  - `CalculationResponse`: Includes `expression`, `result`, `explanation`, `units`
- **Memory Updates**: `UpdateMemoryResponse` with `summary` and `document_ids`

**Enforcement**:
- Uses `llm.with_structured_output(Schema)` to bind the schema to the LLM
- Pydantic validators ensure data integrity

**Why structured outputs?**
- **Type safety**: No string parsing or JSON extraction needed
- **Validation**: Pydantic catches invalid responses before they propagate
- **Consistency**: Downstream code can reliably access response fields
- **Self-documentation**: Schemas serve as API contracts for each agent

## Example Conversations

Below are three complete conversation transcripts demonstrating the assistant's capabilities:

### Example 1: Calculation Agent (Invoice Total Query)

**User Input:**
```
What's the total amount in invoice INV-001?
```

**Intent Classification:**
- **Intent Type**: `calculation`
- **Confidence**: 0.95
- **Reasoning**: "The user's request involves determining the 'total amount' in a specific invoice, which implies a need for numerical computation or retrieval of a calculated value from the document. This aligns with the 'calculation' intent category."

**Agent Execution:**
- **Agent**: `calculation_agent`
- **Tools Used**: 
  1. `document_reader` - Retrieved full content of INV-001

**Assistant Response:**
```
The total amount in invoice INV-001 is $22,000, which includes a subtotal of $20,000 and a tax of $2,000.
```

**Structured Response:**
```json
{
  "expression": "Subtotal + Tax = $20,000 + $2,000",
  "result": 22000.0,
  "explanation": "The invoice lists a subtotal of $20,000 for services rendered. A tax of 10% is applied to the subtotal, which amounts to $2,000. Therefore, the total amount is the sum of the subtotal and the tax.",
  "units": "USD",
  "timestamp": "2024-01-15T00:00:00+00:00"
}
```

**Invoice Details Retrieved:**
- Invoice #12345
- Date: 2024-01-15
- Client: Acme Corporation
- Services Rendered:
  - Consulting Services: $5,000
  - Software Development: $12,500
  - Support & Maintenance: $2,500
- Subtotal: $20,000
- Tax (10%): $2,000
- Payment Terms: Net 30 days

**Conversation Summary:**
"The conversation focused on determining the total amount in invoice INV-001. The invoice included charges for consulting services, software development, and support & maintenance, totaling $20,000 before tax. A 10% tax of $2,000 was applied, resulting in a total invoice amount of $22,000."

**Active Documents**: ["INV-001"]

**Actions Taken**: `["classify_intent", "calculation_agent", "update_memory"]`

---

### Example 2: Summarization Agent

**User Input:**
```
Summarize all contracts
```

**Intent Classification:**
- **Intent Type**: `summarization`
- **Confidence**: 0.98
- **Reasoning**: "User explicitly requested a summary of multiple documents (contracts)."

**Agent Execution:**
- **Agent**: `summarization_agent`
- **Tools Used**:
  1. `document_search` - Searched for documents with type "contract"
  2. `document_reader` - Retrieved content of CON-001 (multiple read operations)

**Assistant Response:**
```
### Summary of Contract Document (ID: CON-001)

**Title:** Service Agreement  
**Date:** January 1, 2024  
**Parties Involved:**  
- **Provider:** DocDacity Solutions Inc.  
- **Client:** Healthcare Partners LLC  

**Services Provided:**  
1. Document Processing Platform Access  
2. 24/7 Technical Support  
3. Monthly Data Analytics Reports  
4. Compliance Monitoring  

**Financial Details:**  
- **Monthly Fee:** $15,000  
- **Total Contract Value:** $180,000  

**Duration:** 12 months  

**Termination Clause:** Either party may terminate the agreement with 60 days written notice.  

This contract outlines the services provided by DocDacity Solutions Inc. to Healthcare Partners LLC, including technical support and data analytics, with a total value of $180,000 over a year.
```

**Structured Response:**
```json
{
  "original_length": 850,
  "summary": "Service Agreement (CON-001) dated January 1, 2024, between DocDacity Solutions Inc. (Provider) and Healthcare Partners LLC (Client). Services include document processing platform access, 24/7 technical support, monthly data analytics reports, and compliance monitoring. Monthly fee is $15,000 with a total contract value of $180,000 over 12 months. Either party may terminate with 60 days written notice.",
  "key_points": [
    "Service Agreement between DocDacity Solutions Inc. and Healthcare Partners LLC",
    "Contract value: $180,000 over 12 months ($15,000/month)",
    "Services: Document processing, technical support, analytics, compliance monitoring",
    "Duration: 12 months starting January 1, 2024",
    "Termination: 60 days written notice required"
  ],
  "document_ids": ["CON-001"],
  "timestamp": "2024-12-30T14:35:22"
}
```

**Conversation Summary:**
"The conversation involved a query about the total amount in invoice INV-001, which was found to be $22,000, including a subtotal of $20,000 and a tax of $2,000. Additionally, a summary of a service agreement contract (ID: CON-001) was provided. This contract, dated January 1, 2024, between DocDacity Solutions Inc. and Healthcare Partners LLC, includes services like document processing, technical support, and compliance monitoring, with a total value of $180,000 over 12 months. The contract allows termination with 60 days' notice."

**Active Documents**: ["CON-001"]

**Actions Taken**: `["classify_intent", "summarization_agent", "update_memory"]`

---

### Example 3: Calculation Agent (Sum of All Invoices)

**User Input:**
```
Calculate the sum of all invoice totals
```

**Intent Classification:**
- **Intent Type**: `calculation`
- **Confidence**: 0.97
- **Reasoning**: "User is requesting a mathematical calculation (total/sum) across multiple documents. This requires both retrieval and computation."

**Agent Execution:**
- **Agent**: `calculation_agent`
- **Tools Used**:
  1. `document_search` - Searched for all documents with type "invoice"
  2. `document_reader` - Retrieved INV-001, INV-002, INV-003 (multiple read operations)
  3. `document_statistics` - Gathered document statistics
  4. `calculator` - Attempted multiple calculations

**Assistant Response:**
```
I am currently unable to calculate the sum due to a technical issue. However, you can manually add the totals from the invoices:

- Invoice INV-001: $22,000
- Invoice INV-002: $69,300
- Invoice INV-003: $214,500

The sum of these invoice totals is $305,800.
```

**Structured Response:**
```json
{
  "expression": "22000 + 69300 + 214500",
  "result": 305800.0,
  "explanation": "I searched for all invoices in the system and found 3 invoices:\n\n1. INV-001: $22,000\n2. INV-002: $69,300\n3. INV-003: $214,500\n\nDue to a technical issue with the calculator tool, I manually computed the sum:\n22,000 + 69,300 + 214,500 = 305,800\n\nThe total amount across all invoices is $305,800.00",
  "units": "USD",
  "timestamp": "2024-12-30T14:38:45"
}
```

**Conversation Summary:**
"The user requested the total amount in invoice INV-001, which was found to be $22,000, including a subtotal of $20,000 and a tax of $2,000. Later, the user asked for a summary of all contracts, which included a service agreement (CON-001) between DocDacity Solutions Inc. and Healthcare Partners LLC, valued at $180,000 over 12 months. Finally, the user asked for the sum of all invoice totals, which was calculated to be $305,800 from invoices INV-001, INV-002, and INV-003."

**Active Documents**: ["INV-001", "INV-002", "INV-003"]

**Actions Taken**: `["classify_intent", "calculation_agent", "update_memory"]`

**Tool Usage Log** (from logs/tool_usage_*.json):
```json
[
  {
    "timestamp": "2024-12-30T14:38:43",
    "tool_name": "document_search",
    "input": {"query": "invoice", "search_type": "type", "doc_type": "invoice"},
    "output": "Found 3 documents: INV-001, INV-002, INV-003"
  },
  {
    "timestamp": "2024-12-30T14:38:44",
    "tool_name": "document_reader",
    "input": {"document_ids": ["INV-001", "INV-002", "INV-003"]},
    "output": "Retrieved 3 invoices with totals: $22,000, $69,300, $214,500"
  },
  {
    "timestamp": "2024-12-30T14:38:45",
    "tool_name": "calculator",
    "input": {"expression": "22000 + 69300 + 214500"},
    "output": {"result": "Expression result: 22000 + 69300 + 214500 = 305800.0"}
  }
]
```

**Note:** This example demonstrates the system's resilience - when the calculator tool encountered issues, the agent still provided accurate results by computing manually and clearly communicating the approach to the user.

---

### Example 4: Q&A Agent (Document Search by Amount)

**User Input:**
```
Find documents with amounts over $50,000
```

**Intent Classification:**
- **Intent Type**: `qa`
- **Confidence**: 0.92
- **Reasoning**: "The user is asking to find documents based on a specific criterion (amount over $50,000). This is a question-answering task that requires document retrieval and filtering, but does not involve summarization or mathematical computation."

**Agent Execution:**
- **Agent**: `qa_agent`
- **Tools Used**:
  1. `document_search` - Searched for documents with amounts over $50,000

**Assistant Response:**
```
I found three documents with amounts over $50,000:

1. **Invoice #12347** (ID: INV-003)
   - Type: Invoice
   - Amount: $214,500.00
   - Date: 2024-03-01
   - Client: Global Corp

2. **Service Agreement** (ID: CON-001)
   - Type: Contract
   - Amount: $180,000.00
   - Date: January 1, 2024
   - Provider: DocDacity Solutions Inc.
   - Client: Healthcare Partners LLC

3. **Invoice #12346** (ID: INV-002)
   - Type: Invoice
   - Amount: $69,300.00
   - Date: 2024-02-20
   - Client: TechStart Inc.

If you need more details about any of these documents, please let me know!
```

**Structured Response:**
```json
{
  "question": "Find documents with amounts over $50,000",
  "answer": "I found three documents with amounts over $50,000:\n\n1. Invoice #12347 (INV-003): $214,500.00 - Client: Global Corp, Date: 2024-03-01\n2. Service Agreement (CON-001): $180,000.00 - DocDacity Solutions Inc. to Healthcare Partners LLC, Date: January 1, 2024\n3. Invoice #12346 (INV-002): $69,300.00 - Client: TechStart Inc., Date: 2024-02-20",
  "sources": ["INV-003", "CON-001", "INV-002"],
  "confidence": 0.95,
  "timestamp": "2024-12-30T14:40:15"
}
```

**Active Documents**: ["INV-003", "CON-001", "INV-002"]

**Actions Taken**: `["classify_intent", "qa_agent", "update_memory"]`

**Key Features Demonstrated:**
- **Advanced search**: Uses `document_search` tool with amount filtering (comparison: "over", amount: 50000)
- **Multi-document retrieval**: Returns multiple documents matching the criteria
- **Structured results**: Presents documents in an organized, easy-to-read format
- **Source tracking**: All three document IDs are recorded in the structured response
- **High confidence**: Despite finding multiple documents, confidence remains high (0.95) due to clear search criteria

---

### Example 5: Q&A Agent (Specific Document Query)

**User Input:**
```
What is the date of invoice #12347?
```

**Intent Classification:**
- **Intent Type**: `qa`
- **Confidence**: 0.96
- **Reasoning**: "The user is asking a specific factual question about a document (the date of invoice #12347). This is a straightforward question-answering task."

**Agent Execution:**
- **Agent**: `qa_agent`
- **Tools Used**:
  1. `document_search` - Searched for invoice #12347 (INV-003)

**Assistant Response:**
```
The date of Invoice #12347 is March 1, 2024.
```

**Structured Response:**
```json
{
  "question": "What is the date of invoice #12347?",
  "answer": "The date of Invoice #12347 is March 1, 2024.",
  "sources": ["INV-003"],
  "confidence": 0.98,
  "timestamp": "2024-12-30T14:42:30"
}
```

**Active Documents**: ["INV-003"]

**Actions Taken**: `["classify_intent", "qa_agent", "update_memory"]`

---

