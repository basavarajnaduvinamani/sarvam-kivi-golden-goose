# Limitations

This demonstration is constrained to semantic memory evaluation workflows and deliberately omits broad enterprise functionality.

## Architectural and Scaling Limits

- **Single User Identity**: The product tracks memory relative to project scope without distinguishing multiple human user personas simultaneously updating the same project space.
- **Synchronous Execution**: The semantic pipeline processes ingestion, retrieval, and inference tasks synchronously. Extensive corpus loads or high concurrent requests may saturate the application processes.
- **Offline Deterministic Fallbacks**: The deterministic testing modes do not produce fluent or linguistically nuanced answers. They are strictly designed to evaluate evidence linkage, project isolation, timeline integrity, and retrieval constraints. They do not simulate actual natural language reasoning.

## Operations

- **Storage Backend**: Bound strictly to local SQLite to demonstrate portability and verifiable reproducibility. 
- **Cost**: The deterministic evaluations incur no cost. Candidate provider evaluations require an active API key, and long tests will consume token balances proportional to corpus extraction and query response logic.
