export type FieldErrors = Record<string, string[]>;

type ErrorBody = {
  code?: string;
  message?: string;
  request_id?: string | null;
  details?: unknown;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly requestId: string | null = null,
    readonly fieldErrors: FieldErrors = {},
  ) {
    super(message);
    this.name = "ApiError";
  }

  static network(): ApiError {
    return new ApiError(
      0,
      "NETWORK_ERROR",
      "Could not reach PropFlow. Check your connection and try again.",
    );
  }

  static fromResponse(status: number, payload: unknown, headerRequestId: string | null): ApiError {
    const body = errorBodyOf(payload);
    return new ApiError(
      status,
      body?.code ?? "UNKNOWN_ERROR",
      body?.message ?? "Something went wrong. Please try again.",
      body?.request_id ?? headerRequestId,
      fieldErrorsFrom(body?.details),
    );
  }
}

function errorBodyOf(payload: unknown): ErrorBody | null {
  if (typeof payload !== "object" || payload === null || !("error" in payload)) return null;
  const error = (payload as { error: unknown }).error;
  return typeof error === "object" && error !== null ? (error as ErrorBody) : null;
}

/** 422 details look like {"json": {"email": ["Not a valid email address."]}}: drop the location. */
export function fieldErrorsFrom(details: unknown): FieldErrors {
  const result: FieldErrors = {};
  if (typeof details !== "object" || details === null) return result;
  for (const location of Object.values(details)) {
    if (typeof location !== "object" || location === null) continue;
    for (const [field, messages] of Object.entries(location)) {
      if (Array.isArray(messages)) {
        result[field] = messages.filter(
          (message): message is string => typeof message === "string",
        );
      }
    }
  }
  return result;
}

/** A user-facing message for any failure. */
export function messageOf(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}
