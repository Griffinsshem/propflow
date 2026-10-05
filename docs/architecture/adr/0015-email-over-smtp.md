# ADR 0015: Email delivery over SMTP

## Status
Accepted

## Context
Production could not deliver email (ADR 0014): invitations and password resets were a launch
blocker. Every major transactional provider accepts SMTP.

## Decisions
- **SMTP via the standard library** (`smtplib`): no new dependency, no provider lock-in;
  changing provider changes four environment variables.
- **TLS required in production** (`starttls` or `ssl`); `none` exists only for local test
  servers and is refused at startup in production.
- **Failure classes:** connection errors, timeouts and 4xx responses raise
  `EmailTransportError` (worker retries with backoff); authentication failures are logged and
  retried so rotated credentials can be fixed; 5xx rejections and refused recipients are
  logged at error level and not retried.
- **No sensitive data in logs:** bodies contain token links; logs record recipient domain
  and subject only.
- **Header injection refused** by the modern email API (CR/LF in a header raises).
- **Configuration validated at startup:** a real `MAIL_FROM`, an `SMTP_HOST`, and a password
  whenever a username is set.

## Consequences
- Deliverability depends on the sending domain's SPF, DKIM and DMARC records, which belong to
  the custom-domain launch work.
- In local development with `BACKGROUND_TASKS=sync`, an SMTP failure surfaces in the request;
  development normally uses the console backend.
