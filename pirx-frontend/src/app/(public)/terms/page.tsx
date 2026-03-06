import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function TermsOfServicePage() {
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
          <CardTitle className="text-2xl">Terms of Service</CardTitle>
          <p className="text-sm text-muted-foreground">
            Last updated: March 2026
          </p>
        </CardHeader>
        <CardContent className="prose prose-invert prose-sm max-w-none space-y-6">
          <section>
            <h3 className="text-lg font-semibold">1. About PIRX</h3>
            <p className="text-muted-foreground">
              PIRX is a performance analysis tool that uses your training data to
              generate running performance projections and identify training
              drivers. By creating an account or using the service, you agree to
              these terms.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">2. Not Medical Advice</h3>
            <p className="text-muted-foreground">
              PIRX is <strong>not a medical device</strong> and does not provide
              medical advice, diagnosis, or treatment. Projections, driver
              attributions, and any physiological insights are for informational
              and training-planning purposes only. Always consult a qualified
              healthcare professional before making decisions based on
              health-related data.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">3. Eligibility</h3>
            <p className="text-muted-foreground">
              You must be at least <strong>16 years of age</strong> to create a
              PIRX account. By signing up, you represent that you meet this
              minimum age requirement.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">4. Account Responsibilities</h3>
            <p className="text-muted-foreground">
              You are responsible for maintaining the security of your account
              credentials and for all activity under your account. Notify us
              immediately if you suspect unauthorized access.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">5. Changes to Terms</h3>
            <p className="text-muted-foreground">
              We may update these terms from time to time. When we make material
              changes, we will notify you through the app or by email. Continued
              use of PIRX after changes take effect constitutes acceptance of the
              revised terms.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">6. Termination</h3>
            <p className="text-muted-foreground">
              You may delete your account and all associated data at any time
              from the Settings page. We reserve the right to suspend or
              terminate accounts that violate these terms or engage in abusive
              behavior. Upon termination, your data will be permanently deleted
              in accordance with our Privacy Policy.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">
              7. Limitation of Liability
            </h3>
            <p className="text-muted-foreground">
              To the maximum extent permitted by applicable law, PIRX and its
              operators shall not be liable for any indirect, incidental,
              special, consequential, or punitive damages arising from your use
              of the service. This includes, without limitation, damages for loss
              of data, training disruptions, or reliance on projections. Our
              total liability shall not exceed the amount you paid for the
              service in the twelve months preceding the claim.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">8. Governing Law</h3>
            <p className="text-muted-foreground">
              These terms are governed by the laws of the Province of Ontario,
              Canada, without regard to conflict-of-law provisions.
            </p>
          </section>

          <section>
            <h3 className="text-lg font-semibold">9. Contact</h3>
            <p className="text-muted-foreground">
              For questions about these terms, contact us at{" "}
              <strong>legal@pirx.app</strong>.
            </p>
          </section>
        </CardContent>
      </Card>
    </>
  );
}
