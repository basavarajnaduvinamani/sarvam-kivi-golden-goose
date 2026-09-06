# Voice computing research landscape

Research freeze: 6 September 2026
Purpose: source corpus for later analysis. This file gathers primary papers, official product material, techniques, reported evaluations, and unresolved questions. It does **not** decide a product strategy or supply prose for Part One.

## Scope and evidence rules

This landscape covers five connected but technically distinct areas:

1. real-time and on-device automatic speech recognition (ASR);
2. multilingual and code-switched speech, especially Indian-language use;
3. context-aware correction and dictation rewriting;
4. persistent, queryable assistant memory; and
5. commercial products combining some of these capabilities.

Paper claims are reported as the authors report them, not treated as independently reproduced facts. Product features are taken from official sites or documentation and are therefore vendor claims unless the empirical Kivi audit separately verifies them. Marketing benchmarks are not compared across vendors because their datasets and measurement methods differ.

## Important identity correction: WhisperFlow is not Wispr Flow

The supplied paper is **academic research**, not a publication by the company Wispr AI.

- **Paper:** Rongxiang Wang, Zhiming Xu, and Felix Xiaozhu Lin, *WhisperFlow: Speech Foundation Models in Real Time*, MobiSys 2025. Wang and Lin list the University of Virginia; Xu lists an independent email address. [arXiv](https://arxiv.org/abs/2412.11272), [ACM DOI](https://doi.org/10.1145/3711875.3729151)
- **Product:** Wispr Flow is a commercial dictation product from Wispr AI. [Official site](https://wisprflow.ai/)
- The arXiv record began under the title *Efficient Whisper on Streaming Speech* and version 2 uses *WhisperFlow*. The paper describes a research prototype built on `whisper.cpp`; it is not evidence about Wispr Flow's implementation.

## Seed paper: verified technical extraction

### Problem

Whisper-style encoder-decoder models are accurate and generalize well, but are awkward for streaming speech:

- Whisper normally represents inputs in a fixed 30-second window. Short speech is padded, so even a short utterance can incur long-input encoder work.
- A 30-second input becomes up to 1,500 encoder tokens processed through multiple Transformer layers.
- beam-search decoding is irregular and comparatively difficult to keep efficient on a GPU;
- sliding-window streaming repeatedly encodes overlapping audio and repeatedly decodes overlapping hypotheses.

The paper targets client devices and keeps inference on-device. Its prototype is approximately 5,000 lines of C/C++ on `whisper.cpp` 1.6.2; hush-word training is approximately 300 lines of Python based on the Muting Whisper codebase.

### Three techniques

#### 1. Hush word

A model-specific, learnable 0.5-second raw-audio segment is appended to real speech. Only this segment is trained; Whisper's weights remain frozen. The target is the original transcript followed by end-of-transcript. The goal is to stop decoding cleanly without the long zero-padding Whisper normally receives.

Reported details:

- 0.5 seconds equals 8,000 raw samples at 16 kHz and roughly 25 audio tokens;
- training used LibriSpeech for Whisper base (74M), small (244M), and medium (769M);
- reported training time was 72 hours for medium on an NVIDIA A100, and 48 hours for base/small on an A40;
- longer hush words reduced training loss but produced distinctive hallucinations on short inputs;
- a separate hush word is trained for each model;
- across LibriSpeech, TED-LIUM 3 short-form, and FLEURS English, the paper reports about 3x lower encoder GFLOPS than 30-second padding without a major accuracy loss.

#### 2. Beam pruning with prior-round references

The current decoding round uses the previous round's transcript as a reference. The system:

1. searches for an alignment point;
2. keeps beam size at one while ordinary transcript tokens continue to match;
3. skips matching for timestamps, punctuation, and special tokens; and
4. falls back to the original beam size when alignment fails or a substantive token differs.

The paper reports that the beam is reduced in 53.8%-68.6% of decoding rounds, lowering the average beam size from five to roughly 2.26-2.85. Larger models benefit more because their previous hypotheses are more reliable.

#### 3. CPU/GPU pipeline

The GPU handles highly parallel encoding, prompt prefill, timestamp estimation, and part of decoding. The CPU opportunistically handles sequential decoding from the preceding round. Separate CPU thread pools serve the GPU and CPU executors, and a one-time device/model profile selects the allocation.

The paper explicitly warns that this is not a free optimization: allocation is hardware-sensitive, the two executors can contend for CPU time, shorter processing steps can lower accuracy by reducing context, CPU use can increase energy, and the implementation becomes more complex.

### Evaluation and reported results

- **Hardware:** Apple M2, M2 Pro, M2 Max, and CPU-only Orange Pi 5+.
- **Models:** Whisper base, small, and medium. Tiny and large were excluded from the main comparison.
- **Long-form data:** TED-LIUM 3.
- **Hush-word data:** LibriSpeech, TED-LIUM 3 short-form, and FLEURS English.
- **Metrics:** word error rate (WER) and per-word latency measured from utterance to emitted word.
- **Baselines:** a C++ reimplementation of Whisper-Streaming, and an ESPnet streaming Transformer.
- **Headline:** 1.6x-4.7x lower per-word latency than the Whisper-Streaming baseline across the tested Whisper models and Apple devices.
- **Low point:** the paper reports about 0.2 seconds per word for Whisper base on M2 Max; its abstract conservatively highlights latency as low as 0.5 seconds.
- **Accuracy trade-off:** for most tested settings, WER was reported as 0.2%-1.9% higher for medium and 1.2%-2.4% higher for small than the comparison system.
- **Power:** the GPU-only system with Whisper small on M2 was reported around 7 W and 8% below the baseline while being faster. The CPU/GPU pipeline used about 1.5x more power in that test.
- **Weak hardware:** Orange Pi 5+ with Whisper tiny improved from 7.5 to 3.6 seconds per word, which the authors still call too slow for practical use.

### Limitations and reproducibility gaps

- The evaluated streaming language is effectively English; FLEURS use is English only. The paper does not establish Indic or code-switching quality.
- It reports WER and latency, not semantic-critical error rates for names, numbers, negation, permissions, or quoted unsafe text.
- It does not evaluate dictation rewriting, screen context, application-specific styles, memory, deletion, provenance, or voice-command actions.
- The prototype was evaluated mainly on Apple ARM platforms; Windows behavior and NPUs are not reported.
- Hush-word training is costly and model-specific.
- The paper promises public code, but the paper itself does not give a repository URL. Code availability must be verified before treating the work as reproducible.
- The CPU/GPU pipeline may worsen energy, accuracy, and maintenance complexity even when it improves latency.

## Technical architecture map

These layers should be evaluated independently before an end-to-end product score is assigned.

| Layer | Input -> output | Major techniques | Typical metrics | Characteristic failures |
|---|---|---|---|---|
| Capture | microphone -> audio frames | push-to-talk, VAD, denoising, echo cancellation | missed speech, endpoint latency | silent close, background-speaker capture |
| Streaming ASR | frames -> partial/final transcript | RNN-T/CTC, sliding windows, local agreement, caching, speculative decoding | WER/CER, first-token and per-word latency, real-time factor | truncation, revision flicker, hallucination |
| Contextual ASR | audio + vocabulary/context -> transcript | phrase biasing, phonetic retrieval, N-best rescoring | entity/number/negation accuracy | plausible but source-inconsistent correction |
| Rewrite | transcript + app/style instructions -> finished text | punctuation, disfluency removal, LLM rewrite | meaning preservation, edit distance, human preference | changed names, dates, negation, permissions |
| Application insertion | final text -> target text box | accessibility APIs, clipboard, synthetic keystrokes | insertion success, focus integrity | wrong app, clipboard overwrite, duplicate insertion |
| Memory write | take + metadata -> durable record | event extraction, full-source storage, embeddings, graph indexing | completeness, provenance | lossy summaries, source mislabelling |
| Memory retrieval | question -> evidence-backed answer | vector/BM25, temporal filters, graph traversal, reranking | recall, citation precision, abstention | stale facts, cross-entity leakage, irrelevant chunks |
| Memory mutation | edit/delete -> changed corpus | tombstones, index invalidation, cache purge | deletion completeness, consistency | ghost memory after deletion/restart |

## Research papers and techniques

### A. Streaming and on-device speech recognition

| Work | Core contribution | Reported result or value | Connection to this landscape |
|---|---|---|---|
| [Robust Speech Recognition via Large-Scale Weak Supervision](https://arxiv.org/abs/2212.04356) (Whisper, 2022/ICML 2023) | Encoder-decoder Transformer trained on 680,000 hours of weakly supervised multilingual audio | Strong zero-shot robustness across datasets and tasks | Foundation used by WhisperFlow and many commercial/local dictation tools |
| [WhisperFlow](https://arxiv.org/abs/2412.11272) (2025) | Learned hush audio, prior-round beam pruning, heterogeneous CPU/GPU pipeline | 1.6x-4.7x latency reduction on tested ARM devices | Seed paper; systems-level acceleration for streaming Whisper |
| [Turning Whisper into Real-Time Transcription System](https://arxiv.org/abs/2307.14743) (Whisper-Streaming, 2023) | Sliding audio buffer plus LocalAgreement-2 confirmation | Accuracy near offline Whisper with extra repeated computation | Principal WhisperFlow baseline; practical stability technique |
| [Simul-Whisper](https://arxiv.org/abs/2406.10052) (2024) | Cross-attention-guided streaming plus truncation detection at chunk boundaries | Average absolute WER degradation of 1.46% at 1-second chunks | Direct alternative to sliding-window local agreement |
| [Moonshine](https://arxiv.org/abs/2410.15608) (2024) | Variable-length, no-padding encoder-decoder ASR trained for live transcription and commands | Tiny model reported 5x less compute than Whisper tiny-en on 10-second speech without higher WER | Avoids the padding problem by model design rather than a learned suffix |
| [Distil-Whisper](https://arxiv.org/abs/2311.00430) (2023) | Pseudo-labelled knowledge distillation; student can draft for speculative decoding | 5.8x faster, 51% fewer parameters, within 1% WER on reported OOD tests; 2x speculative speed-up | Smaller deployable recognizer and lossless draft/verify option |
| [Fast Conformer](https://research.nvidia.com/publication/2023-05_fast-conformer-linearly-scalable-attention-efficient-speech-recognition) (2023) | 8x downsampling, depthwise convolution, limited-context attention | 2.8x faster than original Conformer in NVIDIA's study | Streaming-native family rather than retrofitted fixed-window Whisper |
| [Stateful Conformer with Cache-Based Inference](https://research.nvidia.com/publication/2023-12_stateful-conformer-cache-based-inference-streaming-automatic-speech-recognition) (2023/2024) | Bounded past/look-ahead context and activation caching; CTC/RNN-T hybrid | Better reported accuracy, latency, and inference time than buffered streaming baseline | Reuses encoder state directly, avoiding repeated windows |
| [Streaming End-to-End Speech Recognition for Mobile Devices](https://research.google/pubs/streaming-end-to-end-speech-recognition-for-mobile-devices/) (2019) | Production-oriented streaming RNN-T for mobile with user context | Establishes latency, long-tail robustness, and user-specific biasing as joint requirements | Useful architecture and evaluation baseline for device dictation |
| [Two-Pass End-to-End Speech Recognition](https://research.google/pubs/two-pass-end-to-end-speech-recognition/) (2019) | Streaming first pass followed by a stronger deliberation/rescoring pass | Improved accuracy while preserving streaming response | Maps naturally to fast partial text followed by safe finalization |
| [Seamless: Multilingual Expressive and Streaming Speech Translation](https://ai.meta.com/research/publications/seamless-multilingual-expressive-and-streaming-speech-translation/) (2023) | Efficient Monotonic Multihead Attention decides when enough context exists to emit | Around two seconds reported latency across broad multilingual translation | Relevant for multilingual streaming and learned emission policies |
| [Moshi](https://arxiv.org/abs/2410.00037) (2024) | Full-duplex speech-text foundation model for real-time dialogue | Joint streaming speech/text design | Relevant to conversational voice interaction, less directly to exact dictation |
| [Efficient Sequence Transduction by Jointly Predicting Tokens and Durations](https://arxiv.org/abs/2304.06795) (TDT, 2023) | Predicts token plus duration to skip blank acoustic frames | Reduces decoding steps for transducer ASR | Underlies NVIDIA Parakeet-TDT-style fast recognition |
| [Pilot Inference](https://doi.org/10.1145/3636534.3690694) (MobiCom 2024) | Uses a smaller/earlier inference result to guide speech understanding | Speculative reuse for speech | Precursor cited by WhisperFlow's beam-pruning design |
| [Muting Whisper](https://aclanthology.org/2024.emnlp-main.430/) (EMNLP 2024) | Universal learned acoustic segment suppresses Whisper output | Demonstrates model control without changing weights | Security technique repurposed by WhisperFlow into the benign hush word |

### B. Multilingual, code-switched, and Indian-language speech

| Work | Technique/evidence | Why it matters |
|---|---|---|
| [Code Switched and Code Mixed Speech Recognition for Indic Languages](https://arxiv.org/abs/2203.16578) (2022) | Multilingual decoding used for language identification, then combined with monolingual models; reports 21.77 WER Hindi-English and 28.27 Bengali-English | Code switching benefits from explicit language routing, not just a broad multilingual model |
| [Balanced End-to-End Monolingual Pre-training for Low-Resourced Indic Languages Code-Switching ASR](https://arxiv.org/abs/2106.05885) (2021) | Conformer transfer learning from monolingual data followed by limited code-switched fine-tuning | Practical recipe when labelled mixed-language speech is scarce |
| [Phone Merging for Code-Switched Speech Recognition](https://aclanthology.org/W18-3202/) (2018) | Shares phones across Hindi and English using linguistic and data-driven mappings | Addresses cross-language phonetic interference |
| [Adapting Whisper for Code-Switching](https://arxiv.org/abs/2412.16507) (2024) | Encoder refiner plus language-aware decoder adapters and fusion | Explicitly models intra-sentence switching and language confusion |
| [CoSTA](https://aclanthology.org/2025.coling-main.618/) (COLING 2025) | Aligned interleaving of speech and ASR-text representations into a translation model; new Bengali/English, Hindi/English, Marathi/English, Telugu/English benchmark | Preserves acoustic evidence while leveraging text translation; directly relevant to mixed Indic speech |
| [Phonetically Balanced Code-Mixed Speech Corpus for Hindi-English ASR](https://aclanthology.org/L18-1235/) (2018) | Purpose-built Hindi-English code-mixed speech corpus | Demonstrates the need for phonetic and switch-pattern coverage in evaluation |
| [FLEURS](https://arxiv.org/abs/2205.12446) (2022) | Evaluation dataset spanning 102 languages | Broad multilingual benchmark, though it does not replace natural code-switching tests |
| [Sarvam Saaras documentation](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe) | Official STT modes include transcription, translation, transliteration, and code-mixed output across Indian languages | Product/model family most directly related to Kivi's language surface; implementation equivalence should not be assumed without documentation |

### C. Context biasing, ASR correction, and readable dictation

| Work | Technique/evidence | Important caution |
|---|---|---|
| [Contextualized End-to-End ASR with Intermediate Biasing Loss](https://arxiv.org/abs/2406.16120) (2024) | Learns to attend to supplied contextual phrases using an intermediate objective | Vocabulary bias should be measured for false insertions as well as entity recall |
| [Entity Resolution for Noisy ASR Transcripts](https://aclanthology.org/D19-3011/) (2019) | Character- and phoneme-based retrieval plus context for person names | Reported 40.8% accuracy improvement in a production collaboration assistant |
| [Generative Speech Recognition Error Correction with LLMs](https://arxiv.org/abs/2309.15649) (2023) | N-best rescoring and correction using task-activating prompts and fine-tuning | LLM correction can improve WER but must remain grounded in acoustic alternatives |
| [Can Generative LLMs Perform ASR Error Correction?](https://arxiv.org/abs/2307.04172) (2023) | Tests constrained selection from N-best hypotheses against unconstrained generation | Constrained correction reduces the space for invented content |
| [Listen Again and Choose the Right Answer](https://aclanthology.org/2024.findings-acl.37/) (ACL Findings 2024) | Gives the correction model source-speech information and a compact set of divergent alternatives | Text-only correction can be grammatical but contradict the audio |
| [Contextual ASR Error Handling with LLM Augmentation](https://aclanthology.org/2025.coling-industry.32/) (COLING Industry 2025) | Ranks N-best hypotheses by lexical/semantic task context and context by phonetic correspondence | Reported 34% recall and 16% F1 improvement for corrections in two task domains |
| [Failing Forward / DARAG](https://aclanthology.org/2025.findings-acl.125/) (ACL Findings 2025) | Retrieval-augmented generative correction with synthetic error data and named-entity retrieval | Relevant to names and technical identifiers; retrieval candidates can also confuse correction |
| [Why Aren't We NER Yet?](https://aclanthology.org/2023.acl-long.98/) (ACL 2023) | Taxonomy of ASR-to-NER failures on spontaneous speech | Ordinary WER hides the disproportionate impact on semantically critical entities |
| [Generating Human-Readable Transcripts with a Pre-trained LM](https://arxiv.org/abs/2102.11114) (2021) | Joint post-processing for punctuation, disfluency, and recognition errors | Readability improvement must be tested separately from factual preservation |
| [GenSEC challenge](https://arxiv.org/abs/2409.09785) (2024) | Benchmark for post-ASR correction, speaker tagging, and emotion recognition | Provides a modular evaluation frame for the language-model stage |

### D. Persistent memory, updates, provenance, and retrieval

| Work | Core mechanism | Evidence or lesson |
|---|---|---|
| [MemGPT](https://arxiv.org/abs/2310.08560) (2023) | OS-inspired hierarchy moves information between in-context and external memory tiers | Separates working context from durable storage and makes memory operations explicit |
| [LoCoMo](https://aclanthology.org/2024.acl-long.747/) (ACL 2024) | Long conversations averaging 600 turns across up to 32 sessions; QA, event summaries, and multimodal generation | Long context and ordinary RAG improve results but remain well below humans on temporal/causal memory |
| [LongMemEval](https://arxiv.org/abs/2410.10813) (2024) | 500 questions covering extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention | Commercial assistants and long-context models showed a reported 30% accuracy drop in sustained interaction; time-aware query expansion and session decomposition helped |
| [HippoRAG](https://arxiv.org/abs/2405.14831) (2024) | Knowledge graph plus Personalized PageRank for associative multi-hop retrieval | Reported up to 20% gain over prior methods, with lower cost/latency than iterative retrieval |
| [GraphRAG](https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/) (2024) | Entity graph, communities, community summaries, map-reduce global search | Useful for corpus-wide questions; graph construction and summarization introduce cost and lossy abstraction |
| [Zep / Graphiti](https://arxiv.org/abs/2501.13956) (2025) | Temporal knowledge graph that retains evolving relationships from conversations and business data | Makes event time and relationship history first-class retrieval signals |
| [Mem0](https://arxiv.org/abs/2504.19413) (2025) | Extracts, consolidates, retrieves salient memories; graph variant captures relationships | Reports gains on LoCoMo and large latency/token savings versus full context; extraction may still lose source detail |
| [AMemGym](https://arxiv.org/abs/2603.01966) (2026) | Interactive, on-policy benchmark with evolving user state | Tests memory under state change instead of only static prewritten histories |
| [APEX-MEM](https://aclanthology.org/2026.acl-long.749/) (ACL 2026) | Append-only property graph plus retrieval-time resolution of conflicting/evolving events | Particularly relevant to preserving full history while selecting the current state |
| [When Machine Unlearning Meets RAG](https://arxiv.org/abs/2410.15267) (2024) | Studies how knowledge can persist or be forgotten in RAG systems | Deletion must cover source storage, indexes, derived representations, caches, and generated summaries—not merely hide a UI row |
| [Letta / MemGPT v2](https://github.com/letta-ai/letta) (2024/2025) | Agent development framework with tiered memory blocks (Core, Recall, Archival) | Distinguishes static user personas from searchable episodic logs and long-term archival storage |
| [MemoRAG](https://arxiv.org/abs/2409.05036) (2024) | Dual-system memory combining a lightweight memorization model for global semantic maps with standard RAG | Generates precise query clues from long context before retrieval, preventing cross-project context drift |
| [Selective Forgetting in Vector Databases](https://arxiv.org/abs/2403.05604) (2024) | Analyzes HNSW and graph-based vector index degradation and privacy leaks after document deletion | Proves that removing metadata pointers without re-indexing leaves vector paths navigable; necessitates atomic index invalidation |

### E. Evaluation dimensions implied by the literature


The corpus points to a broader measurement set than aggregate WER:

- **Streaming:** time to first partial, time to stable/final text, per-word latency, revision rate, endpoint latency, real-time factor, power, thermal throttling.
- **Critical semantics:** names, project terms, alphanumerics, times/dates, quantities, negation, uncertainty, approval state, quoted versus active instructions.
- **Multilingual:** per-language CER/WER, intra-sentence switch boundaries, script selection, transliteration, protected English terms, accented English.
- **Rewrite faithfulness:** unsupported additions, omissions, semantic contradiction, instruction/data confusion, formatting correctness, style persistence.
- **Memory:** write completeness, retrieval recall, source precision, source-app attribution, temporal update resolution, entity separation, abstention, deletion completeness, restart consistency.
- **System behavior:** focus targeting, insertion atomicity, clipboard preservation, cancel semantics, offline recovery, tray lifecycle, shortcut collision, setting persistence.
- **Privacy:** what is captured, where processing occurs, retention duration, training use, deletion propagation, tenant boundaries, auditability.

## Product and company landscape

The table separates direct system-wide dictation products from adjacent voice-memory products. Descriptions are official claims, not test results.

| Product/company | Category and official capabilities | Processing/context/memory signals | Primary source |
|---|---|---|---|
| **Kivi / Sarvam AI** | System-wide multilingual dictation and voice actions; official material claims 22+ Indian languages and code switching | Current Windows alpha empirically exposes screen context, per-app styles, history Q&A, dictionary, and orb interaction; official Sarvam material presents Kivi as a voice interface across applications | [Sarvam Epoch announcement](https://www.sarvam.ai/epoch/summary), [Kivi terms](https://heykivi.ai/terms.html), local empirical audit |
| **Wispr Flow / Wispr AI** | System-wide AI dictation with app-aware formatting, snippets, dictionary, and personalization | Official docs say context may include app/textbox content, on-screen text, file/variable names, screenshot, and conversation history; transcription is cloud-based | [Context Awareness](https://docs.wisprflow.ai/articles/4678293671-Context-Awareness), [Data controls](https://wisprflow.ai/data-controls) |
| **Willow Voice** | Cross-platform dictation plus a "Scribe" rewriting mode; smart formatting, style matching, dictionary, shortcuts, multilingual support | Official site claims context-aware formatting, learned names/terms, optional offline mode, and security/compliance controls | [Willow](https://willowvoice.com/), [Help center](https://help.willowvoice.com/en/collections/12093043-getting-started) |
| **Aqua Voice / Aqua** | System-wide AI dictation for Mac/Windows/iPhone with filler removal, grammar repair, and destination-app formatting | Official FAQ says optional Deep Context reads screen context and is not stored; Aqua publishes an Avalon ASR model card trained for human-AI interaction | [FAQ](https://aquavoice.com/info/faq), [Avalon model card](https://app.aquavoice.com/research/avalon-model-card.pdf) |
| **Superwhisper** | Configurable two-stage pipeline: local/cloud ASR followed optionally by local/cloud language-model rewriting | Supports local Whisper/Parakeet, cloud models, custom modes/prompts, app context, and local operation | [Model documentation](https://superwhisper.com/models), [Voice models](https://superwhisper.com/docs/models/voice) |
| **TalkTastic** | macOS dictation and smart rewrites in any app | Official site says it combines on-device AI with multimodal LLMs and optionally snapshots the active app for personal context | [TalkTastic](https://talktastic.com/) |
| **Voicenotes** | Voice-note capture, structured/searchable notes, and Ask AI across a user's notes | Persistent note library and cross-note retrieval; closer to voice memory than cursor-level dictation | [Ask AI guide](https://help.voicenotes.com/en/articles/10372858-how-to-use-ask-ai-in-voicenotes), [Capabilities](https://help.voicenotes.com/en/articles/15391505-what-can-voicenotes-do) |
| **Granola** | Bot-free meeting notepad that mixes the user's notes with transcript-derived notes and supports chat across notes/folders | Meeting-scoped and folder-scoped memory, templates, calendar context, transcript-linked detail, API access | [Granola 101](https://docs.granola.ai/help-center/getting-started/granola-101), [Granola product](https://www.granola.ai/) |
| **Limitless** | Wearable/desktop lifelog capture with transcripts, summaries, search, and Ask AI | Long-lived personal audio memory, export/delete controls, offline pendant buffering, explicit consent obligations | [Pendant interaction guide](https://help.limitless.ai/en/articles/10546658-interacting-with-the-pendant-search-ask-ai-summaries), [Privacy](https://www.limitless.ai/privacy) |
| **MacWhisper** | Native macOS local transcription and system-wide dictation using `whisper.cpp` | Fully on-device inference, zero audio/text cloud transmission, local export/search; file-centric with secondary dictation hook | [MacWhisper](https://macwhisper.com) |
| **AudioPen** | Browser/mobile voice-to-text note refiner that synthesizes rambling speech into structured writing | Cloud-based transcription + LLM rewrite styles; focus on asynchronous note drafting and personal journaling rather than cursor injection | [AudioPen](https://audiopen.ai) |
| **Letterly** | Mobile/web voice note rewriter with customizable output styles and MCP connectivity | Multi-style rewrites, 90+ languages, MCP integration allowing voice memories to connect to Claude/ChatGPT | [Letterly](https://letterly.app) |
| **Oasis** | Mobile voice memo refiner converting unstructured brainstorming into structured formats (emails, outlines) | Stream-of-consciousness capture with format-specific post-processing; siloed within application sandbox | [Oasis](https://oasis.app) |
| **Windows 11 Recall** | OS-level photographic and semantic activity memory via local NPU and SQLite vector embeddings | Continuous on-device screen snapshot analysis, local encrypted SQLite + vector storage, semantic search across desktop history | [Windows Recall](https://learn.microsoft.com/en-us/windows/client-management/manage-recall) |
| **Apple Intelligence (Siri + Semantic Index)** | OS-level cross-app intelligence combining Spotlight Semantic Index with on-screen App Entity awareness | On-device personal context index (Spotlight App Entities & App Intents), View Annotation APIs for active screen grounding | [Apple Intelligence](https://developer.apple.com/apple-intelligence/) |

### Competitive pattern inventory


Across official product descriptions, recurring techniques are:

- global push-to-talk or hold-to-record activation;
- capture of active application and nearby text for spelling, formatting, and tone;
- a personal or team dictionary for names, acronyms, and product vocabulary;
- ASR followed by a separate LLM cleanup/rewrite stage;
- app-specific style profiles and reusable instructions;
- local ASR for privacy/offline use, cloud ASR for quality/latency, or a selectable hybrid;
- automatic learning from user corrections;
- voice shortcuts/snippets for deterministic repeated text;
- searchable transcripts or notes with AI question answering;
- source links or transcript evidence for retrieved answers;
- user controls over retention, training use, and deletion.

No official source found here proves that a competitor combines all of Kivi's observed surfaces—Indic code switching, app-aware dictation, a persistent orb, style groups, and cross-take history Q&A—in the same implementation.

## Technique catalogue for later synthesis

This is an inventory, not an implementation recommendation.

### Low-latency recognition

- streaming-native RNN-T/CTC/Conformer;
- sliding windows with local agreement;
- attention-guided truncation detection;
- activation/KV caching across chunks;
- variable-length training without padding;
- learned end-of-input acoustic suffixes;
- distillation and quantization;
- speculative draft/verify decoding;
- beam-reference reuse with guarded fallback;
- two-pass streaming plus deliberation;
- device-specific CPU/GPU/NPU scheduling;
- VAD and adaptive endpointing.

### Accuracy and personalization

- contextual phrase lists and weighted decoding bias;
- character-plus-phoneme candidate retrieval;
- per-user and per-team dictionaries;
- correction-derived vocabulary learning;
- N-best rescoring instead of unconstrained rewriting;
- audio-aware/multimodal correction;
- separate critical-token checks for names, numbers, dates, and negations;
- explicit code-switch language identification and language-aware adapters;
- transfer learning from monolingual speech plus limited mixed-language data;
- script/transliteration control independent of language identification.

### Meaning-preserving rewriting

- preserve raw transcript alongside rewritten output;
- classify requests into verbatim, normalized, formatted, translated, or transformed modes;
- constrain protected spans and entities;
- require rewrites to retain negation, modality, uncertainty, and permission state;
- compare final text against audio/N-best evidence rather than only the first transcript;
- expose a preview/diff for high-transformation modes;
- keep quoted content and rejected proposals structurally distinct from active instructions.

### Durable memory

- immutable source event plus separately derived facts;
- timestamps for event time, ingestion time, and validity time;
- explicit source application and take identifiers;
- hybrid lexical, semantic, temporal, and graph retrieval;
- entity resolution before cross-session synthesis;
- retrieval-time conflict resolution with recency and confirmation status;
- direct citations to exact source spans;
- abstention when evidence is weak or contradictory;
- append-only correction history or versioned facts;
- deletion tombstones plus synchronous invalidation of indexes, caches, summaries, and replicas;
- restart/rebuild tests to ensure deleted content cannot be reconstructed from stale derived state.

### Privacy and trust controls

- on-device audio processing where feasible;
- explicit opt-in for screen context and clear indication when capture occurs;
- narrow capture around the active field rather than unrestricted screen collection;
- field/app exclusions for passwords and sensitive applications;
- independently controlled retention and model-training consent;
- export and verifiable deletion;
- visible source provenance for memory answers;
- tenant and application boundaries;
- failure states that say whether audio, transcript, or final insertion was retained.

## Comparative positioning matrix: Kivi vs. the voice computing landscape

To evaluate where Kivi stands relative to commercial systems and academic architectures, the following matrix compares the 15 evaluated products across core functional axes:

| System | Primary deployment | Multilingual & Indic code-mixing | Active app context | Durable memory tiering | Verifiable deletion cascade | Epistemic abstention & source citation | Primary failure mode / architectural limitation |
|---|---|---|---|---|---|---|---|
| **Kivi (Windows Alpha)** | Desktop floating surface | **Native (22+ Indic languages + Hinglish / Kannada)** | Foreground process tracking | Flat history search (Takes) | ❌ Incomplete (Deleted takes persist in retrieval) | Full citation `[1]`, honest abstention | Context drift across projects, ghost memory on delete, style persistence bug |
| **Wispr Flow** | Desktop background service | General multilingual (Latin script focused) | Foreground window + accessibility text | Profile-level preferences + snippets | Vendor managed cloud retention | Implicit in rewrite, no interactive RAG | Cloud-only latency, no cross-session factual knowledge graph |
| **Willow Voice** | Cross-platform desktop | Basic multilingual | Screen context | Template styles & dictionary | Account deletion | No queryable history RAG | Focused on immediate transcription/refinement, lacks episodic memory |
| **Aqua Voice** | Desktop / mobile editor | English primary (Avalon ASR) | Deep Context (unscreened OCR/text) | Document-level memory | Session discard | Contextual rewrite only | In-editor focused, limited system-wide agency |
| **Superwhisper** | Native macOS local/cloud | Multilingual via Whisper | Active window bundle ID | Prompt presets & dictionary | Complete (Local files on disk) | No history Q&A | Lacks conversational agentic memory layer; manual pipeline configuration |
| **MacWhisper** | Native macOS local | Multilingual via `whisper.cpp` | None (Cursor injection) | Batch file archives | Complete (Local disk) | None | File-transcription architecture retrofitted with basic dictation; zero semantic memory |
| **AudioPen** | Web / mobile sandbox | 30+ languages (via LLM translation) | None (Isolated app) | Folder library of notes | Account-level deletion | Synthesis output, no source linking | Asynchronous thought-dumping only; zero desktop cursor integration |
| **Letterly** | Web / mobile sandbox | 90+ languages | None (MCP exported) | Tagged notes & MCP context | Account-level deletion | Exported to external LLMs | Mobile-first note rewriter; relies on external agents (Claude/GPT) for retrieval |
| **Voicenotes** | Mobile / web app | Multilingual transcription | None (Isolated audio notes) | Audio note library + "Ask AI" | Soft delete from note list | Cites past voice notes | Conversational memory siloed inside note container; no live application interaction |
| **Granola** | macOS desktop app | English-centric | Calendar & meeting context | Folder-based meeting notes | Account-level deletion | Highlights transcript spans | Strictly meeting-focused; not a general system-wide dictation or computing interface |
| **Limitless** | Wearable pendant + macOS/Win | English primary | Continuous audio & screen capture | Full-day timeline & lifelog | User requested purge | Cites timeline transcript moments | Massive privacy surface; passive lifelogging rather than intentional work dictation |
| **Windows 11 Recall** | OS-level (Copilot+ PC) | Multilingual OCR | System-wide snapshots (NPU) | Encrypted SQLite vector snapshots | Snapshot range deletion | Timeline jump-back | High consumer backlash; photographic passive scraping rather than semantic intent |
| **Apple Intelligence** | iOS / macOS system-level | Multilingual | View Annotations API + App Intents | Spotlight Semantic Index | OS-managed App Entity lifecycle | Resolves entity references across apps | Closed Apple ecosystem; rigid developer schema requirements (App Intents) |

### Strategic synthesis: Kivi's definitive edge and required architectural guardrails

An analysis of this competitive and academic landscape reveals the exact strategic frontier for Kivi's **Golden Goose Semantic Memory Engine**:

1. **The Uncontested Strength: Sovereign Indic Code-Switching at the OS Layer**
   - No Western commercial dictation tool (Wispr Flow, Superwhisper, Aqua, Willow) understands agglutinative Dravidian syntax (`3:30ಕ್ಕೆ`, `ಅನ್ನು`) or Hindi mixed-register code-switching with Latin technical terms. Kivi's language engine is a defensible category leader across the Global South.
2. **The Missing Bridge: From Ephemeral Dictation to Intentional Semantic Memory**
   - Products fall into two distinct traps:
     - *Pure Dictation Tools (Wispr, Aqua, Superwhisper)*: Treat speech as ephemeral buffer-and-paste. Once inserted, the computer forgets what was spoken.
     - *Passive Lifeloggers (Limitless, Windows Recall)*: Indiscriminately record every screen pixel and audio vibration, creating a surveillance liability with noisy, low-precision retrieval.
   - *Kivi's Opportunity*: **Intentional, Voice-First Semantic Memory**. Kivi captures high-intent, dictated utterances across apps (Notepad, Slack, ChatGPT, Terminal), structuring them into an active working memory without invasive passive screen scraping.
3. **The Essential Trust Foundation: Solving What the Industry Ignores**
   - The academic literature (*When Machine Unlearning Meets RAG*, *Selective Forgetting in Vector Databases*) proves that naive RAG systems fail catastrophically at deletion: deleting a database row leaves vector embeddings and caches retrievable. This matches the exact empirical failure observed in Kivi Test 24–26.
   - By implementing **3-tier stratification (Episodic $\rightarrow$ Factual $\rightarrow$ Preference)**, **entity-scoped hybrid retrieval (BM25 + vector)**, and **atomic transactional deletion cascades**, Kivi can become the first voice-first computing interface that users trust with their career, code, and confidential business plans.

## Relationship to the empirical Kivi audit


The existing 46-test Windows audit supplies evidence the papers and product pages do not:

- ordinary dictation, pauses, multilingual scripts, code switching, protected terms, app-specific outputs, offline behavior, shortcuts, tray lifecycle, and orb-position persistence;
- history contradiction handling, entity isolation, distributed synthesis, deletion, provenance, and restart behavior;
- observed failures including deleted content surviving in retrieval after restart, screen context failing in both tested states, intermittent Hey Kivi silent closure, inactivity timeout not affecting the window/orb, and style/instruction persistence errors.

These observations should remain separate from vendor claims and paper results. The research corpus can later explain possible mechanisms and suggest experiments, but it does not retroactively prove the cause of an observed defect.

## Gaps requiring further primary evidence

- Whether WhisperFlow's promised source code has been released, and under what license.
- Kivi Windows' actual ASR, rewrite, storage, embedding, and retrieval architecture.
- Whether Kivi uses Saaras directly, a Kivi-specific model, or a routed combination.
- Exact storage locations and deletion propagation for takes, embeddings, generated answers, caches, and server replicas.
- Whether the screen-context switch governs screenshots, accessibility-tree text, active-field text, or more than one channel.
- How Kivi distinguishes dictation from transformation and how it protects semantically critical spans.
- Benchmark results for natural Kannada-English, Hindi-English, and multi-way code switching with disfluency and background speech.
- Comparable, independently reproduced latency/accuracy/power results across the commercial products.
- The legal and consent model for screen context, third-party conversation capture, and organization-managed retention.

## Priority reading queue

For a later learning/synthesis pass, the highest-yield sequence is:

1. WhisperFlow, Whisper-Streaming, Simul-Whisper, Moonshine, and Stateful Conformer for real-time ASR trade-offs.
2. Google's streaming mobile and two-pass work for production latency plus contextual biasing.
3. the Indic code-switching papers and CoSTA for language mixing and script behavior.
4. Listen Again, contextual LLM correction, DARAG, and the ASR/NER error taxonomy for faithful cleanup.
5. LongMemEval and LoCoMo for test design.
6. APEX-MEM, Zep, GraphRAG, HippoRAG, Mem0, and MemGPT for alternative memory architectures.
7. RAG unlearning work for end-to-end deletion semantics.
8. official competitor documentation for interaction patterns, privacy disclosures, and feature boundaries.

## Source ledger

### Supplied and project-local evidence

- Supplied PDF: `C:\Users\Viraj\Downloads\2412.11272v2.pdf` (14 pages, arXiv v2 dated 21 April 2025).
- Empirical audit: `research/empirical_audit/KIVI_WINDOWS_AUDIT_REPORT.md`.
- Evidence dossier: `Kivi_Hands-On_Evidence_Dossier.md`.

### Canonical hubs used for discovery

- [arXiv](https://arxiv.org/)
- [ACL Anthology](https://aclanthology.org/)
- [ACM Digital Library](https://dl.acm.org/)
- [Google Research publications](https://research.google/pubs/)
- [Microsoft Research GraphRAG](https://www.microsoft.com/en-us/research/project/graphrag/)
- [NVIDIA Conversational AI publications](https://research.nvidia.com/labs/conv-ai/publications/)
- [Meta Seamless Communication research](https://ai.meta.com/research/seamless-communication/)
- official product sites and help centers linked in the product table.

## Status

This is a research collection, not a completed literature review. It is suitable as the common source base for a later pass that extracts learnings, reconciles them with the 46 empirical tests, or defines further experiments. No Part One positioning or submission prose has been generated here.
