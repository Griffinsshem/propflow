import type { ComponentProps } from "react";

type TextAreaFieldProps = ComponentProps<"textarea"> & {
  id: string;
  label: string;
  error?: string;
};

export function TextAreaField({
  id,
  label,
  error,
  className = "",
  ...textarea
}: TextAreaFieldProps) {
  const errorId = error ? `${id}-error` : undefined;
  const ring = error
    ? "ring-red-400 focus:ring-red-500"
    : "ring-slate-300 focus:ring-indigo-600";
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-900">
        {label}
      </label>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        className={`mt-1.5 block w-full rounded-md border-0 px-3 py-2 text-sm text-slate-900 shadow-sm ring-1 ring-inset focus:ring-2 focus:ring-inset ${ring}`}
        {...textarea}
      />
      {error ? (
        <p id={errorId} className="mt-1.5 text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
