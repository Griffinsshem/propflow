import {
  ArrowRight,
  Building2,
  CircleCheck,
  ClipboardCheck,
  Code,
  HardHat,
  History,
  Image as ImageIcon,
  KeyRound,
  LayoutDashboard,
  ShieldCheck,
  Smartphone,
  Users,
  Wrench,
} from "lucide-react";
import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";

import { StartDemoButton } from "@/features/demo/start-demo-button";
import { ProductPreview } from "@/features/landing/product-preview";
import { WakeApi } from "@/features/landing/wake-api";

const TITLE = "PropFlow: property maintenance, from report to resolved";
const DESCRIPTION =
  "Tenants report repairs from their phone, managers assign contractors, and everyone follows the same status until the job is closed.";

export const metadata: Metadata = {
  title: { absolute: TITLE },
  description: DESCRIPTION,
  openGraph: { title: TITLE, description: DESCRIPTION, siteName: "PropFlow", type: "website" },
  twitter: { card: "summary_large_image", title: TITLE, description: DESCRIPTION },
};

// Set to the GitHub address once the repository is public; until then, no link (it would 404).
const REPOSITORY_URL: string | null = "https://github.com/Griffinsshem/propflow";

const primary =
  "inline-flex items-center justify-center gap-2 rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600";
const secondary =
  "inline-flex items-center justify-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-sm ring-1 ring-slate-300 hover:bg-slate-50";

const demo =
  "inline-flex items-center justify-center gap-2 rounded-md bg-indigo-50 px-4 py-2.5 text-sm font-semibold text-indigo-700 ring-1 ring-indigo-200 hover:bg-indigo-100";

const STEPS = [
  {
    icon: Smartphone,
    title: "Report",
    text: "A tenant describes the problem from their phone and adds photos. It takes about a minute.",
  },
  {
    icon: ClipboardCheck,
    title: "Triage",
    text: "The property's manager sees it straight away, sets the priority and assigns a contractor.",
  },
  {
    icon: HardHat,
    title: "Fix",
    text: "The contractor accepts the job, updates progress, and talks to everyone in one thread.",
  },
  {
    icon: CircleCheck,
    title: "Close",
    text: "The manager resolves and closes the request. The tenant is notified at every step.",
  },
];

const ROLES = [
  {
    icon: LayoutDashboard,
    title: "Owners and managers",
    points: [
      "Dashboards showing what is new, urgent and overdue",
      "Properties, units and tenants in one place",
      "Work orders with due dates and full history",
    ],
  },
  {
    icon: Users,
    title: "Tenants",
    points: [
      "Report repairs with photos, any time",
      "Follow progress without phoning anyone",
      "Notifications whenever something changes",
    ],
  },
  {
    icon: Wrench,
    title: "Contractors",
    points: [
      "One list of the jobs assigned to you",
      "Accept, or decline with a reason",
      "Update progress and completion from site",
    ],
  },
];

const TRUST = [
  {
    icon: ShieldCheck,
    title: "Everyone sees only their part",
    text: "Roles are enforced by the server on every request: tenants see their own requests, contractors only their jobs.",
  },
  {
    icon: ImageIcon,
    title: "Private photos",
    text: "Photos are stored privately and shown only through short-lived links, with location data removed.",
  },
  {
    icon: History,
    title: "Every change recorded",
    text: "An audit log keeps who changed what and when, and each request shows its full timeline.",
  },
  {
    icon: KeyRound,
    title: "Accounts protected",
    text: "Strong password hashing, email verification, and limits on repeated attempts.",
  },
];

const STACK = [
  "Next.js · TypeScript",
  "Flask · Python",
  "PostgreSQL",
  "Redis",
  "Cloudflare R2",
  "Playwright",
];

function Actions({ signedIn, large = false }: { signedIn: boolean; large?: boolean }) {
  const size = large ? " px-5 py-3 text-base" : "";
  return signedIn ? (
    <Link href="/dashboard" className={primary + size}>
      Go to dashboard <ArrowRight aria-hidden className="h-4 w-4" />
    </Link>
  ) : (
    <>
      <Link href="/register" className={primary + size}>
        Get started <ArrowRight aria-hidden className="h-4 w-4" />
      </Link>
      <Link href="/login" className={secondary + size}>
        Sign in
      </Link>
    </>
  );
}

