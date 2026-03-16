import { Trash2 } from "lucide-react";

interface ConfirmDeleteProps {
  id: string;
  pending: string | null;
  deleting: string | null;
  onRequest: (id: string) => void;
  onConfirm: (id: string) => void;
  onCancel: () => void;
}

export function ConfirmDelete({ id, pending, deleting, onRequest, onConfirm, onCancel }: ConfirmDeleteProps) {
  if (pending === id) {
    return (
      <div className="flex items-center gap-1.5 whitespace-nowrap">
        <span className="text-xs text-[#374151]">Sure?</span>
        <button
          onClick={() => onCancel()}
          className="px-2 py-0.5 rounded text-xs text-[#6b7280] hover:bg-[#f3f4f6] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => onConfirm(id)}
          disabled={deleting === id}
          className="px-2 py-0.5 rounded text-xs font-medium bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
        >
          {deleting === id ? "…" : "Delete"}
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={() => onRequest(id)}
      disabled={!!deleting}
      className="p-1.5 rounded-md text-[#d1d5db] hover:text-red-400 hover:bg-red-50 transition-colors disabled:opacity-40"
      title="Delete"
    >
      <Trash2 className="size-3.5" />
    </button>
  );
}
