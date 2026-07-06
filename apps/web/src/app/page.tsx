import Link from "next/link";
import { Film } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentVideosTable } from "@/components/dashboard/recent-videos-table";
import { ActivityChart } from "@/components/dashboard/activity-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Overview of your VOD archives on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/archives">
            <Film className="h-3.5 w-3.5" />
            Manage archives
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <ActivityChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentVideosTable />
        </div>
      </div>
    </div>
  );
}