export default async function LandingPage() {
  // A hint for which buttons to show, without asking the (possibly sleeping) API. The app still
  // checks the session properly: an expired one simply leads to the sign-in page.
  const signedIn = (await cookies()).getAll().some((cookie) => /session/i.test(cookie.name));
  const year = new Date().getFullYear();

  return (
    <div className="bg-white text-slate-900">
      <WakeApi />
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4">
          <Link href="/" className="text-lg font-bold tracking-tight text-indigo-600">
            PropFlow
          </Link>
          <nav
            aria-label="Sections"
            className="hidden items-center gap-6 text-sm text-slate-600 md:flex"
          >
            <a href="#how-it-works" className="hover:text-slate-900">
              How it works
            </a>
            <a href="#roles" className="hover:text-slate-900">
              For every role
            </a>
            <a href="#trust" className="hover:text-slate-900">
              Security
            </a>
            <a href="#built" className="hover:text-slate-900">
              How it&apos;s built
            </a>
          </nav>
          <div className="flex items-center gap-2">
            {signedIn ? (
              <Link href="/dashboard" className={primary}>
                Go to dashboard <ArrowRight aria-hidden className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Sign in
                </Link>
                <Link href="/register" className={primary}>
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-14 sm:py-20 lg:grid-cols-2">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700">
              <Building2 aria-hidden className="h-4 w-4" />
              For owners, managers, tenants and contractors
            </p>
            <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-5xl">
              Maintenance requests that don&apos;t get lost.
            </h1>
            <p className="mt-5 text-lg text-slate-600">{DESCRIPTION}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Actions signedIn={signedIn} large />
              {signedIn ? null : <StartDemoButton className={demo + " px-5 py-3 text-base"} />}
            </div>
            <p className="mt-4 text-sm text-slate-500">
              Free to try. The live demo needs no account and is yours alone.
            </p>
          </div>
          <ProductPreview />
        </section>

        <section id="how-it-works" className="scroll-mt-20 bg-slate-50 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4">
            <h2 className="text-3xl font-bold tracking-tight">How a repair moves</h2>
            <p className="mt-3 max-w-2xl text-slate-600">
              One request, one status, seen by everyone involved, from the first report to the
              closed job.
            </p>
            <ol className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map(({ icon: Icon, title, text }, index) => (
                <li key={title} className="rounded-xl bg-white p-6 ring-1 ring-slate-200">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
                      <Icon aria-hidden className="h-5 w-5" />
                    </span>
                    <span className="text-sm font-semibold text-slate-500">Step {index + 1}</span>
                  </div>
                  <h3 className="mt-4 font-semibold">{title}</h3>
                  <p className="mt-2 text-sm text-slate-600">{text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="roles" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:py-20">
          <h2 className="text-3xl font-bold tracking-tight">Something for everyone involved</h2>
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {ROLES.map(({ icon: Icon, title, points }) => (
              <div key={title} className="rounded-xl p-6 ring-1 ring-slate-200">
                <Icon aria-hidden className="h-6 w-6 text-indigo-600" />
                <h3 className="mt-4 text-lg font-semibold">{title}</h3>
                <ul className="mt-3 space-y-2 text-sm text-slate-600">
                  {points.map((point) => (
                    <li key={point} className="flex gap-2">
                      <CircleCheck
                        aria-hidden
                        className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                      />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section id="trust" className="scroll-mt-20 bg-slate-50 py-16 sm:py-20">
          <div className="mx-auto max-w-6xl px-4">
            <h2 className="text-3xl font-bold tracking-tight">Built to be trusted</h2>
            <div className="mt-10 grid gap-6 sm:grid-cols-2">
              {TRUST.map(({ icon: Icon, title, text }) => (
                <div
                  key={title}
                  className="flex gap-4 rounded-xl bg-white p-6 ring-1 ring-slate-200"
                >
                  <Icon aria-hidden className="h-6 w-6 shrink-0 text-indigo-600" />
                  <div>
                    <h3 className="font-semibold">{title}</h3>
                    <p className="mt-1 text-sm text-slate-600">{text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="built" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16 sm:py-20">
          <div className="flex items-center gap-3">
            <Code aria-hidden className="h-6 w-6 text-indigo-600" />
            <h2 className="text-3xl font-bold tracking-tight">How it&apos;s built</h2>
          </div>
          <p className="mt-4 max-w-3xl text-slate-600">
            PropFlow is a full-stack project: a Flask API with PostgreSQL and Redis, a Next.js
            frontend, and private photo storage on Cloudflare R2. Every change runs backend and
            frontend tests and browser journeys before it can deploy, and each significant design
            choice is recorded as an architecture decision record.
          </p>
          <ul className="mt-6 flex flex-wrap gap-2">
            {STACK.map((item) => (
              <li
                key={item}
                className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700"
              >
                {item}
              </li>
            ))}
          </ul>
          {REPOSITORY_URL ? (
            <a
              href={REPOSITORY_URL}
              className="mt-6 inline-flex font-semibold text-indigo-600 hover:text-indigo-500"
            >
              Read the code and decisions on GitHub
            </a>
          ) : null}
        </section>

        <section className="bg-indigo-600">
          <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-14 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Ready to stop chasing repair requests?
            </h2>
            <div className="flex flex-wrap gap-3">
              {signedIn ? (
                <Link href="/dashboard" className={secondary}>
                  Go to dashboard
                </Link>
              ) : (
                <>
                  <Link href="/register" className={secondary}>
                    Get started
                  </Link>
                  <Link
                    href="/login"
                    className="inline-flex items-center rounded-md px-4 py-2.5 text-sm font-semibold text-white ring-1 ring-white/40 hover:bg-white/10"
                  >
                    Sign in
                  </Link>
                </>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:justify-between">
          <p>© {year} PropFlow · Built by Griffins Shem</p>
          <p>Property operations: maintenance, work orders and tenants in one place.</p>
        </div>
      </footer>
    </div>
  );
}
