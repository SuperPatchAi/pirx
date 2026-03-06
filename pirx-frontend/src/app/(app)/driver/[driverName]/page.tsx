export default async function DriverPage({
  params,
}: {
  params: Promise<{ driverName: string }>;
}) {
  const { driverName } = await params;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">
        Driver: {decodeURIComponent(driverName)}
      </h1>
      <p className="text-muted-foreground">Driver detail view</p>
    </div>
  );
}
