export default async function EventPage({
  params,
}: {
  params: Promise<{ eventId: string }>;
}) {
  const { eventId } = await params;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Event {eventId}</h1>
      <p className="text-muted-foreground">Event projection details</p>
    </div>
  );
}
