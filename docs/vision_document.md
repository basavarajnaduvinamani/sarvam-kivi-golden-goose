# Product Vision Document: Semantic Memory Engine for Kivi

### 1. What Semantic Memory Should Allow Kivi to Become

Today, dictation tools are deaf to their own past. They act as transient pipes, converting spoken acoustic frames into application keystrokes before discarding the semantic payload. Kivi must become an epistemic operating system—an ambient intelligence partner that synthesizes fragmented, cross-application spoken thoughts into an integrated, longitudinal knowledge graph. When a user dictates in Slack, drafts in Notepad, and prompts in ChatGPT, Kivi does not merely route audio; it builds an auditable, temporal fabric of projects, commitments, and evolving state.

### 2. Where the Real Value Is Created for the User

Real value is not created by hoarding trivia or mirroring user chatter. Value emerges when Kivi relieves cognitive load across four high-leverage workflows:
1. Cross-Application Continuity: Resolving temporal dependencies across disjoint software (e.g., retrieving a launch restriction dictated in Slack to safely contextualize an email draft in Outlook).
2. Context-Aware Transformation: Re-synthesizing earlier thoughts without re-explaining background ("Polish my 5 PM standup take for tomorrow's investor update").
3. Temporal Conflict Resolution: Automatically identifying when a newer take supersedes an older commitment (e.g., moving Project Harbor from Tuesday to Thursday).
4. Epistemic Modality Tracking: Discerning firm commitments from rejected proposals, open brainstorms, or conditional approvals.

### 3. What Deserves to Be Remembered

A memory system that retains everything becomes noisy, slow, and untrustworthy. Kivi enforces a strict three-tier memory hierarchy:
- Factual Memory: Verified entities, project states, timelines, and architectural constraints. Every fact carries explicit validity intervals (valid_from, valid_until) and source provenance.
- Episodic Memory: The verbatim context of specific spoken interactions, indexed by timestamp, foreground application, and conversational role.
- Preference Memory: Durable stylistic traits, vocabulary conventions, and communication patterns.

Conversely, Kivi deliberately discards: conversational filler, transient acoustic artifacts, exploratory brainstorming, and explicit hypotheticals. Spoken discourse quoted as rejected or unapproved (such as brainstorming to delete a database) is indexed strictly under epistemic qualification, never as an active directive.

### 4. What Kivi Must Never Assume

Empirical testing reveals that AI memory breaks user trust through uncalibrated inferences. Kivi operates under four inviolable prohibitions:
- Never Infer Action from Musings: Brainstorming, sarcastic remarks, or hypothetical scenarios must never be elevated to facts or tasks without explicit user ratification.
- Never Guess Missing State: When queried on unmentioned entities, Kivi must deliberately abstain ("I have no record of that in your dictations") rather than hallucinating plausibility.
- Never Breach Entity Boundaries: Information learned under one project scope must not contaminate unrelated projects during semantic vector retrieval.
- Never Retain Ghost State: When a user deletes a take or memory, deletion must be transactional and absolute—synchronously purging relational rows, vector embeddings, and cached prompts.

### 5. Why Someone Should Trust This System Enough to Keep Using It

Trust is an architectural property, not a marketing promise. Users trust Kivi because it is:
- Verifiable: Every synthesized response provides exact, clickable provenance citations mapping directly to the underlying timestamped take.
- Sovereign & Local-First: Memory is persisted in local relational storage. Encryption keys remain user-controlled, ensuring zero unauthorized model training.
- Inspectable & Amendable: Users possess an interactive Memory Inspector allowing instant auditing, editing, or revocation of learned facts and preferences.
- Epistemically Honest: Kivi states its confidence boundaries transparently, distinguishing between verified fact, pending approval, and historical record.
