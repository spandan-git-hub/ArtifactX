# PROJECT MASTER RULES & DEVELOPMENT GUIDELINES

## CRITICAL OPERATIONAL RULE: NO EXCESSIVE OR REPETITIVE TESTING
1. **Direct Action Over Testing Loops:** Never run repeated benchmark loops, redundant micro-tests, or endless exploratory test commands to write or verify basic code. 
2. **Minimal, Targeted Verification Only:** When testing is strictly necessary, execute only ONE direct, targeted verification step that directly validates the fix, and then stop immediately.
3. **No Unrequested Benchmarking:** Do not run diagnostic timing tests, query timers, or multi-minute profiling tasks unless specifically requested by the user.
4. **Fast Execution:** Prioritize rapid development, direct fixes, and immediate delivery of working code over circular verification cycles.
