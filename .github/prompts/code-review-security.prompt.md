---
description: "Security-focused code review. Analyzes code for OWASP Top 10 issues, authorization gaps, data leakage, injection risks, and Rails-specific security concerns."
name: "code-review-security"
argument-hint: "Paste the code or PR to review for security issues..."
agent: "agent"
tools: [read, search]
---

Perform a security-focused review of the following code:

**Code / PR:**
[paste code or describe the change]

**Context:**
[e.g., "new API endpoint", "authentication change", "file upload feature"]

---

Analyze for every category below. For each finding, state the exact risk and how it could be exploited.

---

## 1. Broken Access Control
- Is authorization enforced on every action? (Pundit `authorize`, `policy_scope`)
- Are resources scoped to the current company/tenant? (no `User.find(params[:id])` — should be `current_company.users.find(params[:id])`)
- Can a user access data belonging to another user or company by changing an ID in the request?
- Are any admin-only actions accessible by regular users?
- Is `before_action :authenticate_user!` present on all controllers that need it?

## 2. Injection
- Is any user input used in raw SQL? (look for `where("#{params...}")`, `execute`, string interpolation in queries)
- Is any user input used in shell commands? (`system`, backticks, `Open3`)
- Is any user input reflected in HTML without proper escaping? (`html_safe`, `raw` usage)
- Are there any SSRF risks? (user-controlled URLs used in HTTP requests)

## 3. Sensitive Data Exposure
- Does any log line output sensitive data? (passwords, tokens, SSNs, bank accounts, PII)
- Does any API response include fields that shouldn't be exposed for this role?
- Are error messages too verbose? (stack traces, SQL errors leaked to the client)
- Is sensitive data stored in plain text where it should be encrypted or hashed?
- Are API keys / secrets hardcoded anywhere or committed to source control?

## 4. Mass Assignment
- Are strong parameters defined for every controller action that accepts params?
- Can a user set fields they shouldn't (e.g., `role`, `company_id`, `is_admin`) by adding them to a request?

## 5. Authentication & Session
- Is the authentication flow correct? (no way to bypass `authenticate_user!`)
- Are password reset / email confirmation tokens single-use and time-limited?
- Are there any endpoints that act on a user's behalf without verifying their identity?

## 6. File Uploads (if applicable)
- Is the file type validated server-side (not just by extension — by MIME type)?
- Is file size limited?
- Are files stored outside the webroot (can't be served as executable code)?
- Is the filename sanitized before being stored or used anywhere?

## 7. Dependency Issues
- Are any third-party gems used that have known vulnerabilities? (flag gem name + version)

---

## Security Review Summary

### 🔴 Critical Findings
[Immediate risks — data breach, unauthorized access, injection]

### 🟡 Medium Findings
[Need fixing before production — information disclosure, weak controls]

### 🔵 Hardening Suggestions
[Defense-in-depth improvements — not critical but worth doing]

### ✅ Security Positives
[What the code does well from a security perspective]
