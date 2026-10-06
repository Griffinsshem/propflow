# ADR 0017: Local disk storage for development and end-to-end tests

## Status
Accepted

## Context
Photos upload directly from browsers to object storage with short-lived signed URLs (ADR 0009).
The in-memory test backend issues `memory://` URLs, which browsers cannot use, and lives inside
one process, so neither local development nor browser tests could exercise uploads.

## Decision
- `STORAGE_BACKEND=local` (development and tests only; production refuses it): files on local
  disk, shared by every process on the machine.
- Its URLs mirror S3 presigned URLs: they expire, and the method, key, content type and expiry
  are covered by an HMAC signature verified in constant time. A download link cannot upload, and
  uploads must send exactly the signed Content-Type.
- URLs point at the frontend origin, so browsers reach them through the same proxy as the API;
  keys can never resolve outside the storage directory. The upload route alone accepts up to
  12 MB, so oversize photos still reach the API's own 10 MB rejection, as with S3.
- Browsers upload without cookies (`credentials: "omit"`): the signed URL is the only credential.
- The frontend CSP adds exactly one configured origin (`STORAGE_ORIGIN`) to `connect-src` and
  `img-src` in production; locally, storage links are same-origin.

## Consequences
- Browser tests cover the full photo journey: link, upload, confirmation, worker processing,
  display and rejection.
- The S3 code path itself (real presigned URLs and R2 CORS rules) is first exercised at the first
  deployment, where the runbook requires uploading a real photo.
