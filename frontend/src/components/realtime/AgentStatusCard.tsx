"use client";

interface Props {
    agentName: string;
    status: "running" | "completed" | "failed";
    description?: string;
}

export default function AgentStatusCard({
    agentName,
    status,
    description,
}: Props) {
    const color =
        status === "completed"
            ? "text-emerald-400"
            : status === "failed"
                ? "text-red-400"
                : "text-cyan-400";

    return (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="flex items-center justify-between">
                <h3 className="font-medium">{agentName}</h3>

                <span className={`text-xs ${color}`}>
                    {status.toUpperCase()}
                </span>
            </div>

            {description && (
                <p className="text-xs text-zinc-500 mt-2">
                    {description}
                </p>
            )}
        </div>
    );
}