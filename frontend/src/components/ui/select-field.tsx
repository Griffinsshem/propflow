import type { ComponentProps } from "react";

type Option = { value: string; label: string };

type SelectFieldProps = ComponentProps<"select"> & {
  id: string;
  label: string;
  options: readonly Option[];
  error?: string;
};

export function SelectField({
  id,
  label,
  options,
  error,
  className = "",
  ...select
}: SelectFieldProps) {
  const errorId = error ? `${id}-error` : undefined;
  const ring = error
    ? "ring-red-400 focus:ring-red-500"
    : "ring-slate-300 focus:ring-indigo-600";
  return (
    <div className={className}>
      <label htmlFor={id} className="block text-sm font-medium text-slate-900">
        {label}
      </label>
      <select
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        className={`mt-1.5 block w-full rounded-md border-0 py-2 pl-3 pr-8 text-sm text-slate-900 ring-1 ring-inset focus:ring-2 focus:ring-inset ${ring}`}
        {...select}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error ? (
        <p id={errorId} className="mt-1.5 text-sm text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
}
