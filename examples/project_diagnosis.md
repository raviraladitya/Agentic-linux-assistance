# Project Diagnosis Transcript

**Test Scenario**: Diagnosing a failing test suite in a local development repository.

```
You: My project was working yesterday. What changed?
[Agent] Analyzing request...
[MCP]  git_status(repo='~/Projects/my-app')
[MCP]  git_log(repo='~/Projects/my-app', max_entries=5)
[MCP]  run_tests(repo='~/Projects/my-app')
[Agent] Evaluating evidence...
[Agent] Analyzing request...
[MCP]  git_diff(repo='~/Projects/my-app', cached=False)
[Agent] Evaluating evidence...
[Agent] Generating diagnosis...

╭─────────────────────────────────────────────── Diagnosis ────────────────────────────────────────────────╮
│                                                                                                          │
│ Diagnosis: A recent modification to the authentication configuration appears to have broken the login    │
│ tests.                                                                                                 │
│                                                                                                          │
│ Evidence:                                                                                                │
│                                                                                                          │
│  • The test suite (run_tests) is currently failing, specifically the test                            │
│    test_user_login_with_valid_credentials and test_oauth_flow.                                           │
│  • The git_status shows that src/auth/config.py has been modified but not yet committed.                 │
│  • The git_diff reveals that the DEFAULT_SESSION_TIMEOUT value in src/auth/config.py was changed     │
│    from 3600 to 300, and a new environment variable requirement (OAUTH_CLIENT_SECRET) was added          │
│    without a fallback.                                                                                   │
│                                                                                                          │
│ Confidence: HIGH                                                                                         │
│                                                                                                          │
│ Recommended next step: Review the uncommitted changes in src/auth/config.py. Either revert the       │
│ changes or update the failing tests to provide the required OAUTH_CLIENT_SECRET mock and account for     │
│ the shorter session timeout.                                                                             │
│                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
