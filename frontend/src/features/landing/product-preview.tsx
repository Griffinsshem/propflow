import { CircleCheck, Clock, Inbox, TriangleAlert } from "lucide-react";

const TILES = [
  { icon: Inbox, value: 4, label: "New requests" },
  { icon: TriangleAlert, value: 1, label: "Urgent and open" },
  { icon: Clock, value: 2, label: "Awaiting acceptance" },
  { icon: CircleCheck, value: 12, label: "Resolved this month" },
];

const REQUESTS = [
  {
    title: "Leaking kitchen tap",
    place: "Riverside Court · A1",
    status: "Submitted",
    tone: "bg-sky-50 text-sky-700 ring-sky-200",
  },
  {
    title: "No hot water",
    place: "Riverside Court · A2",
    status: "In progress",
    tone: "bg-amber-50 text-amber-800 ring-amber-200",
  },
  {
    title: "Hallway light flickering",
    place: "Hillside Homes · Common area",
    status: "Resolved",
    tone: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  },
];

/** A picture of the dashboard drawn in code: crisp at any size, no image file for the CSP. */
export function ProductPreview() {
  return (
    <div
      role="img"
      aria-label="Preview of the PropFlow dashboard, showing new, urgent and resolved maintenance requests"
      className="overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-slate-200"
    >
      <div aria-hidden>
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
          <span className="ml-2 text-xs font-medium text-slate-500">Dashboard</span>
        </div>
        <div className="space-y-4 p-4 sm:p-5">
          <div className="grid grid-cols-2 gap-2 sm:gap-3">
            {TILES.map(({ icon: Icon, value, label }) => (
              <div key={label} className="rounded-lg bg-slate-50 p-3 ring-1 ring-slate-100">
                <div className="flex items-start justify-between">
                  <span className="text-xl font-semibold text-slate-900">{value}</span>
                  <Icon className="h-4 w-4 text-slate-400" />
                </div>
                <p className="mt-1 text-xs text-slate-600">{label}</p>
              </div>
            ))}
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-700">Recently reported</p>
            <ul className="mt-2 divide-y divide-slate-100">
              {REQUESTS.map((request) => (
                <li key={request.title} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-indigo-600">{request.title}</p>
                    <p className="truncate text-xs text-slate-500">{request.place}</p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${request.tone}`}
                  >
                    {request.status}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
