import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function PrivacyPolicyPage() {
  return (
    <>
      <Link
        href="/login"
        className="mb-6 inline-block text-sm text-muted-foreground hover:text-primary"
      >
        &larr; Back to Login
      </Link>

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Privacy Policy</CardTitle>
          <p className="text-sm text-muted-foreground">
            Last updated: March 2026
          </p>
        </CardHeader>
        <CardContent className="prose prose-invert prose-sm max-w-none space-y-6">
          <section>
            <h3 className="text-lg font-semibold">1. What Data We Collect</h3>
            <p className="text-muted-foreground">
              PIRX collects the following categories of personal data to power
              your performance projections:
            </p>
            <ul className="list-disc space-y-1 pl-6 text-muted-foreground">
              <li>
                <strong>Running activities</strong> — pace, distance, duration,
                heart-rate, GPS routes, and interval splits synced from your
                connected wearable devices.
              </li>
              <li>
                <strong>Physiological data</strong> — resting heart-rate, HRV,
                sleep metrics, and other biometrics provided by wearable
                integrations.
              </li>
              <li>
                <strong>Blood work entries</strong> — lab values you manually
                enter (e.g. ferritin, hemoglobin) to inform health-related
                drivers.
              </li>
              <li>
                <strong>Wearable connections</strong> — OAuth tokens and
                connection metadata for Garmin, Strava, Apple Health, and other
                supported platforms.
              </li>
              <li>
                <strong>Account information</strong> — email address and
                authentication credentials.
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-lg font-semibold">2. Why We Collect It</h3>
            <p className="text-muted-foreground">
              All data is collected solely to compute your personal performance
              projections, identify training drivers, and provide actionable
              insights through the PIRX platform. We do not use your data for
              advertising or profiling purposes unrelated to your performance
              analysis.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">3. Data Sharing</h3>
            <p className="text-muted-foreground">
              <strong>We do not sell or share your personal data with third
              parties.</strong>{" "}
              Your training data, physiological information, and projections
              remain private to your account. Infrastructure providers (hosting,
              database) process data on our behalf under strict data processing
              agreements but have no independent access to your information.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">4. Data Retention</h3>
            <p className="text-muted-foreground">
              Your data is retained for as long as your PIRX account remains
              active. If you delete your account, all associated data is
              permanently removed from our systems. We do not maintain backups of
              deleted account data beyond a 30-day rolling backup window.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">
              5. Your Rights — Export &amp; Deletion
            </h3>
            <p className="text-muted-foreground">
              You have the right to access, export, and delete all of your
              personal data at any time. Visit the{" "}
              <strong>Settings</strong> page in your PIRX account to:
            </p>
            <ul className="list-disc space-y-1 pl-6 text-muted-foreground">
              <li>
                <strong>Export My Data</strong> — download a complete JSON
                archive of your activities, projections, driver history,
                physiology, and chat data.
              </li>
              <li>
                <strong>Delete All Data</strong> — permanently erase your
                account and all associated data across every table.
              </li>
            </ul>
          </section>

          <section>
            <h3 className="text-lg font-semibold">6. Compliance</h3>
            <p className="text-muted-foreground">
              PIRX is designed to comply with:
            </p>
            <ul className="list-disc space-y-1 pl-6 text-muted-foreground">
              <li>
                <strong>PIPEDA</strong> (Personal Information Protection and
                Electronic Documents Act) — Canada&apos;s federal privacy law.
              </li>
              <li>
                <strong>GDPR</strong> (General Data Protection Regulation) — the
                European Union&apos;s data protection regulation, including the
                right to access, rectification, erasure, and data portability.
              </li>
            </ul>
            <p className="text-muted-foreground">
              If you have questions about your privacy rights, contact us at{" "}
              <strong>privacy@pirx.app</strong>.
            </p>
          </section>
        </CardContent>
      </Card>
    </>
  );
}
