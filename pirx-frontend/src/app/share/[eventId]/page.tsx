import { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";

const EVENT_NAMES: Record<string, string> = {
  "1500": "1500m",
  "3000": "3K",
  "5000": "5K",
  "10000": "10K",
  "21097": "Half Marathon",
  "42195": "Marathon",
};

interface PageProps {
  params: Promise<{ eventId: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { eventId } = await params;
  const eventName = EVENT_NAMES[eventId] || `${eventId}m`;
  return {
    title: `PIRX ${eventName} Projection`,
    description: `See my ${eventName} race projection powered by PIRX — structural performance modeling for runners.`,
    openGraph: {
      title: `PIRX ${eventName} Projection`,
      description: `Performance projection for ${eventName} — powered by PIRX structural modeling.`,
      type: "website",
      siteName: "PIRX",
    },
    twitter: {
      card: "summary_large_image",
      title: `PIRX ${eventName} Projection`,
      description: `Performance projection for ${eventName}`,
    },
  };
}

export default async function SharePage({ params }: PageProps) {
  const { eventId } = await params;
  const eventName = EVENT_NAMES[eventId] || `${eventId}m`;

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-6">
      <div className="text-center space-y-6 max-w-sm">
        <div className="text-xs font-bold tracking-widest text-primary uppercase">
          PIRX
        </div>
        <h1 className="text-3xl font-bold text-white">{eventName} Projection</h1>
        <p className="text-zinc-400 text-sm">
          PIRX is a projection-driven structural performance modeling system for
          competitive runners.
        </p>
        <div className="pt-4">
          <Link href="/signup">
            <Button size="lg">Get Your Own Projection</Button>
          </Link>
        </div>
        <p className="text-zinc-600 text-xs">
          pirx.app — Performance Intelligence Rx
        </p>
      </div>
    </div>
  );
}
