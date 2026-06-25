"use client";

import { Wifi, WifiOff, Loader2 } from "lucide-react";

interface Props {
    state: "connected" | "connecting" | "reconnecting" | "disconnected";
}

export default function ConnectionStatus({ state }: Props) {
    if (state === "connected") {
        return (
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
                <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <Wifi className="w-3 h-3" />
                Connected
            </div>
        );
    }

    if (state === "connecting") {
        return (
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs">
                <Loader2 className="w-3 h-3 animate-spin" />
                Connecting
            </div>
        );
    }

    if (state === "reconnecting") {
        return (
            <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs">
                <Loader2 className="w-3 h-3 animate-spin" />
                Reconnecting
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
            <WifiOff className="w-3 h-3" />
            Disconnected
        </div>
    );
}