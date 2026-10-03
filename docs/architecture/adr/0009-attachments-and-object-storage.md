# ADR 0009: Maintenance attachments on Cloudflare R2

## Status
Accepted

## Decisions
- **Storage**: Cloudflare R2 (S3 API via boto3): free tier, no egress fees, provider-neutral
  code. Separate buckets and tokens per environment; tokens scoped to one bucket with
  Object Read & Write only. Tests use an in-memory backend (no extra dependency); the real
  integration is verified with a smoke test.
- **Direct upload**: the API issues a 5-minute presigned PUT for a server-generated key under
  `pending/`, with the content type signed. Bytes never pass through Flask or the Vercel proxy.
- **Verification on completion**: Pillow decodes the real bytes (filename and browser MIME
  type ignored); the detected format must match the declared type; size (10 MB) and pixel
  count (40 MP) are bounded; the image is re-encoded to JPEG (max 2560 px edge), which strips
  EXIF/GPS metadata and appended payloads. Rejected files are deleted immediately.
- **Keys** are built only from server UUIDs (`orgs/{org}/maintenance/{request}/{id}.jpg`):
  no user input reaches a path.
- **Downloads**: authorization first, then 5-minute presigned GET URLs. The bucket is private.
- **Abandoned uploads** under `pending/` are removed by an R2 lifecycle rule (1 day).
- **Failure**: storage errors return 503 `STORAGE_UNAVAILABLE`; the attachment stays
  `pending` and the client can retry. Database state is never left half-written.

## Trade-offs
- R2 has no presigned POST policies, so the size limit is enforced at completion rather than
  at upload; the short URL lifetime, rate limits and lifecycle cleanup bound abuse.
- Verification runs inline in the `complete` request for now; Phase 9 moves it to the worker
  without changing the API (clients already handle `pending` -> `ready`).
- A crash between writing the final object and committing can orphan an object; a periodic
  cleanup job (Phase 9) reconciles storage with the database.
