# Comtrade Benchmark Architecture Guide

**For Beginners: Understanding the Complete Program Flow**

This guide provides a detailed walkthrough of the entire Comtrade Benchmark system, explaining every component, how they interact, and the principles behind the design. By the end, you'll understand the complete flow from task definition to scoring.

---

## Table of Contents

1. [High-Level Overview](#high-level-overview)
2. [The Three Repositories](#the-three-repositories)
3. [Core Concepts](#core-concepts)
4. [System Architecture](#system-architecture)
5. [Component Deep Dive](#component-deep-dive)
6. [Data Flow: From Task to Score](#data-flow-from-task-to-score)
7. [File-by-File Breakdown](#file-by-file-breakdown)
8. [Key Programming Patterns](#key-programming-patterns)
9. [How to Extend the System](#how-to-extend-the-system)

---

## High-Level Overview

### What is This System?

This is a **benchmark evaluation framework** for testing AI agents that need to extract and process international trade data from the UN Comtrade API. The system:

1. **Simulates** a real API with deliberate faults (pagination issues, duplicates, HTTP errors)
2. **Challenges** agents to extract clean, accurate data despite these faults
3. **Evaluates** agent performance across 6 dimensions: correctness, completeness, robustness, efficiency, data quality, and observability
4. **Integrates** with the AgentBeats platform for standardized agent evaluation

### Why Does It Exist?

In real-world scenarios, AI agents must handle:
- **Imperfect APIs**: Pagination bugs, rate limits, server errors
- **Data Quality Issues**: Duplicates, missing values, inconsistencies
- **Resource Constraints**: API call limits, time constraints

This benchmark tests whether an agent can reliably extract accurate data despite these challenges.

---

## The Three Repositories

### 1. **green-comtrade-bench** (The Judge)
- **Role**: Defines tasks, runs the mock API, evaluates agent outputs
- **Path**: `/Users/sarah/Desktop/Antigravity/TEST/green-comtrade-bench`
- **Key Insight**: This is the "examiner" - it creates the test, provides the environment, and grades the results

### 2. **purple-comtrade-baseline-v2** (The Baseline Agent)
- **Role**: A reference implementation that shows how to solve the tasks
- **Path**: `/Users/sarah/Desktop/Antigravity/TEST/purple-comtrade-baseline-v2`
- **Key Insight**: This is the "example student" - it demonstrates one way to pass the exam

### 3. **agentbeats-leaderboard** (The Orchestrator)
- **Role**: Generates docker-compose configurations to run benchmarks, records results
- **Path**: `/Users/sarah/Desktop/Antigravity/TEST/agentbeats-leaderboard`
- **Key Insight**: This is the "test administrator" - it sets up the exam room and records scores

---

## Core Concepts

### 1. Agent-to-Agent (A2A) Protocol

**What it is**: A JSON-RPC 2.0 communication standard over HTTP that allows agents to interact with judges without tight coupling.

**Why it matters**: Instead of importing Python modules directly, agents and judges communicate via HTTP POST requests. This allows:
- Agents written in any language (Python, JavaScript, Go)
- Containerized isolation (each component in its own Docker container)
- Standardized interface (follows a2a-sdk specifications)

**Example Communication**:
```json
// Request from AgentBeats client to Green Judge
{
  "jsonrpc": "2.0",
  "method": "task.init",
  "params": {"task_id": "T2_duplicate_records"},
  "id": 1
}

// Response from Green Judge
{
  "jsonrpc": "2.0",
  "result": {
    "mock_api_url": "http://mock-comtrade:8000",
    "max_api_calls": 20
  },
  "id": 1
}

// Request from AgentBeats client to Purple Agent
{
  "jsonrpc": "2.0",
  "method": "agent.invoke",
  "params": {"task_input": {"mock_api_url": "...", ...}},
  "id": 2
}

// Response from Purple Agent with solution
{
  "jsonrpc": "2.0",
  "result": {
    "total_trade_value_usd": 1234567890.50,
    "record_count": 150,
    "api_calls_made": 8
  },
  "id": 2
}
```

**Key Files**:
- `green-comtrade-bench/agent_a2a.py`: Green agent A2A handler
- `purple-comtrade-baseline-v2/run_a2a.py`: Purple agent A2A server

### 2. The Seven Tasks (T1-T7)

Each task represents a progressively harder challenge:

| Task | Name | Fault Injected | Difficulty |
|------|------|---------------|------------|
| T1 | Basic Pagination | Standard pagination (page_size=100) | ⭐ Baseline |
| T2 | Duplicate Records | 10% of records randomly duplicated | ⭐⭐ Deduplication required |
| T3 | HTTP 429 Rate Limit | 20% requests fail with 429 | ⭐⭐⭐ Retry logic needed |
| T4 | HTTP 500 Server Error | 15% requests fail with 500 | ⭐⭐⭐ Error handling needed |
| T5 | Page Drift | Page contents change between calls | ⭐⭐⭐⭐ Cursor-based pagination |
| T6 | Totals Trap | API returns fake totals_available | ⭐⭐⭐⭐⭐ Don't trust metadata |
| T7 | Combined Chaos | All faults active simultaneously | ⭐⭐⭐⭐⭐ Ultimate test |

**Key Insight**: Tasks are **not real UN Comtrade data**. They use:
- Deterministic random number generator (RNG) seeded by task_id
- Pre-generated fixture data (countries, commodities, years) in `fixtures/`
- Controlled fault injection to ensure reproducibility

**Key File**: `green-comtrade-bench/tasks.py` - Defines all task configurations

### 3. The Six Scoring Dimensions

Each agent output is scored 0-100 across six dimensions:

#### **Correctness** (max 30 points)
- **What**: Is `total_trade_value_usd` accurate?
- **Formula**: `30 * (1 - |agent_value - true_value| / true_value)` with 5% tolerance
- **Why it matters**: The most critical metric - did the agent get the right answer?

#### **Completeness** (max 15 points)
- **What**: Did the agent retrieve all records?
- **Formula**: `15 * (agent_record_count / true_record_count)`
- **Why it matters**: Missing data leads to wrong conclusions

#### **Robustness** (max 15 points)
- **What**: Did the agent handle errors without crashing?
- **Formula**: `15` if no exceptions, `0` if crashed
- **Why it matters**: Production systems must handle failures gracefully

#### **Efficiency** (max 15 points)
- **What**: Did the agent minimize API calls?
- **Formula**: `15 * (min_required_calls / agent_api_calls)` capped at 15
- **Why it matters**: Real APIs have rate limits and costs

#### **Data Quality** (max 15 points)
- **What**: Did the agent remove duplicates?
- **Formula**: `15 * (1 - duplicate_rate)` where duplicate_rate = duplicates / total_records
- **Why it matters**: Dirty data corrupts analytics

#### **Observability** (max 10 points)
- **What**: Did the agent provide transparency into its process?
- **Formula**: Points for `api_calls_made` (+3), `duplicate_count` (+3), `errors_encountered` (+4)
- **Why it matters**: Debugging and auditing require visibility

**Total Score**: Sum of all dimensions = 0-100 per task

**Key File**: `green-comtrade-bench/judge.py` - Implements all scoring logic

### 4. Governance Gates (Anti-Gaming Rules)

The judge enforces two critical rules to prevent agents from "gaming" the system:

#### **Completeness Gate**
```python
if score_breakdown["completeness"] < 14.0:  # Less than 93% complete
    score_breakdown["correctness"] = 0  # Zero out correctness
```
**Why**: An agent shouldn't get correctness points if it only retrieved 10% of records and got lucky.

#### **Correctness Gate**
```python
if score_breakdown["correctness"] < 1.0:  # Essentially wrong answer
    score_breakdown["data_quality"] = 0  # Zero out data quality
```
**Why**: Data quality doesn't matter if the final answer is completely wrong.

**Key Insight**: These gates ensure that agents must solve the **entire problem**, not just optimize for one dimension.

---

## System Architecture

### Deployment View (Docker Compose)

When you run the benchmark, four containers start:

```
┌─────────────────────────────────────────────────────────┐
│  agentbeats-client (orchestrator)                       │
│  - Sends task.init to green-agent                       │
│  - Sends agent.invoke to purple-agent                   │
│  - Collects results and saves to results/*.json         │
└─────────────────────────────────────────────────────────┘
                 │                      │
                 │ A2A JSON-RPC         │ A2A JSON-RPC
                 ▼                      ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│  green-agent (judge)     │  │  purple-agent (solution) │
│  Port: 8001              │  │  Port: 8002              │
│  - task.init             │  │  - agent.invoke          │
│  - task.score            │  │  - Returns solution JSON │
└──────────────────────────┘  └──────────────────────────┘
         │                               │
         │ Provides mock_api_url         │ Makes GET requests
         ▼                               │
┌──────────────────────────┐            │
│  mock-comtrade (mock)    │◄───────────┘
│  Port: 8000              │
│  - GET /api/comtrade     │
│  - Injects faults        │
└──────────────────────────┘
```

**Key Insight**: Each container is isolated. Communication only happens via:
1. A2A HTTP requests (port 8001, 8002)
2. Mock API HTTP requests (port 8000)

### Sequence Diagram: One Task Execution

```
agentbeats-client     green-agent          mock-comtrade      purple-agent
       │                   │                      │                 │
       │  task.init(T2)    │                      │                 │
       ├──────────────────>│                      │                 │
       │                   │  [Initialize mock]   │                 │
       │                   ├─────────────────────>│                 │
       │                   │◄─────────────────────┤                 │
       │  task_input       │                      │                 │
       │<──────────────────┤                      │                 │
       │                   │                      │                 │
       │  agent.invoke(task_input)                │                 │
       ├────────────────────────────────────────────────────────────>│
       │                   │                      │                 │
       │                   │                      │  GET /api?page=1│
       │                   │                      │<────────────────┤
       │                   │                      │  {data:[...]}   │
       │                   │                      ├────────────────>│
       │                   │                      │                 │
       │                   │                      │  GET /api?page=2│
       │                   │                      │<────────────────┤
       │                   │                      │  {data:[...]}   │
       │                   │                      ├────────────────>│
       │                   │                      │                 │
       │                   │                      │    ... (more)   │
       │                   │                      │                 │
       │  solution_output  │                      │                 │
       │<────────────────────────────────────────────────────────────┤
       │                   │                      │                 │
       │  task.score(solution_output)             │                 │
       ├──────────────────>│                      │                 │
       │                   │  [Compute scores]    │                 │
       │  scores           │                      │                 │
       │<──────────────────┤                      │                 │
       │                   │                      │                 │
```

**Key Steps**:
1. **task.init**: Green agent prepares the task, returns task_input (includes mock_api_url, max_api_calls)
2. **agent.invoke**: Purple agent receives task_input, calls mock API repeatedly, returns solution
3. **task.score**: Green agent compares solution to ground truth, returns scores

---

## Component Deep Dive

### Mock Comtrade Service

**Location**: `green-comtrade-bench/mock_service/app.py`

**Purpose**: Simulates the UN Comtrade API with controllable faults.

**Key Functions**:

#### 1. `GET /api/comtrade` - Main API Endpoint
```python
@app.get("/api/comtrade")
async def get_comtrade_data(
    reporter: str,
    partner: str,
    cmdCode: str,
    year: int,
    page: Optional[int] = 1,
    page_size: Optional[int] = 100,
):
    # Load task config
    # Generate base records using seeded RNG
    # Apply fault injection (duplicates, errors, page drift)
    # Return paginated response
```

**Fault Injection Logic**:
- **Duplicates** (T2): After generating clean records, randomly select 10% and duplicate them
- **HTTP 429** (T3): `if rng.random() < 0.20: raise HTTPException(429)`
- **HTTP 500** (T4): `if rng.random() < 0.15: raise HTTPException(500)`
- **Page Drift** (T5): Re-seed RNG with `seed + page` to make each page different on each request
- **Totals Trap** (T6): Return `totals_available = 999999` instead of true count

**Key Insight**: The mock service is **stateless** - it regenerates data on every request using a seeded RNG. This ensures:
- **Reproducibility**: Same task_id always generates same data
- **No persistence needed**: No database required
- **Fast reset**: New task_id = completely fresh environment

#### 2. `POST /reset` - Task Initialization
```python
@app.post("/reset")
async def reset_task(config: TaskConfig):
    # Store task config in global TASK_REGISTRY
    # Seed RNG with task_id hash
```

**Key Insight**: Green agent calls this endpoint during `task.init` to configure the mock service for a specific task.

### Green Judge

**Location**: `green-comtrade-bench/judge.py`

**Purpose**: Orchestrates task execution and scoring.

**Key Class**: `ComtradeBenchJudge`

#### Method 1: `init_task(task_id: str) -> dict`
```python
def init_task(self, task_id: str) -> dict:
    # 1. Load task config from tasks.py
    # 2. Generate ground truth data using same RNG seed
    # 3. Store ground truth for later scoring
    # 4. Send task config to mock service via POST /reset
    # 5. Return task_input with mock_api_url, max_api_calls, etc.
```

**Critical Detail**: Ground truth generation uses **identical logic** to mock service's data generation:
```python
# Both use:
rng = random.Random(seed)
for _ in range(record_count):
    reporter_code = rng.choice(countries)["code"]
    partner_code = rng.choice(countries)["code"]
    # ... generate trade_value_usd
```

This ensures that judge and mock service have **synchronized expectations**.

#### Method 2: `score_output(task_id: str, agent_output: dict) -> dict`
```python
def score_output(self, task_id: str, agent_output: dict) -> dict:
    # 1. Retrieve ground truth for task_id
    # 2. Extract agent values: total_trade_value_usd, record_count, etc.
    # 3. Compute 6-dimensional scores
    # 4. Apply governance gates
    # 5. Return score_breakdown and score_total
```

**Scoring Steps**:
1. **Correctness**: `abs(agent_total - true_total) / true_total` with 5% tolerance
2. **Completeness**: `agent_record_count / true_record_count`
3. **Robustness**: Check if agent raised exception
4. **Efficiency**: `min_required_api_calls / agent_api_calls`
5. **Data Quality**: `1 - (agent_duplicate_count / agent_record_count)`
6. **Observability**: Count presence of `api_calls_made`, `duplicate_count`, `errors_encountered` fields

**Key Insight**: The judge is **stateful** - it stores ground truth during `init_task` and retrieves it during `score_output`. This is why task_id must be unique.

### Green A2A Handler

**Location**: `green-comtrade-bench/agent_a2a.py`

**Purpose**: Wraps the judge in an A2A-compatible HTTP server.

**Key Functions**:

#### 1. `handle_task_init(params: dict) -> dict`
```python
@app.post("/a2a")
async def a2a_endpoint(request: Request):
    body = await request.json()
    if body["method"] == "task.init":
        result = judge.init_task(body["params"]["task_id"])
        return {"jsonrpc": "2.0", "result": result, "id": body["id"]}
    elif body["method"] == "task.score":
        result = judge.score_output(
            body["params"]["task_id"],
            body["params"]["solution_output"]
        )
        return {"jsonrpc": "2.0", "result": result, "id": body["id"]}
```

**Key Insight**: This is a thin wrapper that:
- Receives JSON-RPC 2.0 requests on port 8001
- Routes `task.init` → `judge.init_task()`
- Routes `task.score` → `judge.score_output()`
- Returns JSON-RPC 2.0 responses

**Why separate files?**
- `judge.py` = Pure Python logic (can be imported and tested directly)
- `agent_a2a.py` = HTTP server wrapper (only needed for A2A protocol)

### Purple Baseline Agent

**Location**: `purple-comtrade-baseline-v2/purple_agent.py`

**Purpose**: Demonstrates a working solution to all 7 tasks.

**Key Class**: `PurpleAgent`

#### Method 1: `solve_task(task_input: dict) -> dict`
```python
def solve_task(self, task_input: dict) -> dict:
    # Extract task parameters
    mock_api_url = task_input["mock_api_url"]
    max_api_calls = task_input.get("max_api_calls", 100)

    # Call API with pagination
    all_records = []
    page = 1
    while True:
        response = self.call_api(mock_api_url, page)
        all_records.extend(response["data"])
        if not response.get("next_page"):
            break
        page += 1

    # Deduplicate records
    unique_records = self.deduplicate(all_records)

    # Compute total trade value
    total_trade_value_usd = sum(r["trade_value_usd"] for r in unique_records)

    # Return solution
    return {
        "total_trade_value_usd": total_trade_value_usd,
        "record_count": len(unique_records),
        "api_calls_made": page,
        "duplicate_count": len(all_records) - len(unique_records),
        "errors_encountered": self.error_count
    }
```

**Key Strategies**:

1. **Pagination Handling**: Loop until `next_page` is null
2. **Retry Logic**: Exponential backoff for HTTP 429/500
   ```python
   def call_api(self, url, page, retries=5):
       for attempt in range(retries):
           try:
               response = requests.get(url, params={"page": page})
               if response.status_code == 429:
                   time.sleep(2 ** attempt)  # 1s, 2s, 4s, 8s, 16s
                   continue
               return response.json()
           except Exception as e:
               if attempt == retries - 1:
                   raise
   ```
3. **Deduplication**: Use composite key `(reporter_code, partner_code, cmdCode, trade_value_usd)`
   ```python
   def deduplicate(self, records):
       seen = set()
       unique = []
       for r in records:
           key = (r["reporter_code"], r["partner_code"], r["cmdCode"], r["trade_value_usd"])
           if key not in seen:
               seen.add(key)
               unique.append(r)
       return unique
   ```
4. **Error Counting**: Track all exceptions in `self.error_count`
5. **Observability**: Return `api_calls_made`, `duplicate_count`, `errors_encountered`

**Key Insight**: Purple agent is **not perfect** - it scores ~87-90/100 on average. It demonstrates:
- Solid correctness and completeness
- Good robustness (catches errors)
- Reasonable efficiency (not over-optimized)
- Excellent observability (returns all metrics)

### Purple A2A Server

**Location**: `purple-comtrade-baseline-v2/run_a2a.py`

**Purpose**: Wraps purple agent in an A2A-compatible HTTP server.

```python
@app.post("/a2a")
async def a2a_endpoint(request: Request):
    body = await request.json()
    if body["method"] == "agent.invoke":
        agent = PurpleAgent()
        result = agent.solve_task(body["params"]["task_input"])
        return {"jsonrpc": "2.0", "result": result, "id": body["id"]}
```

**Key Insight**: Similar to green A2A handler, this is a thin wrapper:
- Receives `agent.invoke` requests on port 8002
- Instantiates `PurpleAgent()`
- Calls `agent.solve_task()`
- Returns solution as JSON-RPC 2.0 response

### AgentBeats Orchestrator

**Location**: `agentbeats-leaderboard/generate_compose.py`

**Purpose**: Generates docker-compose.yml files for different benchmark scenarios.

**Key Function**: `generate_compose(scenario_config: dict) -> str`
```python
def generate_compose(scenario_config):
    # 1. Read scenario.toml to get submission paths
    # 2. For each submission, create docker-compose services:
    #    - mock-comtrade (from green submission)
    #    - green-agent (from green submission)
    #    - purple-agent (from purple submission)
    #    - agentbeats-client (orchestrator)
    # 3. Set environment variables:
    #    - GREEN_A2A_URL=http://green-agent:8001/a2a
    #    - PURPLE_A2A_URL=http://purple-agent:8002/a2a
    #    - TASK_LIST=T1,T2,T3,T4,T5,T6,T7
    # 4. Write docker-compose.yml
```

**Key Insight**: This script is **run locally**, not in CI. It reads:
- `submissions/scenario-*.toml` (defines which green/purple submissions to test)
- Outputs `docker-compose.yml` files

Then, the GitHub Actions workflow (`.github/workflows/run-scenario.yml`) uses these generated files to run benchmarks.

### AgentBeats Client

**Built into agentbeats-client Docker image** (not in our repos)

**Purpose**: Executes the A2A protocol flow:
1. Call `task.init` on green agent for each task_id
2. Call `agent.invoke` on purple agent with task_input
3. Call `task.score` on green agent with solution_output
4. Save results to `results/{submission_id}-{timestamp}.json`

**Key Insight**: This is a **black box** from our perspective - we don't control its code. We just ensure our agents implement the A2A protocol correctly.

---

## Data Flow: From Task to Score

Let's trace the complete journey of **Task T2 (Duplicate Records)** through the system.

### Step 1: Local Development - Define the Task

**File**: `green-comtrade-bench/tasks.py`
```python
TASKS = {
    "T2_duplicate_records": {
        "task_id": "T2_duplicate_records",
        "reporter": "USA",
        "partner": "CHN",
        "cmdCode": "TOTAL",
        "year": 2020,
        "record_count": 150,
        "faults": {
            "duplicate_rate": 0.10
        }
    }
}
```

**What happens**: Developer specifies that T2 will have 150 records with 10% duplicates.

### Step 2: CI Trigger - GitHub Actions Starts

**File**: `agentbeats-leaderboard/.github/workflows/run-scenario.yml`

**What happens**: Developer pushes to `agentbeats-leaderboard` repo, triggering workflow:
```yaml
- name: Generate docker-compose.yml
  run: python generate_compose.py --scenario default

- name: Run benchmark
  run: docker-compose up --abort-on-container-exit
```

### Step 3: Container Startup - Four Services Launch

**Generated file**: `docker-compose.yml`

**What happens**: Docker starts 4 containers:
- `mock-comtrade` (port 8000)
- `green-agent` (port 8001)
- `purple-agent` (port 8002)
- `agentbeats-client` (orchestrator)

### Step 4: Task Initialization - Green Agent Prepares

**Triggered by**: agentbeats-client sends POST to `http://green-agent:8001/a2a`:
```json
{
  "jsonrpc": "2.0",
  "method": "task.init",
  "params": {"task_id": "T2_duplicate_records"},
  "id": 1
}
```

**Flow**:
1. `agent_a2a.py` receives request, routes to `judge.init_task("T2_duplicate_records")`
2. `judge.py` loads task config from `tasks.TASKS["T2_duplicate_records"]`
3. `judge.py` generates ground truth:
   ```python
   rng = random.Random(hash("T2_duplicate_records") % (2**32))
   true_records = []
   for i in range(150):
       reporter_code = rng.choice(countries)["code"]
       partner_code = rng.choice(countries)["code"]
       trade_value_usd = rng.uniform(1000, 1000000)
       true_records.append({
           "id": i,
           "reporter_code": reporter_code,
           "partner_code": partner_code,
           "cmdCode": "TOTAL",
           "trade_value_usd": trade_value_usd
       })
   true_total = sum(r["trade_value_usd"] for r in true_records)
   # Store: self.ground_truth["T2_duplicate_records"] = true_records
   ```
4. `judge.py` sends task config to mock service:
   ```python
   requests.post("http://mock-comtrade:8000/reset", json={
       "task_id": "T2_duplicate_records",
       "reporter": "USA",
       "faults": {"duplicate_rate": 0.10}
   })
   ```
5. `agent_a2a.py` returns task_input:
   ```json
   {
     "jsonrpc": "2.0",
     "result": {
       "task_id": "T2_duplicate_records",
       "mock_api_url": "http://mock-comtrade:8000/api/comtrade",
       "reporter": "USA",
       "partner": "CHN",
       "cmdCode": "TOTAL",
       "year": 2020,
       "max_api_calls": 20
     },
     "id": 1
   }
   ```

**Key State Changes**:
- **Green Judge Memory**: `ground_truth["T2_duplicate_records"]` = 150 clean records, `true_total` = $X
- **Mock Service Memory**: `TASK_REGISTRY["T2_duplicate_records"]` = task config with duplicate_rate=0.10

### Step 5: Agent Invocation - Purple Agent Solves

**Triggered by**: agentbeats-client sends POST to `http://purple-agent:8002/a2a`:
```json
{
  "jsonrpc": "2.0",
  "method": "agent.invoke",
  "params": {
    "task_input": {
      "mock_api_url": "http://mock-comtrade:8000/api/comtrade",
      "reporter": "USA",
      "partner": "CHN",
      "cmdCode": "TOTAL",
      "year": 2020,
      "max_api_calls": 20
    }
  },
  "id": 2
}
```

**Flow**:
1. `run_a2a.py` receives request, instantiates `PurpleAgent()`
2. `purple_agent.py` starts solving:
   ```python
   all_records = []
   page = 1
   api_calls = 0

   # Page 1 request
   response = requests.get("http://mock-comtrade:8000/api/comtrade", params={
       "reporter": "USA",
       "partner": "CHN",
       "cmdCode": "TOTAL",
       "year": 2020,
       "page": 1,
       "page_size": 100
   })
   api_calls += 1
   all_records.extend(response.json()["data"])  # 100 records (includes ~10 duplicates)

   # Page 2 request
   response = requests.get("...", params={"page": 2})
   api_calls += 1
   all_records.extend(response.json()["data"])  # 65 records (50 clean + ~15 duplicates)

   # Now all_records has ~165 records (150 clean + ~15 duplicates)

   # Deduplicate
   seen = set()
   unique_records = []
   duplicate_count = 0
   for r in all_records:
       key = (r["reporter_code"], r["partner_code"], r["cmdCode"], r["trade_value_usd"])
       if key not in seen:
           seen.add(key)
           unique_records.append(r)
       else:
           duplicate_count += 1

   # unique_records now has 150 records
   # duplicate_count = 15

   # Compute total
   agent_total = sum(r["trade_value_usd"] for r in unique_records)

   # Return solution
   return {
       "total_trade_value_usd": agent_total,
       "record_count": 150,
       "api_calls_made": 2,
       "duplicate_count": 15,
       "errors_encountered": 0
   }
   ```
3. `run_a2a.py` returns solution:
   ```json
   {
     "jsonrpc": "2.0",
     "result": {
       "total_trade_value_usd": 123456789.50,
       "record_count": 150,
       "api_calls_made": 2,
       "duplicate_count": 15,
       "errors_encountered": 0
     },
     "id": 2
   }
   ```

**Key Data**: Purple agent successfully:
- Retrieved all 150 clean records
- Detected and removed 15 duplicates
- Made only 2 API calls (efficient)
- Reported observability metrics

### Step 6: Scoring - Green Judge Evaluates

**Triggered by**: agentbeats-client sends POST to `http://green-agent:8001/a2a`:
```json
{
  "jsonrpc": "2.0",
  "method": "task.score",
  "params": {
    "task_id": "T2_duplicate_records",
    "solution_output": {
      "total_trade_value_usd": 123456789.50,
      "record_count": 150,
      "api_calls_made": 2,
      "duplicate_count": 15,
      "errors_encountered": 0
    }
  },
  "id": 3
}
```

**Flow**:
1. `agent_a2a.py` routes to `judge.score_output()`
2. `judge.py` retrieves ground truth:
   ```python
   true_total = self.ground_truth["T2_duplicate_records"]["true_total"]
   true_record_count = 150
   ```
3. `judge.py` computes scores:
   ```python
   # Correctness (max 30)
   error_rate = abs(123456789.50 - true_total) / true_total
   if error_rate <= 0.05:  # Within 5% tolerance
       correctness = 30.0 * (1 - error_rate / 0.05)
   else:
       correctness = 0.0
   # Assume error_rate = 0.01 (1%) → correctness = 30 * (1 - 0.01/0.05) = 30 * 0.8 = 24.0

   # Completeness (max 15)
   completeness = 15.0 * (150 / 150) = 15.0

   # Robustness (max 15)
   # No exception field in solution_output
   robustness = 15.0

   # Efficiency (max 15)
   # min_required = ceil(150 / 100) = 2 pages
   efficiency = 15.0 * (2 / 2) = 15.0

   # Data Quality (max 15)
   # duplicate_count=15, record_count=150 (after dedup)
   # Original record count = 150 + 15 = 165
   # duplicate_rate = 15 / 165 = 0.091
   data_quality = 15.0 * (1 - 0.091) = 13.6

   # Observability (max 10)
   # Has api_calls_made (+3), duplicate_count (+3), errors_encountered (+4)
   observability = 10.0

   # Apply governance gates
   # Completeness = 15.0 >= 14.0 → correctness not zeroed
   # Correctness = 24.0 >= 1.0 → data_quality not zeroed

   # Total
   total_score = 24.0 + 15.0 + 15.0 + 15.0 + 13.6 + 10.0 = 92.6
   ```
4. `agent_a2a.py` returns scores:
   ```json
   {
     "jsonrpc": "2.0",
     "result": {
       "score_breakdown": {
         "correctness": 24.0,
         "completeness": 15.0,
         "robustness": 15.0,
         "efficiency": 15.0,
         "data_quality": 13.6,
         "observability": 10.0
       },
       "score_total": 92.6
     },
     "id": 3
   }
   ```

**Key Insight**: Judge scoring is **deterministic** - same agent output always produces same scores.

### Step 7: Result Recording - Save to JSON

**Done by**: agentbeats-client writes to `results/yonghongzhang-io-20260128-120000.json`:
```json
{
  "submission_id": "yonghongzhang-io-20260128-120000",
  "timestamp": "2026-01-28T12:00:00Z",
  "participants": {
    "green-comtrade-bench": "yonghongzhang-io/green-comtrade-bench-v2:latest",
    "purple-comtrade-baseline-v2": "yonghongzhang-io/purple-comtrade-baseline-v2:latest"
  },
  "results": [
    [
      {
        "task_id": "T2_duplicate_records",
        "score_breakdown": {
          "correctness": 24.0,
          "completeness": 15.0,
          "robustness": 15.0,
          "efficiency": 15.0,
          "data_quality": 13.6,
          "observability": 10.0
        },
        "score_total": 92.6
      }
      // ... results for T1, T3, T4, T5, T6, T7
    ]
  ]
}
```

### Step 8: Leaderboard Display - DuckDB Queries

**File**: `green-comtrade-bench/agentbeats_leaderboard.sql`

**What happens**: AgentBeats platform runs DuckDB queries on all result files:
```sql
SELECT
    results.participants."purple-comtrade-baseline-v2" AS id,
    ROUND(AVG(r.score_total), 1) AS "Score",
    COUNT(*) AS "Tasks",
    CASE WHEN AVG(r.score_total) >= 80.0 THEN 'PASS' ELSE 'FAIL' END AS "Pass"
FROM results
CROSS JOIN UNNEST(results.results[1]) AS t(r)
GROUP BY results.participants."purple-comtrade-baseline-v2"
ORDER BY "Score" DESC;
```

**Output on AgentBeats**:
| id | Score | Tasks | Pass |
|----|-------|-------|------|
| yonghongzhang-io/purple-comtrade-baseline-v2:latest | 90.1 | 7 | PASS |

**Key Insight**: The leaderboard is **computed on-demand** by running SQL queries over all result JSON files. No database needed.

---

## File-by-File Breakdown

### green-comtrade-bench Repository

#### Core Files

**`tasks.py`** (142 lines)
- **Purpose**: Defines all 7 task configurations
- **Key Data Structure**:
  ```python
  TASKS = {
      "T1_basic_pagination": {
          "task_id": "T1_basic_pagination",
          "reporter": "USA",
          "partner": "CHN",
          "cmdCode": "TOTAL",
          "year": 2020,
          "record_count": 250,
          "faults": {}  # No faults
      },
      # ... T2 through T7
  }
  ```
- **Key Function**: `get_task(task_id: str) -> dict`
- **When it's used**: Called by `judge.init_task()` to load task config

**`judge.py`** (387 lines)
- **Purpose**: Implements scoring logic and ground truth generation
- **Key Class**: `ComtradeBenchJudge`
- **Key Methods**:
  - `init_task(task_id) -> dict`: Prepares task, returns task_input
  - `score_output(task_id, agent_output) -> dict`: Computes 6-dimensional scores
  - `_generate_ground_truth(task_config) -> dict`: Creates true records using seeded RNG
- **Key Variables**:
  - `self.ground_truth`: Dict storing true values for each task_id
  - `self.mock_service_url`: URL of mock-comtrade service
- **When it's used**: Called by A2A handler for task.init and task.score

**`agent_a2a.py`** (89 lines)
- **Purpose**: FastAPI server wrapping judge for A2A protocol
- **Key Route**: `POST /a2a`
- **Key Logic**:
  ```python
  if method == "task.init":
      return judge.init_task(params["task_id"])
  elif method == "task.score":
      return judge.score_output(params["task_id"], params["solution_output"])
  ```
- **When it's used**: Receives all A2A requests from agentbeats-client

**`agent.py`** (253 lines)
- **Purpose**: Non-A2A command-line interface for local testing
- **Key Function**: `main(task_id: str, agent_url: str)`
- **Flow**:
  ```python
  # 1. Initialize judge
  judge = ComtradeBenchJudge()
  task_input = judge.init_task(task_id)

  # 2. Call agent (if provided)
  if agent_url:
      response = requests.post(agent_url, json=task_input)
      agent_output = response.json()
  else:
      agent_output = None  # Manual testing mode

  # 3. Score output
  if agent_output:
      scores = judge.score_output(task_id, agent_output)
      print(scores)
  ```
- **When it's used**: `python agent.py --task T1_basic_pagination --agent http://localhost:8002/invoke`

#### Mock Service Files

**`mock_service/app.py`** (312 lines)
- **Purpose**: FastAPI mock Comtrade API with fault injection
- **Key Routes**:
  - `GET /api/comtrade`: Main data endpoint
  - `POST /reset`: Task initialization
- **Key State**: `TASK_REGISTRY = {}` (stores current task config)
- **Key Logic**:
  ```python
  # Generate records
  rng = random.Random(seed)
  records = generate_base_records(rng, config)

  # Inject duplicates (if T2)
  if "duplicate_rate" in config.faults:
      records = inject_duplicates(records, config.faults.duplicate_rate, rng)

  # Inject HTTP errors (if T3/T4)
  if "http_429_rate" in config.faults:
      if rng.random() < config.faults.http_429_rate:
          raise HTTPException(status_code=429)

  # Paginate
  page_size = request.page_size or 100
  start = (request.page - 1) * page_size
  end = start + page_size
  page_data = records[start:end]

  return {
      "data": page_data,
      "pagination": {
          "page": request.page,
          "page_size": page_size,
          "total_pages": ceil(len(records) / page_size),
          "next_page": request.page + 1 if end < len(records) else None
      }
  }
  ```
- **When it's used**: Purple agent calls `GET /api/comtrade` to fetch data

**`mock_service/Dockerfile`** (11 lines)
- **Purpose**: Containerizes mock service
- **Key Commands**:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

#### Fixture Data Files

**`fixtures/countries.json`** (200+ countries)
- **Purpose**: List of real country codes and names
- **Format**:
  ```json
  [
    {"code": "USA", "name": "United States"},
    {"code": "CHN", "name": "China"},
    {"code": "JPN", "name": "Japan"},
    ...
  ]
  ```
- **When it's used**: RNG samples from this list to generate reporter_code/partner_code

**`fixtures/commodities.json`** (100+ commodities)
- **Purpose**: HS commodity codes
- **Format**:
  ```json
  [
    {"code": "01", "description": "Live animals"},
    {"code": "84", "description": "Machinery and mechanical appliances"},
    ...
  ]
  ```

**`fixtures/years.json`**
- **Purpose**: Valid year range
- **Format**: `[2010, 2011, ..., 2023]`

#### Schema Files

**`schemas/task_input.json`**
- **Purpose**: JSON schema for task_input returned by task.init
- **Key Fields**:
  ```json
  {
    "type": "object",
    "properties": {
      "task_id": {"type": "string"},
      "mock_api_url": {"type": "string", "format": "uri"},
      "reporter": {"type": "string"},
      "partner": {"type": "string"},
      "cmdCode": {"type": "string"},
      "year": {"type": "integer"},
      "max_api_calls": {"type": "integer"}
    },
    "required": ["task_id", "mock_api_url", "reporter"]
  }
  ```

**`schemas/agent_output.json`**
- **Purpose**: JSON schema for agent solution
- **Key Fields**:
  ```json
  {
    "type": "object",
    "properties": {
      "total_trade_value_usd": {"type": "number"},
      "record_count": {"type": "integer"},
      "api_calls_made": {"type": "integer"},
      "duplicate_count": {"type": "integer"},
      "errors_encountered": {"type": "integer"}
    },
    "required": ["total_trade_value_usd", "record_count"]
  }
  ```

#### Script Files

**`scripts/gen_fixtures.py`**
- **Purpose**: Generates countries.json, commodities.json, years.json from real UN data
- **Usage**: `python scripts/gen_fixtures.py` (run once during development)

**`scripts/validate_purple_output.py`**
- **Purpose**: Validates purple agent output against schema
- **Usage**: `python scripts/validate_purple_output.py < output.json`

#### CI/CD Files

**`.github/workflows/publish-ghcr.yml`**
- **Purpose**: Builds and publishes Docker images to GitHub Container Registry
- **Trigger**: Push to main branch
- **Key Steps**:
  ```yaml
  - name: Build green-agent image
    run: docker build -t ghcr.io/${{ github.repository }}:latest .

  - name: Build mock-service image
    run: docker build -t ghcr.io/${{ github.repository }}/mock-service:latest ./mock_service

  - name: Push images
    run: |
      docker push ghcr.io/${{ github.repository }}:latest
      docker push ghcr.io/${{ github.repository }}/mock-service:latest
  ```

**`.github/workflows/test.yml`**
- **Purpose**: Runs unit tests on PRs
- **Key Steps**:
  ```yaml
  - run: pip install pytest
  - run: pytest tests/
  ```

#### Documentation Files

**`README.md`** (250+ lines)
- **Sections**:
  - Overview
  - Quick Start (docker-compose up)
  - Task Descriptions (T1-T7)
  - Scoring Methodology
  - A2A Protocol
  - System Requirements
  - Development Guide

**`SUBMISSION_ABSTRACT.txt`** (115 lines)
- **Sections**:
  - Motivation
  - Benchmark Design
  - Evaluation Methodology
  - A2A Protocol Integration
  - Reproducibility
  - Baseline Results
  - Key Contributions

**`ARCHITECTURE_GUIDE.md`** (This file!)

#### Docker Files

**`Dockerfile`** (Green agent container)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY agent.py agent_a2a.py judge.py tasks.py ./
COPY fixtures/ ./fixtures/
COPY schemas/ ./schemas/
EXPOSE 8001
CMD ["python", "agent_a2a.py"]
```

**`docker-compose.yml`** (Local development)
```yaml
services:
  mock-comtrade:
    build: ./mock_service
    ports:
      - "8000:8000"

  green-agent:
    build: .
    ports:
      - "8001:8001"
    environment:
      - MOCK_SERVICE_URL=http://mock-comtrade:8000

  purple-agent:
    image: ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2:latest
    ports:
      - "8002:8002"
```

### purple-comtrade-baseline-v2 Repository

#### Core Files

**`purple_agent.py`** (198 lines)
- **Purpose**: Implements the baseline solution strategy
- **Key Class**: `PurpleAgent`
- **Key Methods**:
  - `solve_task(task_input) -> dict`: Main entry point
  - `call_api(url, params, retries=5) -> dict`: API call with retry
  - `deduplicate(records) -> list`: Removes duplicates
  - `aggregate(records) -> float`: Sums trade values
- **Key Logic**:
  ```python
  def solve_task(self, task_input):
      # Extract parameters
      mock_api_url = task_input["mock_api_url"]
      reporter = task_input["reporter"]
      partner = task_input["partner"]
      cmdCode = task_input["cmdCode"]
      year = task_input["year"]
      max_api_calls = task_input.get("max_api_calls", 100)

      # Fetch all pages
      all_records = []
      page = 1
      api_calls = 0
      errors = 0

      while api_calls < max_api_calls:
          try:
              response = self.call_api(mock_api_url, {
                  "reporter": reporter,
                  "partner": partner,
                  "cmdCode": cmdCode,
                  "year": year,
                  "page": page,
                  "page_size": 100
              })
              all_records.extend(response["data"])
              api_calls += 1

              if not response["pagination"].get("next_page"):
                  break
              page += 1
          except Exception as e:
              errors += 1
              if errors > 10:
                  break  # Give up after 10 errors

      # Deduplicate
      unique_records = self.deduplicate(all_records)
      duplicate_count = len(all_records) - len(unique_records)

      # Aggregate
      total_trade_value_usd = self.aggregate(unique_records)

      return {
          "total_trade_value_usd": total_trade_value_usd,
          "record_count": len(unique_records),
          "api_calls_made": api_calls,
          "duplicate_count": duplicate_count,
          "errors_encountered": errors
      }
  ```

**`run_a2a.py`** (67 lines)
- **Purpose**: A2A server wrapper for purple agent
- **Key Route**: `POST /a2a`
- **Key Logic**:
  ```python
  @app.post("/a2a")
  async def a2a_endpoint(request: Request):
      body = await request.json()
      if body["method"] == "agent.invoke":
          agent = PurpleAgent()
          result = agent.solve_task(body["params"]["task_input"])
          return {"jsonrpc": "2.0", "result": result, "id": body["id"]}
  ```

**`run.py`** (54 lines)
- **Purpose**: Non-A2A CLI for local testing
- **Usage**: `python run.py --mock-url http://localhost:8000/api/comtrade --reporter USA`

**`tasks.py`** (Same as green-comtrade-bench)
- **Purpose**: Copy of task definitions for reference
- **Note**: Not used at runtime (purple agent receives task_input from green agent)

#### Docker Files

**`Dockerfile`**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY purple_agent.py run_a2a.py run.py ./
EXPOSE 8002
CMD ["python", "run_a2a.py"]
```

#### CI/CD Files

**`.github/workflows/publish-ghcr.yml`**
- **Purpose**: Publishes purple agent Docker image
- **Image**: `ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2:latest`

#### Documentation Files

**`README.md`**
- **Sections**:
  - Overview
  - Quick Start
  - Strategy Explanation
  - Local Testing
  - A2A Integration

### agentbeats-leaderboard Repository

#### Core Files

**`generate_compose.py`** (231 lines)
- **Purpose**: Generates docker-compose.yml from scenario.toml
- **Key Function**: `generate_compose(scenario_file: str) -> None`
- **Logic**:
  ```python
  def generate_compose(scenario_file):
      # 1. Parse scenario.toml
      config = toml.load(scenario_file)
      green_submission = config["submissions"]["green"]
      purple_submission = config["submissions"]["purple"]

      # 2. Build service definitions
      services = {
          "mock-comtrade": {
              "image": f"{green_submission['repo']}/mock-service:{green_submission['tag']}",
              "ports": ["8000:8000"]
          },
          "green-agent": {
              "image": f"{green_submission['repo']}:{green_submission['tag']}",
              "ports": ["8001:8001"],
              "environment": {
                  "MOCK_SERVICE_URL": "http://mock-comtrade:8000"
              }
          },
          "purple-agent": {
              "image": f"{purple_submission['repo']}:{purple_submission['tag']}",
              "ports": ["8002:8002"]
          },
          "agentbeats-client": {
              "image": "ghcr.io/agentbeats/client:latest",
              "environment": {
                  "GREEN_A2A_URL": "http://green-agent:8001/a2a",
                  "PURPLE_A2A_URL": "http://purple-agent:8002/a2a",
                  "TASK_LIST": "T1,T2,T3,T4,T5,T6,T7",
                  "OUTPUT_DIR": "/results"
              },
              "volumes": ["./results:/results"],
              "depends_on": ["green-agent", "purple-agent", "mock-comtrade"]
          }
      }

      # 3. Write docker-compose.yml
      with open("docker-compose.yml", "w") as f:
          yaml.dump({"services": services}, f)
  ```
- **When it's used**: Run locally before committing: `python generate_compose.py --scenario submissions/scenario-default.toml`

**`record_provenance.py`** (89 lines)
- **Purpose**: Adds git commit metadata to result files
- **Usage**: Called after benchmark completes
- **Logic**:
  ```python
  def record_provenance(result_file):
      # 1. Parse result JSON
      with open(result_file) as f:
          result = json.load(f)

      # 2. Get git commit info
      green_commit = subprocess.check_output(
          ["git", "rev-parse", "HEAD"],
          cwd="/repos/green-comtrade-bench"
      ).decode().strip()
      purple_commit = subprocess.check_output(
          ["git", "rev-parse", "HEAD"],
          cwd="/repos/purple-comtrade-baseline-v2"
      ).decode().strip()

      # 3. Add provenance
      result["provenance"] = {
          "green_commit": green_commit,
          "purple_commit": purple_commit,
          "timestamp": datetime.now().isoformat()
      }

      # 4. Overwrite result file
      with open(result_file, "w") as f:
          json.dump(result, f, indent=2)
  ```

#### Scenario Files

**`submissions/scenario-default.toml`**
```toml
[submissions.green]
repo = "ghcr.io/yonghongzhang-io/green-comtrade-bench-v2"
tag = "latest"

[submissions.purple]
repo = "ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2"
tag = "latest"

[config]
task_list = ["T1_basic_pagination", "T2_duplicate_records", "T3_http_429", "T4_http_500", "T5_page_drift", "T6_totals_trap", "T7_combined_chaos"]
```

**`submissions/scenario-dev.toml`**
```toml
# Same structure, but using dev tags for testing
[submissions.green]
repo = "ghcr.io/yonghongzhang-io/green-comtrade-bench-v2"
tag = "dev"

[submissions.purple]
repo = "ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2"
tag = "dev"
```

#### Result Files

**`results/yonghongzhang-io-20260128-140613.json`** (Example)
```json
{
  "submission_id": "yonghongzhang-io-20260128-140613",
  "timestamp": "2026-01-28T14:06:13Z",
  "participants": {
    "green-comtrade-bench": "ghcr.io/yonghongzhang-io/green-comtrade-bench-v2:latest",
    "purple-comtrade-baseline-v2": "ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2:latest"
  },
  "results": [
    [
      {
        "task_id": "T1_basic_pagination",
        "score_breakdown": {
          "correctness": 30.0,
          "completeness": 15.0,
          "robustness": 15.0,
          "efficiency": 15.0,
          "data_quality": 15.0,
          "observability": 10.0
        },
        "score_total": 100.0
      },
      {
        "task_id": "T2_duplicate_records",
        "score_breakdown": {
          "correctness": 24.0,
          "completeness": 15.0,
          "robustness": 15.0,
          "efficiency": 15.0,
          "data_quality": 13.6,
          "observability": 10.0
        },
        "score_total": 92.6
      }
      // ... T3-T7 results
    ]
  ],
  "provenance": {
    "green_commit": "a1b2c3d4e5f6...",
    "purple_commit": "f6e5d4c3b2a1...",
    "timestamp": "2026-01-28T14:06:13Z"
  }
}
```

#### CI/CD Files

**`.github/workflows/run-scenario.yml`**
```yaml
name: Run Benchmark Scenario

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      scenario:
        description: 'Scenario file (e.g., scenario-default.toml)'
        required: true
        default: 'scenario-default.toml'

jobs:
  run-benchmark:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install toml pyyaml

      - name: Generate docker-compose.yml
        run: python generate_compose.py --scenario submissions/${{ inputs.scenario || 'scenario-default.toml' }}

      - name: Pull Docker images
        run: docker-compose pull

      - name: Run benchmark
        run: docker-compose up --abort-on-container-exit

      - name: Record provenance
        run: python record_provenance.py results/*.json

      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: results/

      - name: Commit results
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add results/
          git commit -m "Add benchmark results: ${{ inputs.scenario }}"
          git push
```

#### Documentation Files

**`README.md`**
- **Sections**:
  - Overview
  - Scenario Configuration
  - Running Benchmarks Locally
  - CI/CD Integration
  - Result Schema
  - Leaderboard Queries

---

## Key Programming Patterns

### Pattern 1: Seeded Random Number Generation for Reproducibility

**Problem**: How to generate random test data that's different for each task but identical across runs?

**Solution**: Hash the task_id to create a seed, then use `random.Random(seed)` for all randomness.

**Implementation**:
```python
# In judge.py and mock_service/app.py
import random

def generate_data(task_id):
    seed = hash(task_id) % (2**32)  # Hash to 32-bit integer
    rng = random.Random(seed)  # Create independent RNG instance

    # All randomness uses this rng
    countries = load_countries()
    for i in range(150):
        reporter = rng.choice(countries)  # Deterministic choice
        trade_value = rng.uniform(1000, 1000000)  # Deterministic value
```

**Why it works**:
- `random.Random(seed)` creates an **independent RNG instance** (doesn't affect global `random.random()`)
- Same seed → same sequence of random values
- Different task_ids → different seeds → different data

**Key Insight**: This pattern enables:
- **Reproducible tests**: Re-run task = same results
- **No stored data**: Generate on-demand
- **Parallel execution**: Each task has independent RNG

### Pattern 2: JSON-RPC 2.0 Over HTTP (A2A Protocol)

**Problem**: How to standardize communication between agents and judges written in different languages?

**Solution**: Use JSON-RPC 2.0 over HTTP POST.

**Request Format**:
```json
{
  "jsonrpc": "2.0",
  "method": "task.init",
  "params": {"task_id": "T1_basic_pagination"},
  "id": 1
}
```

**Response Format**:
```json
{
  "jsonrpc": "2.0",
  "result": {"mock_api_url": "http://..."},
  "id": 1
}
```

**Error Format**:
```json
{
  "jsonrpc": "2.0",
  "error": {"code": -32600, "message": "Invalid Request"},
  "id": 1
}
```

**Implementation**:
```python
# In agent_a2a.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/a2a")
async def a2a_endpoint(request: Request):
    body = await request.json()

    # Validate JSON-RPC 2.0 format
    if body.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": body.get("id")}

    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")

    # Route to handler
    if method == "task.init":
        result = judge.init_task(params["task_id"])
    elif method == "task.score":
        result = judge.score_output(params["task_id"], params["solution_output"])
    else:
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request_id}

    return {"jsonrpc": "2.0", "result": result, "id": request_id}
```

**Why it works**:
- **Language-agnostic**: Any language with HTTP client can participate
- **Standardized**: JSON-RPC 2.0 is a well-defined spec
- **Simple**: No complex serialization (just JSON)
- **Debuggable**: Can test with `curl` or Postman

### Pattern 3: Governance Gates (Anti-Gaming Logic)

**Problem**: Agents might optimize for one metric at the expense of overall correctness.

**Example Attack**: Agent retrieves only 10% of records, computes total (wrong answer), but claims high data quality.

**Solution**: Apply cascading gates that zero out dependent scores when prerequisites fail.

**Implementation**:
```python
# In judge.py
def score_output(self, task_id, agent_output):
    # Compute all scores normally
    score_breakdown = {
        "correctness": compute_correctness(...),
        "completeness": compute_completeness(...),
        "robustness": compute_robustness(...),
        "efficiency": compute_efficiency(...),
        "data_quality": compute_data_quality(...),
        "observability": compute_observability(...)
    }

    # Gate 1: Completeness → Correctness
    if score_breakdown["completeness"] < 14.0:  # Less than 93% complete
        score_breakdown["correctness"] = 0
        # Reason: Can't trust correctness if you didn't get all the data

    # Gate 2: Correctness → Data Quality
    if score_breakdown["correctness"] < 1.0:  # Essentially wrong
        score_breakdown["data_quality"] = 0
        # Reason: Data quality doesn't matter if the final answer is wrong

    score_total = sum(score_breakdown.values())
    return {"score_breakdown": score_breakdown, "score_total": score_total}
```

**Why it works**:
- **Prevents partial solutions**: Must solve the whole problem
- **Enforces correctness priority**: Correctness matters most
- **Simple to understand**: Clear cause-effect relationships

**Key Insight**: Gates encode domain knowledge about what matters. In trade data extraction:
1. **Completeness matters first**: Missing data = wrong conclusion
2. **Correctness matters second**: Right answer is the goal
3. **Quality matters last**: Only if you got the right answer

### Pattern 4: Exponential Backoff for Retries

**Problem**: API returns transient errors (HTTP 429, 500). Agent should retry but not overwhelm the API.

**Solution**: Exponential backoff with max retries.

**Implementation**:
```python
# In purple_agent.py
import time

def call_api(self, url, params, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("Max retries exceeded")
            elif response.status_code == 500:  # Server error
                if attempt < max_retries - 1:
                    wait_time = 1 + 2 ** attempt  # 2s, 3s, 5s, 9s, 17s
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception("Max retries exceeded")
            else:
                raise Exception(f"HTTP {response.status_code}")

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    raise Exception("Max retries exceeded")
```

**Why it works**:
- **Exponential spacing**: Gives API time to recover (1s → 16s)
- **Max retries**: Prevents infinite loops
- **Different strategies**: 429 (client fault) vs 500 (server fault) handled slightly differently

**Key Insight**: Real-world APIs are unreliable. Agents must be resilient.

### Pattern 5: Composite Key Deduplication

**Problem**: Detect and remove duplicate records when records don't have unique IDs.

**Solution**: Create composite key from multiple fields, use set for O(1) lookup.

**Implementation**:
```python
# In purple_agent.py
def deduplicate(self, records):
    seen = set()
    unique_records = []
    duplicate_count = 0

    for record in records:
        # Create composite key from fields that should be unique together
        key = (
            record["reporter_code"],
            record["partner_code"],
            record["cmdCode"],
            record["trade_value_usd"]  # Risky: float equality
        )

        if key not in seen:
            seen.add(key)
            unique_records.append(record)
        else:
            duplicate_count += 1

    return unique_records, duplicate_count
```

**Why it works**:
- **Composite key**: Multiple fields together form unique identifier
- **Set membership**: O(1) average-case lookup
- **Preserves order**: First occurrence kept, duplicates dropped

**Potential Issues**:
- **Float comparison**: Using `trade_value_usd` (float) in key can cause false negatives if values differ slightly (e.g., 1234.56 vs 1234.560000001)
- **Better approach**: Round floats or use integer cents

**Improved Version**:
```python
key = (
    record["reporter_code"],
    record["partner_code"],
    record["cmdCode"],
    round(record["trade_value_usd"], 2)  # Round to cents
)
```

### Pattern 6: Docker Compose for Multi-Container Orchestration

**Problem**: Need to run 4 services (mock, green, purple, client) with correct networking and dependencies.

**Solution**: Use docker-compose.yml to define all services, networks, and dependencies.

**Implementation**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  mock-comtrade:
    image: ghcr.io/yonghongzhang-io/green-comtrade-bench-v2/mock-service:latest
    ports:
      - "8000:8000"
    networks:
      - benchmark-net

  green-agent:
    image: ghcr.io/yonghongzhang-io/green-comtrade-bench-v2:latest
    ports:
      - "8001:8001"
    environment:
      - MOCK_SERVICE_URL=http://mock-comtrade:8000
    depends_on:
      - mock-comtrade
    networks:
      - benchmark-net

  purple-agent:
    image: ghcr.io/yonghongzhang-io/purple-comtrade-baseline-v2:latest
    ports:
      - "8002:8002"
    networks:
      - benchmark-net

  agentbeats-client:
    image: ghcr.io/agentbeats/client:latest
    environment:
      - GREEN_A2A_URL=http://green-agent:8001/a2a
      - PURPLE_A2A_URL=http://purple-agent:8002/a2a
      - TASK_LIST=T1,T2,T3,T4,T5,T6,T7
      - OUTPUT_DIR=/results
    volumes:
      - ./results:/results
    depends_on:
      - green-agent
      - purple-agent
    networks:
      - benchmark-net

networks:
  benchmark-net:
    driver: bridge
```

**Key Features**:
- **Service Discovery**: Containers reference each other by service name (e.g., `http://mock-comtrade:8000`)
- **Dependency Order**: `depends_on` ensures mock starts before green
- **Port Mapping**: Host can access via `localhost:8001`, but containers use internal network
- **Volume Mounting**: Results written to container's `/results` appear in host's `./results`
- **Environment Variables**: Pass config without rebuilding images

**Usage**:
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f green-agent

# Stop all services
docker-compose down

# Rebuild images
docker-compose build
```

---

## How to Extend the System

### Adding a New Task (T8)

**Goal**: Add a new task that tests agents' ability to handle missing fields in API responses.

**Steps**:

1. **Define task config in `tasks.py`**:
   ```python
   TASKS["T8_missing_fields"] = {
       "task_id": "T8_missing_fields",
       "reporter": "DEU",
       "partner": "FRA",
       "cmdCode": "TOTAL",
       "year": 2021,
       "record_count": 200,
       "faults": {
           "missing_field_rate": 0.15  # 15% of records missing trade_value_usd
       }
   }
   ```

2. **Implement fault injection in `mock_service/app.py`**:
   ```python
   def inject_missing_fields(records, missing_rate, rng):
       for record in records:
           if rng.random() < missing_rate:
               del record["trade_value_usd"]  # Remove field
       return records

   # In get_comtrade_data():
   if "missing_field_rate" in task_config.faults:
       records = inject_missing_fields(
           records,
           task_config.faults["missing_field_rate"],
           rng
       )
   ```

3. **Update ground truth generation in `judge.py`**:
   ```python
   def _generate_ground_truth(self, task_config):
       # Generate records normally
       records = self._generate_base_records(task_config)

       # Ground truth should EXCLUDE records that will have missing fields
       # (since agent can't compute trade_value for them)
       rng = random.Random(hash(task_config["task_id"]) % (2**32))
       clean_records = []
       for record in records:
           if rng.random() >= task_config["faults"].get("missing_field_rate", 0):
               clean_records.append(record)

       true_total = sum(r["trade_value_usd"] for r in clean_records)
       true_record_count = len(clean_records)

       return {
           "true_total": true_total,
           "true_record_count": true_record_count,
           "records": clean_records
       }
   ```

4. **Update scoring logic in `judge.py`** (if needed):
   ```python
   # Completeness scoring might need adjustment
   # Should agent count records with missing fields?
   # Decision: Agent should report record_count = number of VALID records
   ```

5. **Update purple agent in `purple_agent.py`**:
   ```python
   def solve_task(self, task_input):
       all_records = self.fetch_all_pages(task_input)

       # Filter out records with missing trade_value_usd
       valid_records = [r for r in all_records if "trade_value_usd" in r]
       missing_count = len(all_records) - len(valid_records)

       unique_records = self.deduplicate(valid_records)
       total = self.aggregate(unique_records)

       return {
           "total_trade_value_usd": total,
           "record_count": len(unique_records),
           "api_calls_made": self.api_call_count,
           "duplicate_count": len(valid_records) - len(unique_records),
           "missing_field_count": missing_count,  # New observability metric
           "errors_encountered": self.error_count
       }
   ```

6. **Update observability scoring** (if adding new metric):
   ```python
   # In judge.py score_output()
   observability_score = 0
   if "api_calls_made" in agent_output:
       observability_score += 3
   if "duplicate_count" in agent_output:
       observability_score += 2
   if "missing_field_count" in agent_output:
       observability_score += 2  # New metric
   if "errors_encountered" in agent_output:
       observability_score += 3
   ```

7. **Update task list in scenario config**:
   ```toml
   # In submissions/scenario-default.toml
   [config]
   task_list = ["T1_basic_pagination", "T2_duplicate_records", ..., "T8_missing_fields"]
   ```

8. **Test locally**:
   ```bash
   python agent.py --task T8_missing_fields
   ```

9. **Commit and push**:
   ```bash
   git add tasks.py mock_service/app.py judge.py
   git commit -m "Add T8: missing fields challenge"
   git push
   ```

10. **GitHub Actions will automatically**:
    - Build new Docker images
    - Push to GHCR
    - Run benchmarks in agentbeats-leaderboard repo

### Adding a New Scoring Dimension

**Goal**: Add "Security" dimension that checks if agent logs API keys or sensitive data.

**Steps**:

1. **Update scoring in `judge.py`**:
   ```python
   def score_output(self, task_id, agent_output):
       # Existing dimensions
       score_breakdown = {
           "correctness": self._score_correctness(...),
           "completeness": self._score_completeness(...),
           "robustness": self._score_robustness(...),
           "efficiency": self._score_efficiency(...),
           "data_quality": self._score_data_quality(...),
           "observability": self._score_observability(...),
           "security": self._score_security(agent_output)  # New dimension
       }

       # ... governance gates ...

       score_total = sum(score_breakdown.values())
       return {"score_breakdown": score_breakdown, "score_total": score_total}

   def _score_security(self, agent_output):
       """
       Score security practices (max 10 points)
       - Check if agent_output contains sensitive patterns
       - Penalize if API keys, tokens, or PII appear in logs
       """
       security_score = 10.0

       # Convert output to string for pattern matching
       output_str = json.dumps(agent_output)

       # Check for API key patterns
       if re.search(r"(api[_-]?key|token|secret)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9]{20,}", output_str, re.IGNORECASE):
           security_score -= 5.0  # Major violation

       # Check for PII patterns (emails, phone numbers)
       if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", output_str):
           security_score -= 2.0

       # Check for hardcoded credentials
       if re.search(r"(password|pwd)[\"']?\s*[:=]\s*[\"']?[^\s]{4,}", output_str, re.IGNORECASE):
           security_score -= 5.0

       return max(0.0, security_score)
   ```

2. **Update max total score**:
   - Old total: 100 (30+15+15+15+15+10)
   - New total: 110 (30+15+15+15+15+10+10)
   - **Decision**: Keep total at 100 by reducing other dimensions, OR accept 110 total

3. **Update documentation in `README.md`**:
   ```markdown
   ## Scoring Dimensions

   ### Security (max 10 points)
   - **What**: Did the agent handle sensitive data responsibly?
   - **Penalties**:
     - API keys or tokens in output: -5 points
     - PII (email, phone) in output: -2 points
     - Hardcoded credentials: -5 points
   ```

4. **Update leaderboard queries in `agentbeats_leaderboard.sql`**:
   ```sql
   SELECT
       results.participants."purple-comtrade-baseline-v2" AS id,
       ROUND(AVG(COALESCE(r.score_breakdown.correctness, 0)), 1) AS "Correctness /30",
       ROUND(AVG(COALESCE(r.score_breakdown.completeness, 0)), 1) AS "Completeness /15",
       ROUND(AVG(COALESCE(r.score_breakdown.robustness, 0)), 1) AS "Robustness /15",
       ROUND(AVG(COALESCE(r.score_breakdown.efficiency, 0)), 1) AS "Efficiency /15",
       ROUND(AVG(COALESCE(r.score_breakdown.data_quality, 0)), 1) AS "Data Quality /15",
       ROUND(AVG(COALESCE(r.score_breakdown.observability, 0)), 1) AS "Observability /10",
       ROUND(AVG(COALESCE(r.score_breakdown.security, 0)), 1) AS "Security /10",  -- New
       ROUND(AVG(r.score_total), 1) AS "Total /110"  -- Updated
   FROM results
   CROSS JOIN UNNEST(results.results[1]) AS t(r)
   GROUP BY results.participants."purple-comtrade-baseline-v2"
   ORDER BY AVG(r.score_total) DESC;
   ```

### Adding a New Agent (Orange Agent)

**Goal**: Competitor wants to submit their own agent implementation.

**Steps**:

1. **Create new repository**: `orange-comtrade-agent`

2. **Implement A2A protocol**:
   ```python
   # orange_agent.py
   from fastapi import FastAPI, Request
   import requests

   app = FastAPI()

   @app.post("/a2a")
   async def a2a_endpoint(request: Request):
       body = await request.json()

       if body["method"] == "agent.invoke":
           task_input = body["params"]["task_input"]

           # Your custom strategy here
           result = my_solve_function(task_input)

           return {
               "jsonrpc": "2.0",
               "result": result,
               "id": body["id"]
           }

   if __name__ == "__main__":
       import uvicorn
       uvicorn.run(app, host="0.0.0.0", port=8002)
   ```

3. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY orange_agent.py .
   EXPOSE 8002
   CMD ["python", "orange_agent.py"]
   ```

4. **Build and publish Docker image**:
   ```bash
   docker build -t ghcr.io/yourname/orange-comtrade-agent:latest .
   docker push ghcr.io/yourname/orange-comtrade-agent:latest
   ```

5. **Create scenario config in agentbeats-leaderboard**:
   ```toml
   # submissions/scenario-orange.toml
   [submissions.green]
   repo = "ghcr.io/yonghongzhang-io/green-comtrade-bench-v2"
   tag = "latest"

   [submissions.orange]  # Changed from purple
   repo = "ghcr.io/yourname/orange-comtrade-agent"
   tag = "latest"

   [config]
   task_list = ["T1_basic_pagination", "T2_duplicate_records", "T3_http_429", "T4_http_500", "T5_page_drift", "T6_totals_trap", "T7_combined_chaos"]
   ```

6. **Run benchmark**:
   ```bash
   cd agentbeats-leaderboard
   python generate_compose.py --scenario submissions/scenario-orange.toml
   docker-compose up
   ```

7. **Results appear in** `results/yourname-20260128-*.json`

8. **Leaderboard updates automatically** (AgentBeats platform reads all result files)

---

## Conclusion: The Big Picture

This system demonstrates several fundamental principles of software engineering:

### 1. **Separation of Concerns**
- **Mock service**: Simulates external API
- **Judge**: Defines tasks and evaluates solutions
- **Agent**: Implements solution strategy
- **Orchestrator**: Coordinates execution

Each component has a single, clear responsibility.

### 2. **Reproducibility Through Determinism**
- Seeded RNG ensures same task_id always generates same data
- Docker containers ensure same environment
- A2A protocol ensures same communication format

### 3. **Extensibility Through Modularity**
- Adding new tasks requires no changes to A2A protocol
- Adding new agents requires no changes to judge
- Adding new dimensions requires only judge changes

### 4. **Robustness Through Governance**
- Governance gates prevent gaming
- Retry logic handles transient failures
- Error tracking provides visibility

### 5. **Simplicity Through Standards**
- A2A protocol is standard JSON-RPC 2.0
- Docker Compose is standard orchestration
- JSON is standard data format

### 6. **Transparency Through Observability**
- Agents report `api_calls_made`, `duplicate_count`, `errors_encountered`
- Results stored as human-readable JSON
- Leaderboard queries are open SQL

---

## Final Thoughts

This architecture balances:
- **Rigor**: Deterministic scoring, comprehensive evaluation
- **Flexibility**: Easy to add tasks, agents, dimensions
- **Simplicity**: No databases, no complex state management
- **Transparency**: All code is open, all results are public

By understanding this architecture, you've learned:
- How to design a benchmark evaluation framework
- How to use seeded RNG for reproducible randomness
- How to implement JSON-RPC 2.0 protocol
- How to orchestrate multi-container systems with Docker Compose
- How to prevent gaming through governance gates
- How to build extensible, modular systems

These patterns apply far beyond this specific benchmark - they're fundamental principles for building robust, testable, maintainable software systems.

**Next Steps**:
- Try implementing your own agent
- Add a new task (T8, T9, T10)
- Contribute improvements to the baseline agent
- Design your own benchmark for a different domain

Happy coding! 🚀
