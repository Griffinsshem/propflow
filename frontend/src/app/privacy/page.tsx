import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What PropFlow stores about you, why, who processes it, and how long it is kept.",
  alternates: { canonical: "/privacy" },
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
      <div className="space-y-3 text-slate-700">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-10 px-4 py-12 sm:py-16">
      <header className="space-y-3">
        <Link href="/" className="text-lg font-bold tracking-tight text-indigo-600">
          PropFlow
        </Link>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Privacy</h1>
        <p className="text-slate-600">
          PropFlow is a portfolio project by Griffins Shem. This page says, in plain language, what
          it stores and why. Last updated 17 October 2026.
        </p>
      </header>

      <Section title="What is stored">
        <ul className="list-disc space-y-2 pl-5">
          <li>Your name and email address, and your password only as a one-way hash.</li>
          <li>
            What you and your organization enter: properties, units, tenants, contractors,
            maintenance requests, comments, work orders and photos.
          </li>
          <li>
            Security records: the IP address and browser of each sign-in, and an audit log of
            changes (who changed what, and when).
          </li>
        </ul>
      </Section>

      <Section title="Why">
        <p>
          To run the service you use; to send the emails it needs (verification, invitations,
          password resets and notifications); and to keep accounts safe, for example by limiting
          repeated sign-in attempts.
        </p>
        <p>There are no adverts, no selling of data and no tracking cookies.</p>
      </Section>

      <Section title="Photos">
        <p>
          Location data is removed from photos before they are stored. Photos are private, and are
          shown only to people allowed to see the request, through links that expire.
        </p>
      </Section>

      <Section title="Cookies">
        <p>
          Only two kinds, both needed for signing in: a session cookie, and a cookie that protects
          your account against forged requests.
        </p>
      </Section>

      <Section title="Who processes it">
        <p>
          Vercel (the website), Render (the API), Neon (the database, in Frankfurt), Cloudflare R2
          (photos) and Brevo (email). Each processes data only to provide its part of the service.
        </p>
      </Section>

      <Section title="How long it is kept">
        <p>
          Expired sessions and old notifications are deleted automatically. Demo sandboxes, and
          everything in them, are deleted after 24 hours. Account data is kept until you ask for it
          to be deleted.
        </p>
      </Section>

      <Section title="Your choices">
        <p>
          You can ask to see, correct or delete your data. Please get in touch through{" "}
          <a
            href="https://github.com/Griffinsshem"
            className="font-semibold text-indigo-600 hover:text-indigo-500"
          >
            github.com/Griffinsshem
          </a>
          .
        </p>
        <p>
          As a portfolio project, PropFlow should not be used to store sensitive personal
          information.
        </p>
      </Section>
    </main>
  );
}
