"use client";
import { Handle, Position, type NodeProps } from "reactflow";
import { useSchemaPorts } from "@/modules/canvas/hooks/useSchemaPorts";

function Box({ title, subtitle, tone, status }: { title: string; subtitle?: string; tone: string; status?: string }) {
  const toneCls = tone === "purple" ? "bg-neutral-900 border-neutral-700" : tone === "green" ? "bg-neutral-900 border-neutral-700" : tone === "blue" ? "bg-neutral-900 border-neutral-700" : "bg-neutral-900 border-neutral-700";
  const statusCls = status === "running" ? "border-blue-500" : status === "completed" ? "border-green-500" : status === "failed" ? "border-red-500" : "";
  return (
    <div className={`relative min-w-[140px] max-w-[220px] border ${toneCls} ${statusCls} rounded p-2 text-xs text-neutral-200`}>
      {status && (
        <span
          className={`absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full ${status === "running" ? "bg-blue-500" : status === "completed" ? "bg-green-500" : status === "failed" ? "bg-red-500" : "bg-neutral-700"}`}
        />
      )}
      <div>{title}</div>
      {subtitle && <div className="text-[11px] text-neutral-400 mt-0.5 truncate max-w-[180px]">{subtitle}</div>}
    </div>
  );
}

export function LLMNode(props: NodeProps) {
  const st = String((props.data as any)?.status || "");
  const ports = useSchemaPorts("llm");
  const sub = String((props.data as any)?.summary || "");
  return (
    <div>
      {ports.inputs.map((p) => (<Handle key={p.name} id={p.name} type="target" position={Position.Left} />))}
      <Box title="LLM" subtitle={sub} tone="purple" status={st} />
      {ports.outputs.map((p) => (<Handle key={p.name} id={p.name} type="source" position={Position.Right} />))}
    </div>
  );
}

export function ToolNode(props: NodeProps) {
  const st = String((props.data as any)?.status || "");
  const ports = useSchemaPorts("tool");
  const sub = String((props.data as any)?.summary || "");
  return (
    <div>
      {ports.inputs.map((p) => (<Handle key={p.name} id={p.name} type="target" position={Position.Left} />))}
      <Box title="Tool" subtitle={sub} tone="blue" status={st} />
      {ports.outputs.map((p) => (<Handle key={p.name} id={p.name} type="source" position={Position.Right} />))}
    </div>
  );
}

export function ConditionNode(props: NodeProps) {
  const st = String((props.data as any)?.status || "");
  const ports = useSchemaPorts("condition");
  const sub = String((props.data as any)?.summary || "");
  return (
    <div>
      {ports.inputs.map((p) => (<Handle key={p.name} id={p.name} type="target" position={Position.Left} />))}
      <Box title="Condition" subtitle={sub} tone="green" status={st} />
      <div className="flex justify-between">
        {ports.outputs.map((p) => (<Handle key={p.name} id={p.name} type="source" position={p.name === "false" ? Position.Bottom : Position.Right} />))}
      </div>
    </div>
  );
}

export const nodeTypes = {
  llm: LLMNode,
  tool: ToolNode,
  condition: ConditionNode,
};
