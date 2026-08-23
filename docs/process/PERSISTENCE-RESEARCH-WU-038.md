# Persistence Research — WU-038

## Sources reviewed

### SQLite

SQLite documents WAL as a transaction mechanism in which changes are written
to a write-ahead log and committed through a commit marker. SQLite also
supports a user-defined `user_version` field for application-level schema
versioning. SQLite documents the database as a suitable application file
format with atomic transactions and incremental updates.

### LangGraph

LangGraph separates short-term thread checkpoints from longer-lived stores.
Its documentation emphasizes persistent checkpoints for resume/failure
recovery and distinguishes in-memory development storage from persistent
production checkpointers.

### Temporal

Temporal separates durable workflow orchestration from failure-prone
Activities. Its guidance keeps external/non-deterministic operations outside
deterministic workflow logic and applies retry policies at the Activity
boundary.

## Architectural conclusions for this project

1. Durable project state should be behind a stable internal repository port.
2. The first durable slice should not introduce a distributed database merely
   because the system may eventually become distributed.
3. Checkpoint semantics and long-term project state are related but should not
   be collapsed into one generic memory abstraction.
4. Retry and execution durability should remain distinct from repository
   persistence.
5. Physical storage representation belongs in Infrastructure.

## External references

- https://sqlite.org/fileformat.html
- https://sqlite.org/appfileformat.html
- https://github.com/langchain-ai/langgraph
- https://github.com/temporalio/sdk-python
- https://github.com/temporalio/documentation
