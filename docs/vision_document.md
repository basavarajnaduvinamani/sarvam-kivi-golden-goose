# Product Vision Document

Kivi should eliminate repeated explanation without turning every utterance into a permanent profile the user never chose.

Kivi first serves knowledge workers making decisions across documents, chats, meetings, and technical tools. Its highest-value job is recovering project state: what was decided, what remains conditional, what changed, and each statement's source. A spoken schedule correction captured while ChatGPT is active should remain available while drafting in Notepad, without re-explanation or contamination from another project.

Across 46 numbered live audit cases, including targeted retests and diagnostics, Kivi's Windows alpha resolved superseded information (Test 13), distinguished a rejected proposal from an approved action (Test 38), and abstained when approval evidence was absent (Test 12). It also returned unrelated project facts (Tests 15 and 16) and continued retrieving a deleted take after restart (Test 26). These failures expose two system invariants. Attribution integrity means each active claim matches the correct project, entity, time, and decision state and cites all supporting takes. Lifecycle integrity means every correction, supersession, or deletion reaches all derived representations.

Ordinary dictation should remain the capture surface; semantic memory should principally affect Hey Kivi. Each take should preserve its raw ASR, formatted text, timestamp, source application, and available project or entity context. Derived memories may represent decisions, constraints, commitments, corrections, and durable preferences. Per-application preferences must override broader settings deterministically and never revert silently. Each derivation must record all supporting takes, its method and time, and which evidence remains active.

Kivi must not promote quoted, hypothetical, rejected, or conditional speech into an active fact. It should preserve such statements only with their status attached. A correction should supersede an older value without erasing its history. Application is provenance, not a hard boundary: evidence may cross applications when it belongs to the same project. Project context must come from explicit context or user confirmation; semantic similarity alone cannot authorize a cross-project match. If scope is uncertain, Kivi should ask.

Kivi demonstrated strong Kannada and Hindi-English code-switching in Tests 3 and 45. Memory must preserve it without changing project identity, protected technical terms, or the force of a constraint.

Every answer must distinguish retrieved evidence from model-generated wording. Unsupported retrieval should return a typed `NO_EVIDENCE` result internally; the interface should translate it into plain language, show relevant sources if any exist, and request clarification when that can resolve the ambiguity. Context-capture or service failures are different states and must produce actionable errors rather than silently closing, as observed in Tests 42 and 44.

Control must remain understandable to someone who never reads schemas. A person should be able to inspect why a memory affected an answer, correct it, and revoke it without opening a database. Retention, synchronization location, and training use must be disclosed and independently controllable.

Deletion should be two-phase. Before reporting success, a durable tombstone must exclude the source take and dependent memories from every query path. Physical purge may finish asynchronously within a published objective, but restarts and index rebuilds must honor the tombstone. Derived memories that lose evidence must be invalidated and re-derived only from remaining valid sources. The interface should report purge and verification status.

This vision succeeds only if it is measurable. Evaluation must test cross-project leakage, unsupported-answer abstention, temporal corrections, decision status, provenance coverage, deletion after restart and index rebuild, latency, storage growth, model usage, and cost. Failures must remain inspectable. Kivi earns trust not by claiming perfect memory, but by making every remembered claim attributable, correctable, and revocable.
