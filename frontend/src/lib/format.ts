const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function formatDate(value: string): string {
  return dateFormat.format(new Date(value));
}

const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDateTime(value: string): string {
  return dateTimeFormat.format(new Date(value));
}

/** A calendar date (YYYY-MM-DD) shown as that same day, whatever the user's time zone. */
export function formatDay(value: string): string {
  return dateFormat.format(new Date(`${value}T00:00:00`));
}
