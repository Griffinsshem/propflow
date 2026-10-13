import { Button } from "@/components/ui/button";
import type { FieldChange } from "@/lib/conflict";

type ConflictNoticeProps = {
  what: string;
  changes: FieldChange[];
  onUseTheirs: () => void;
  onKeepMine: () => void;
};

export function ConflictNotice({ what, changes, onUseTheirs, onKeepMine }: ConflictNoticeProps) {
  return (
    <div
      role="alert"
      className="space-y-3 rounded-md bg-amber-50 p-4 text-sm text-amber-900 ring-1 ring-amber-200"
    >
      <p className="font-semibold">Someone else changed this {what} while you were editing.</p>
      {changes.length > 0 ? (
        <div>
          <p>Their changes:</p>
          <ul className="mt-1 list-disc pl-5">
            {changes.map((change) => (
              <li key={change.field}>
                {change.label}: {change.value}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p>Your changes have not been saved yet.</p>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" onClick={onUseTheirs}>
          Use their version
        </Button>
        <Button type="button" onClick={onKeepMine}>
          Keep my changes
        </Button>
      </div>
    </div>
  );
}
