"use client";

interface Props {
    progress: number;
    currentAgent?: string | null;
}

export default function LiveProgressBar({
    progress,
    currentAgent,
}: Props) {
    return (
        <div className="w-full space-y-2">
            <div className="flex justify-between text-xs text-zinc-400">
                <span>{currentAgent || "Waiting..."}</span>
                <span>{Math.round(progress)}%</span>
            </div>

            <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-violet-500 to-cyan-500 transition-all duration-500"
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}