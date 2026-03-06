export default async function OnboardingStepPage({
  params,
}: {
  params: Promise<{ step: string }>;
}) {
  const { step } = await params;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">
        Onboarding — Step {step}
      </h1>
    </div>
  );
}
