"use client";

import { AnyWSEvent } from "@/types/websocket";

interface Props {
    events: AnyWSEvent[];
}

export default function WorkflowTimeline({ events }: Props) {
    return (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {events.map((event) => (
                <div
                    key={event.event_id}
                    className="border-l-2 border-violet-500 pl-4 py-2"
                >
                    <div className="text-xs text-violet-400">
                        {event.event_type}
                    </div>

                    <div className="text-[11px] text-zinc-500">
                        {new Date(event.timestamp).toLocaleString()}
                    </div>
                </div>
            ))}
        </div>
    );
}