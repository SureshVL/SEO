"use client";

import { useEffect, useState } from "react";
import { FolderOpen } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { listProjects } from "@/lib/api";

interface ProjectRow {
  id: string;
  name: string;
  domain: string | null;
}

export function ProjectPicker() {
  const { apiKey, currentProject, setCurrentProject } = useAppStore();
  const [projects, setProjects] = useState<ProjectRow[]>([]);

  useEffect(() => {
    if (!apiKey) return;
    listProjects(apiKey)
      .then((rows) => {
        setProjects(rows);
        // auto-select the first project if none selected or selection is stale
        if (rows.length && (!currentProject || !rows.some((r) => r.id === currentProject.id))) {
          setCurrentProject(rows[0]);
        }
      })
      .catch(() => setProjects([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey]);

  if (projects.length === 0) return null;

  return (
    <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
      <div className="flex items-center gap-2">
        <FolderOpen className="w-4 h-4 shrink-0" style={{ color: "var(--sidebar-muted)" }} />
        <select
          value={currentProject?.id || ""}
          onChange={(e) => {
            const project = projects.find((p) => p.id === e.target.value);
            if (project) setCurrentProject(project);
          }}
          className="w-full bg-transparent text-sm outline-none cursor-pointer rounded-md py-1"
          style={{ color: "var(--sidebar-text)" }}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id} style={{ color: "#111" }}>
              {p.name}{p.domain ? ` — ${p.domain}` : ""}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
